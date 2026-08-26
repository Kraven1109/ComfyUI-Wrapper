import { app } from "../../scripts/app.js";

/**
 * ComfyUI UI Enhancer - Dynamic Runtime Patch for ComfyUI-Manager
 * Injects styling and DOM fixes purely in browser runtime without touching upstream code.
 */
app.registerExtension({
	name: "Comfy.UIEnhancer.ManagerFix",
	async setup() {
		// 1. Inject high-priority styles for ComfyUI Manager Dialog
		const styleId = "cm-manager-ui-enhancer-style";
		if (!document.getElementById(styleId)) {
			const style = document.createElement("style");
			style.id = styleId;
			style.textContent = `
				/* --- ComfyUI Manager Dialog Enhancements --- */
				#cm-manager-dialog {
					max-width: 95vw !important;
					box-sizing: border-box !important;
				}

				#cm-manager-dialog .cm-menu-container {
					padding: 16px !important;
					column-gap: 20px !important;
					row-gap: 16px !important;
					display: flex !important;
					flex-wrap: wrap !important;
					justify-content: center !important;
					box-sizing: border-box !important;
				}

				#cm-manager-dialog .cm-menu-column {
					display: flex !important;
					flex-direction: column !important;
					flex: 1 1 280px !important;
					max-width: 320px !important;
					box-sizing: border-box !important;
				}

				#cm-manager-dialog .cm-button {
					width: 100% !important;
					position: relative !important;
					overflow: hidden !important;
					background-color: var(--comfy-menu-secondary-bg, rgba(255, 255, 255, 0.05)) !important;
					border: 1px solid var(--border-color, #444) !important;
					border-radius: 6px !important;
					color: var(--input-text, #eee) !important;
					padding: 6px 12px !important;
					font-size: 13px !important;
					font-weight: 500 !important;
					cursor: pointer !important;
					transition: all 0.15s ease !important;
					display: inline-flex !important;
					align-items: center !important;
					justify-content: center !important;
					box-sizing: border-box !important;
				}

				#cm-manager-dialog .cm-button:hover {
					filter: brightness(125%) !important;
					border-color: var(--primary-color, #4b7bec) !important;
					background-color: var(--comfy-menu-hover-bg, rgba(255, 255, 255, 0.1)) !important;
				}

				#cm-manager-dialog .cm-button-red {
					background-color: #88181b !important;
					border-color: #a82327 !important;
					color: white !important;
				}

				#cm-manager-dialog .cm-button-red:hover {
					background-color: #a82327 !important;
					filter: brightness(115%);
				}

				#cm-manager-dialog .cm-experimental,
				#cm-manager-dialog filedset.cm-experimental,
				#cm-manager-dialog fieldset.cm-experimental {
					border: 1px solid var(--border-color, #444) !important;
					border-radius: 8px !important;
					padding: 12px 10px 10px 10px !important;
					display: flex !important;
					flex-direction: column !important;
					gap: 8px !important;
					margin-top: 12px !important;
					box-sizing: border-box !important;
				}

				#cm-manager-dialog .cm-experimental-legend {
					font-size: 11px !important;
					font-weight: 700 !important;
					letter-spacing: 0.5px !important;
					background-color: #990000 !important;
					color: #ffffff !important;
					border-radius: 4px !important;
					padding: 2px 8px !important;
					text-align: center !important;
					margin: -22px auto 4px auto !important;
					transform: none !important;
					display: table !important;
					left: auto !important;
					position: static !important;
				}

				#cm-manager-dialog .cm-menu-combo {
					cursor: pointer !important;
					padding: 5px 8px !important;
					border: 1px solid var(--border-color, #444) !important;
					border-radius: 6px !important;
					background: var(--comfy-menu-secondary-bg, #222) !important;
					color: var(--input-text, #eee) !important;
					font-size: 13px !important;
					width: 165px !important;
					box-sizing: border-box !important;
				}

				#cm-manager-dialog .cm-menu-combo:hover {
					filter: brightness(125%) !important;
					border-color: var(--primary-color, #4b7bec) !important;
				}

				#cm-manager-dialog .setting-item {
					margin-bottom: 6px !important;
				}

				#cm-manager-dialog .setting-item > div {
					display: flex !important;
					flex-direction: row !important;
					align-items: center !important;
					justify-content: space-between !important;
					width: 100% !important;
				}

				#cm-manager-dialog .setting-item span.text-muted {
					font-size: 13px !important;
					font-weight: 500 !important;
					color: var(--input-text, #ccc) !important;
				}

				#cm-manager-dialog #workflowgallery-button {
					min-height: 46px !important;
					padding: 4px 28px 4px 8px !important;
					display: flex !important;
					flex-direction: column !important;
					justify-content: center !important;
					align-items: center !important;
				}

				#cm-manager-dialog #cm-manual-button {
					padding-right: 28px !important;
				}

				#cm-manager-dialog .cm-notice-board {
					border: 1px solid var(--border-color, #444) !important;
					border-radius: 6px !important;
					background: rgba(0, 0, 0, 0.2) !important;
					padding: 8px 12px !important;
					box-sizing: border-box !important;
				}
			`;
			document.head.appendChild(style);
		}

		// 2. DOM Enhancement Hook: Normalize elements dynamically when Manager dialog renders
		const fixDialogDOM = () => {
			const dialog = document.getElementById("cm-manager-dialog");
			if (!dialog) return;

			// Format middle column separators & buttons
			const columns = dialog.querySelectorAll(".cm-menu-column");
			if (columns.length >= 2) {
				const midColumn = columns[1];
				const emptyDivs = Array.from(midColumn.children).filter(
					(child) =>
						child.tagName === "DIV" &&
						child.children.length === 0 &&
						child.textContent.trim() === ""
				);
				emptyDivs.forEach((div) => {
					div.style.borderTop = "1px solid var(--border-color, rgba(255, 255, 255, 0.12))";
					div.style.margin = "2px 0";
					div.style.width = "100%";
					div.style.height = "1px";
					div.style.display = "block";
				});

				// Ensure all buttons in middle column have primevue standard classes
				midColumn.querySelectorAll("button.cm-button").forEach((btn) => {
					btn.classList.add("p-button", "p-component");
				});
			}
		};

		// 3. MutationObserver to catch when the dialog is inserted into the DOM
		const observer = new MutationObserver((mutations) => {
			for (const mutation of mutations) {
				for (const node of mutation.addedNodes) {
					if (node.nodeType === 1) {
						if (
							node.id === "cm-manager-dialog" ||
							node.querySelector?.("#cm-manager-dialog")
						) {
							fixDialogDOM();
						}
					}
				}
			}
		});

		observer.observe(document.body, { childList: true, subtree: true });

		// Also attach periodic/click triggers when manager buttons are pressed
		document.addEventListener("click", (e) => {
			const target = e.target;
			if (
				target?.textContent?.includes?.("Manager") ||
				target?.closest?.("button")?.textContent?.includes?.("Manager")
			) {
				setTimeout(fixDialogDOM, 50);
				setTimeout(fixDialogDOM, 200);
			}
		});
	},
});
