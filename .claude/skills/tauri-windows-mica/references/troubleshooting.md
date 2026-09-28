# Troubleshooting

## Symptom → cause → fix

| Symptom | Cause | Fix |
|---|---|---|
| Only the title bar has Mica; the page is white | `transparent` is not `true`, so WebView2 keeps its white default background. Measured: page `#ffffff` under a Mica caption. | `"transparent": true` |
| The page is a flat `#f6f6f6` / `#2f2f2f` | The create-tauri-app stylesheet paints `:root`. | Delete that background; import mica.css first. |
| The page is white although `transparent` is set | `backgroundColor` in the window config paints over Mica (measured). | Remove `backgroundColor`. |
| The desktop or other windows show through the page | No backdrop behind a transparent window. Either `windowEffects` is missing (`DWMWA_SYSTEMBACKDROP_TYPE` = 0), the effect failed silently (Windows 10), `clearEffects()` ran (= 1), or a window was created from JS without the options. | Add the effect. Keep `detectMica()` for Windows 10. Set `data-mica="off"` when clearing. Pass the options to `new WebviewWindow()`. |
| Dark Mica behind dark text, or light Mica behind white text | `micaDark` / `micaLight` tint only the backdrop; the page stays on the system scheme. | Use `"mica"` plus `"theme"` or `setTheme()`. |
| The tint flips back on its own | Same cause. tao re-applies the theme on every `WM_SETTINGCHANGE` broadcast. | Same fix. |
| White window for about 0.7 s at startup | The window is visible before WebView2 attaches. | `"visible": false` + `show()` |
| The window never appears | `visible: false` without `show()`, or `show()` rejected with "window.show not allowed…". | Call `show()` first in the entry script; add `core:window:allow-show`. |
| `setTheme` / `setEffects` reject with "not allowed" | Missing capability permission. | Add `core:window:allow-set-theme` / `core:window:allow-set-effects`. |
| A solid band across a custom title bar | `setTitlebarColor(color)` from tauri-custom-titlebar sets `DWMWA_CAPTION_COLOR` over the bar. | `setTitlebarColor(null)`, or do not call it. |
| Mica turns flat gray when the window loses focus | The inactive fallback (`#f3f3f3` / `#202020`), by design. | Nothing to fix. |
| Always flat gray, even when active | Transparency effects off, battery saver, high contrast or low-end hardware (per Microsoft's docs). | System state. The verify script prints a note when Transparency effects are off. |
| "Mica looks like plain white" in light mode | The light tint is subtle: `rgb(249,241,236)` here, against `#f3f3f3` inactive. | Check dark mode; trust the verify script. |
| Verify fails "page shows the backdrop" although the page is transparent | Nothing is bare along the page's top edge, and the page barely changes with focus (for example a full-width opaque toolbar). | Leave some bare Mica at the top (a nav pane), or confirm visually from screenshots. |
| Verify fails "tint survives WM_SETTINGCHANGE" | `micaDark` / `micaLight`. The check sends `WM_SETTINGCHANGE` to the app, so the app is now on the flipped tint. | Use `"mica"` plus `"theme"`, then rerun. |

## Testing traps

- Only automate windows you launched, and never act on another app's foreground window. The verify script finds the app by class, title and `WRY_WEBVIEW` child. It sends no input, and uses its own Tk windows as the backdrop and as the focus sink.
- Tk can re-raise its own window while it processes events. Re-assert the z-order before every screenshot, and confirm with `WindowFromPoint` that the app is on top. A raised backdrop once produced an all-magenta screenshot that read as "100% see-through".
- Compare adjacent pixels (the caption against the page right below it), not absolute colors. Mica depends on the wallpaper and the window position, and light Mica differs from the inactive fallback by only a few levels.
- The 1 px border and the rounded corners of every Win11 window blend with what is behind (about 0.7% of the frame). Exclude them from see-through checks.
- In `ctypes`, declare `argtypes` for HWND parameters: without them `HWND_TOPMOST` (-1) arrives as a 32-bit value and `SetWindowPos` fails. Compare HWNDs as plain ints.
- Do not change the Windows theme, Transparency effects or the wallpaper from a script. They are the user's global settings; ask the user to toggle them.
- In a startup measurement the first frame shows the DWM open animation blending with whatever is behind. Judge the frames after it.
