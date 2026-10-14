"""ComfyUI Dynamic Patch: Fix PNG/EXIF Orientation & PyAV Frame Rotation Desync.

This patch fixes the silent desynchronization between the frontend canvas preview
and the backend IMAGE tensor in ComfyUI Core's LoadImage node.

Root Cause:
- PyAV (via FFmpeg) misinterprets PNG eXIf metadata chunks and assigns corrupt
  non-orthogonal frame.rotation values (e.g. 135 degrees).
- `comfy_api.latest._input_impl.video_types:VideoFromFile.get_components_internal`
  performed integer floor division `frame.rotation // 90` which converted 135 deg
  into k=1 (a 90° CCW rotation on upright portrait images).

Fix:
- Validates that rotation angles must be valid non-zero orthogonal multiples of 90
  (i.e. rot % 90 == 0 and rot % 360 != 0) before applying np.rot90.
"""

from __future__ import annotations
import logging
from fractions import Fraction
import numpy as np
import torch
import av

logger = logging.getLogger("ComfyUI-Fix-Image-Rotation")

def apply_patch() -> bool:
    try:
        import comfy_api.latest._input_impl.video_types as video_types
        from comfy_api.latest._input_impl.video_types import VideoComponents, AudioInput, last_decodable_audio_stream
        
        orig_method = video_types.VideoFromFile.get_components_internal
        
        def patched_get_components_internal(self, container):
            video_stream = self._get_first_video_stream(container)
            start_time, duration = self.get_active_trim_window()

            frames = []
            audio_frames = []
            alphas = None
            start_pts = int(start_time / video_stream.time_base)
            end_pts = int((start_time + duration) / video_stream.time_base)

            if start_pts != 0:
                container.seek(start_pts, stream=video_stream)

            image_format = 'gbrpf32le'
            process_image_format = lambda a: a
            align_graph = None
            audio = None

            streams = [video_stream]
            has_first_audio_frame = False
            checked_alpha = False

            video_done = False
            audio_done = True

            audio_stream = last_decodable_audio_stream(container)
            if audio_stream is not None:
                streams += [audio_stream]
                resampler = av.audio.resampler.AudioResampler(format='fltp')
                audio_done = False

            for packet in container.demux(*streams):
                if video_done and audio_done:
                    break

                if packet.stream.type == "video":
                    if video_done:
                        continue
                    try:
                        for frame in packet.decode():
                            if frame.pts < start_pts:
                                continue
                            if duration and frame.pts >= end_pts:
                                video_done = True
                                break

                            if not checked_alpha:
                                alpha_channel = False
                                for comp in frame.format.components:
                                    if comp.is_alpha or frame.format.name == "pal8":
                                        alphas = []
                                        alpha_channel = True
                                        break
                                if frame.format.name in ("yuvj420p", "yuvj422p", "yuvj444p", "rgb24", "rgba", "pal8"):
                                    process_image_format = lambda a: a.float() / 255.0
                                    if alpha_channel:
                                        image_format = 'rgba'
                                    else:
                                        image_format = 'rgb24'
                                else:
                                    process_image_format = lambda a: a
                                    if alpha_channel:
                                        image_format = 'gbrapf32le'
                                    else:
                                        image_format = 'gbrpf32le'

                                checked_alpha = True

                            if image_format in ('gbrpf32le', 'gbrapf32le') and frame.width % 32 != 0:
                                if align_graph is None:
                                    pad_w = ((frame.width + 31) // 32) * 32
                                    pad_h = ((frame.height + 31) // 32) * 32
                                    g = av.filter.Graph()
                                    g_src = g.add_buffer(width=frame.width, height=frame.height,
                                                         format=frame.format.name, time_base=video_stream.time_base)
                                    g_pad = g.add('pad', f'{pad_w}:{pad_h}:0:0')
                                    g_fill = g.add('fillborders', f'left=0:right={pad_w - frame.width}:top=0:bottom={pad_h - frame.height}:mode=smear')
                                    g_sink = g.add('buffersink')
                                    g_src.link_to(g_pad)
                                    g_pad.link_to(g_fill)
                                    g_fill.link_to(g_sink)
                                    g.configure()
                                    align_graph = (g, g_src, g_sink)
                                align_graph[1].push(frame)
                                img = np.ascontiguousarray(align_graph[2].pull().to_ndarray(format=image_format)[:frame.height, :frame.width])
                            else:
                                img = frame.to_ndarray(format=image_format)

                            # FIXED: Validate orthogonal rotation (must be multiple of 90 and not multiple of 360)
                            rot = getattr(frame, 'rotation', 0)
                            if rot and isinstance(rot, (int, float)) and (rot % 90 == 0) and (rot % 360 != 0):
                                k = int(round(rot / 90.0)) % 4
                                img = np.rot90(img, k=k, axes=(0, 1)).copy()

                            if alphas is None:
                                frames.append(torch.from_numpy(img))
                            else:
                                frames.append(torch.from_numpy(img[..., :-1]))
                                alphas.append(torch.from_numpy(img[..., -1:]))
                    except av.error.InvalidDataError:
                        logging.info("pyav decode error")

                elif packet.stream.type == "audio":
                    if audio_done:
                        continue

                    import itertools
                    aframes = itertools.chain.from_iterable(
                        map(resampler.resample, packet.decode())
                    )
                    for frame in aframes:
                        if duration and frame.time > start_time + duration:
                            audio_done = True
                            break

                        if not has_first_audio_frame:
                            offset_seconds = start_time - frame.pts * audio_stream.time_base
                            to_skip = max(0, int(offset_seconds * audio_stream.sample_rate))
                            if to_skip < frame.samples:
                                has_first_audio_frame = True
                                audio_frames.append(frame.to_ndarray()[..., to_skip:])
                        else:
                            audio_frames.append(frame.to_ndarray())

            images = process_image_format(torch.stack(frames)) if len(frames) > 0 else torch.zeros(0, 0, 0, 3)
            if alphas is not None:
                alphas = process_image_format(torch.stack(alphas)) if len(alphas) > 0 else torch.zeros(0, 0, 0, 1)

            frame_rate = Fraction(video_stream.average_rate) if video_stream.average_rate else Fraction(1)

            if len(audio_frames) > 0:
                audio_data = np.concatenate(audio_frames, axis=1)
                if duration:
                    audio_data = audio_data[..., :int(duration * audio_stream.sample_rate)]
                audio_tensor = torch.from_numpy(audio_data).unsqueeze(0)
                audio = AudioInput({
                    "waveform": audio_tensor,
                    "sample_rate": int(audio_stream.sample_rate) if audio_stream.sample_rate else 1,
                })

            metadata = container.metadata
            return VideoComponents(images=images, alpha=alphas, audio=audio, frame_rate=frame_rate, metadata=metadata)

        video_types.VideoFromFile.get_components_internal = patched_get_components_internal
        print("[OK] ComfyUI-Fix-Image-Rotation dynamic patch applied successfully.")
        return True
    except Exception as e:
        print(f"[WARN] Failed to apply ComfyUI-Fix-Image-Rotation patch: {e}")
        return False

apply_patch()

NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
