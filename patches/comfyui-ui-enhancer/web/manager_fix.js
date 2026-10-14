import { app } from "../../scripts/app.js";

/**
 * ComfyUI UI Enhancer - SoTA Runtime Patch for ComfyUI-Manager
 * Features:
 * - Scoped CSS Custom Properties & Glassmorphic UI
 * - RAF-batched & Idempotent DOM Normalization
 * - Two-tier MutationObserver (Zero global click polling overhead)
 */

const STYLE_ID = "cm-manager-ui-enhancer-style";
const DIALOG_ID = "cm-manager-dialog";
const ENHANCED_ATTR = "data-cm-enhanced";

const SOTA_STYLES = `
/* ==========================================================================
   ComfyUI Manager Dialog - SoTA Design System & Tokens
   ========================================================================== */
#${DIALOG_ID} {
	--cm-bg-surface: var(--comfy-menu-bg, rgba(24, 24, 28, 0.88));
	--cm-bg-elevated: var(--comfy-menu-secondary-bg, rgba(255, 255, 255, 0.045));
	--cm-bg-hover: rgba(255, 255, 255, 0.09);
	--cm-bg-active: rgba(255, 255, 255, 0.03);
	--cm-border: var(--border-color, rgba(255, 255, 255, 0.1));
	--cm-border-hover: var(--p-primary-color, var(--primary-color, #4b7bec));
	--cm-text-primary: var(--input-text, #f1f3f5);
	--cm-text-secondary: var(--descrip-text, #adb5bd);
	--cm-danger-bg: linear-gradient(135deg, #9b1c20 0%, #7a1317 100%);
	--cm-danger-border: #c92a2a;
	--cm-radius-sm: 6px;
	--cm-radius-md: 8px;
	--cm-radius-lg: 14px;
	--cm-ease-out: cubic-bezier(0.22, 1, 0.36, 1);

	max-width: min(95vw, 1160px) !important;
	box-sizing: border-box !important;
	background: var(--cm-bg-surface) !important;
	backdrop-filter: blur(18px) saturate(140%) !important;
	-webkit-backdrop-filter: blur(18px) saturate(140%) !important;
	border: 1px solid var(--cm-border) !important;
	border-radius: var(--cm-radius-lg) !important;
	box-shadow: 
		0 24px 48px -12px rgba(0, 0, 0, 0.65),
		0 0 0 1px rgba(255, 255, 255, 0.05) inset !important;
	color: var(--cm-text-primary) !important;
}

/* --- Layout & Columns --- */
#${DIALOG_ID} .cm-menu-container {
	padding: 20px !important;
	column-gap: 24px !important;
	row-gap: 20px !important;
	display: flex !important;
	flex-wrap: wrap !important;
	justify-content: center !important;
	align-items: flex-start !important;
	box-sizing: border-box !important;
}

#${DIALOG_ID} .cm-menu-column {
	display: flex !important;
	flex-direction: column !important;
	flex: 1 1 280px !important;
	max-width: 340px !important;
	gap: 8px !important;
	box-sizing: border-box !important;
}

/* --- Interactive Buttons --- */
#${DIALOG_ID} .cm-button,
#${DIALOG_ID} .cm-button-red {
	width: 100% !important;
	min-height: 36px !important;
	position: relative !important;
	overflow: hidden !important;
	background: var(--cm-bg-elevated) !important;
	border: 1px solid var(--cm-border) !important;
	border-radius: var(--cm-radius-md) !important;
	color: var(--cm-text-primary) !important;
	padding: 7px 14px !important;
	margin: 0 !important;
	font-size: 13px !important;
	font-weight: 500 !important;
	line-height: 1.35 !important;
	cursor: pointer !important;
	transition: 
		transform 0.16s var(--cm-ease-out),
		background-color 0.16s var(--cm-ease-out),
		border-color 0.16s var(--cm-ease-out),
		box-shadow 0.16s var(--cm-ease-out),
		filter 0.16s var(--cm-ease-out) !important;
	display: inline-flex !important;
	align-items: center !important;
	justify-content: center !important;
	text-align: center !important;
	box-sizing: border-box !important;
	user-select: none !important;
	box-shadow: 0 1px 2px rgba(0, 0, 0, 0.2) !important;
}

#${DIALOG_ID} .cm-button:hover {
	background: var(--cm-bg-hover) !important;
	border-color: var(--cm-border-hover) !important;
	transform: translateY(-1px) !important;
	box-shadow: 
		0 4px 12px rgba(0, 0, 0, 0.28),
		0 0 0 1px color-mix(in srgb, var(--cm-border-hover) 25%, transparent) !important;
}

#${DIALOG_ID} .cm-button:active,
#${DIALOG_ID} .cm-button-red:active {
	transform: translateY(0) scale(0.985) !important;
	background: var(--cm-bg-active) !important;
	box-shadow: none !important;
}

#${DIALOG_ID} .cm-button:focus-visible,
#${DIALOG_ID} .cm-button-red:focus-visible,
#${DIALOG_ID} .cm-menu-combo:focus-visible {
	outline: 2px solid var(--cm-border-hover) !important;
	outline-offset: 2px !important;
}

/* --- Danger / Destructive Buttons --- */
#${DIALOG_ID} .cm-button-red {
	background: var(--cm-danger-bg) !important;
	border-color: var(--cm-danger-border) !important;
	color: #ffffff !important;
	font-weight: 600 !important;
}

#${DIALOG_ID} .cm-button-red:hover {
	filter: brightness(1.15) !important;
	border-color: #ff6b6b !important;
	transform: translateY(-1px) !important;
	box-shadow: 0 4px 14px rgba(201, 42, 42, 0.4) !important;
}

/* --- Experimental Fieldset & Legend --- */
#${DIALOG_ID} .cm-experimental,
#${DIALOG_ID} filedset.cm-experimental,
#${DIALOG_ID} fieldset.cm-experimental {
	border: 1px solid var(--cm-border) !important;
	border-radius: var(--cm-radius-md) !important;
	background: rgba(0, 0, 0, 0.14) !important;
	padding: 14px 12px 12px 12px !important;
	display: flex !important;
	flex-direction: column !important;
	gap: 8px !important;
	margin-top: 14px !important;
	box-sizing: border-box !important;
}

#${DIALOG_ID} .cm-experimental-legend {
	font-size: 10.5px !important;
	font-weight: 700 !important;
	text-transform: uppercase !important;
	letter-spacing: 0.75px !important;
	background: var(--cm-danger-bg) !important;
	color: #ffffff !important;
	border: 1px solid rgba(255, 255, 255, 0.18) !important;
	border-radius: 999px !important;
	padding: 2px 10px !important;
	text-align: center !important;
	margin: -24px auto 4px auto !important;
	transform: none !important;
	display: table !important;
	position: static !important;
	box-shadow: 0 2px 6px rgba(0, 0, 0, 0.35) !important;
}

/* --- Select / Combobox --- */
#${DIALOG_ID} .cm-menu-combo {
	cursor: pointer !important;
	padding: 6px 10px !important;
	border: 1px solid var(--cm-border) !important;
	border-radius: var(--cm-radius-sm) !important;
	background: var(--cm-bg-elevated) !important;
	color: var(--cm-text-primary) !important;
	font-size: 12.5px !important;
	font-weight: 500 !important;
	width: 170px !important;
	box-sizing: border-box !important;
	transition: border-color 0.15s ease, background-color 0.15s ease !important;
}

#${DIALOG_ID} .cm-menu-combo:hover {
	background: var(--cm-bg-hover) !important;
	border-color: var(--cm-border-hover) !important;
}

/* --- Setting Rows --- */
#${DIALOG_ID} .setting-item {
	margin-bottom: 4px !important;
	padding: 2px 0 !important;
}

#${DIALOG_ID} .setting-item > div {
	display: flex !important;
	flex-direction: row !important;
	align-items: center !important;
	justify-content: space-between !important;
	gap: 10px !important;
	width: 100% !important;
}

#${DIALOG_ID} .setting-item span.text-muted {
	font-size: 12.5px !important;
	font-weight: 500 !important;
	color: var(--cm-text-secondary) !important;
	white-space: nowrap !important;
	overflow: hidden !important;
	text-overflow: ellipsis !important;
}

/* --- Special Buttons & Notice Board --- */
#${DIALOG_ID} #workflowgallery-button {
	min-height: 46px !important;
	padding: 6px 28px 6px 12px !important;
	display: flex !important;
	flex-direction: column !important;
	justify-content: center !important;
	align-items: center !important;
}

#${DIALOG_ID} #cm-manual-button {
	padding-right: 28px !important;
}

#${DIALOG_ID} .cm-notice-board {
	border: 1px solid var(--cm-border) !important;
	border-radius: var(--cm-radius-md) !important;
	background: rgba(0, 0, 0, 0.25) !important;
	padding: 10px 14px !important;
	box-sizing: border-box !important;
	box-shadow: inset 0 2px 6px rgba(0, 0, 0, 0.25) !important;
	scrollbar-width: thin !important;
}

/* --- Normalized Semantic Divider --- */
#${DIALOG_ID} .cm-divider-line {
	border: 0 !important;
	border-top: 1px solid var(--cm-border) !important;
	margin: 4px 0 !important;
	width: 100% !important;
	height: 1px !important;
	display: block !important;
	opacity: 0.75 !important;
}
`;

app.registerExtension({
	name: "Comfy.UIEnhancer.ManagerFix",
	async setup() {
		// 1. Inject Scoped Stylesheet
		if (!document.getElementById(STYLE_ID)) {
			const style = document.createElement("style");
			style.id = STYLE_ID;
			style.textContent = SOTA_STYLES;
			document.head.appendChild(style);
		}

		let rafId = null;
		let dialogObserver = null;
		let observedDialog = null;

		// 2. Idempotent DOM Normalization
		const normalizeDialogDOM = (dialog) => {
			if (!dialog) return;

			const columns = dialog.querySelectorAll(".cm-menu-column");
			columns.forEach((col) => {
				Array.from(col.children).forEach((child) => {
					// Clean up stray <br> tags injected by legacy Manager layout
					if (child.tagName === "BR") {
						child.style.display = "none";
						return;
					}

					// Convert empty spacer <div> elements into styled semantic dividers
					if (
						child.tagName === "DIV" &&
						!child.hasAttribute(ENHANCED_ATTR) &&
						child.children.length === 0 &&
						child.textContent.trim() === ""
					) {
						child.classList.add("cm-divider-line");
						child.setAttribute("role", "separator");
						child.setAttribute(ENHANCED_ATTR, "true");
					}
				});
			});

			// Ensure all Manager buttons inherit PrimeVue component classes cleanly
			dialog
				.querySelectorAll(`button.cm-button:not([${ENHANCED_ATTR}]), button.cm-button-red:not([${ENHANCED_ATTR}])`)
				.forEach((btn) => {
					btn.classList.add("p-button", "p-component");
					btn.setAttribute(ENHANCED_ATTR, "true");
				});
		};

		// Schedule DOM patch inside requestAnimationFrame to prevent layout thrashing
		const scheduleEnhancement = (dialog) => {
			if (rafId) cancelAnimationFrame(rafId);
			rafId = requestAnimationFrame(() => {
				normalizeDialogDOM(dialog);
				rafId = null;
			});
		};

		// Attach a dedicated observer to the dialog itself once mounted
		const attachDialogObserver = (dialog) => {
			if (observedDialog === dialog) return;
			if (dialogObserver) dialogObserver.disconnect();

			observedDialog = dialog;
			scheduleEnhancement(dialog);

			dialogObserver = new MutationObserver(() => {
				scheduleEnhancement(dialog);
			});

			dialogObserver.observe(dialog, {
				childList: true,
				subtree: true,
			});
		};

		// 3. Lightweight Root Observer: Detects when #cm-manager-dialog enters DOM
		const existingDialog = document.getElementById(DIALOG_ID);
		if (existingDialog) {
			attachDialogObserver(existingDialog);
		}

		const rootObserver = new MutationObserver((mutations) => {
			for (const mutation of mutations) {
				for (const node of mutation.addedNodes) {
					if (node.nodeType !== Node.ELEMENT_NODE) continue;

					if (node.id === DIALOG_ID) {
						attachDialogObserver(node);
						return;
					}

					const nestedDialog = node.querySelector?.(`#${DIALOG_ID}`);
					if (nestedDialog) {
						attachDialogObserver(nestedDialog);
						return;
					}
				}
			}
		});

		rootObserver.observe(document.body, {
			childList: true,
			subtree: true,
		});
	},
});