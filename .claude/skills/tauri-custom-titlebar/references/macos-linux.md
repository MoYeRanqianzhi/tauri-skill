# macOS and Linux

Use the same markup as `frontend.md`. The Windows helpers (`watchTitlebarInsets`, `setTitlebarColor`) do nothing on these platforms, so the CSS fallbacks apply.

## Per-platform config: repeat the whole window object

Tauri merges `tauri.linux.conf.json`, `tauri.macos.conf.json` and `tauri.windows.conf.json` over `tauri.conf.json` as a JSON merge patch. **Arrays are replaced, not merged.** Verified on Linux: a `tauri.linux.conf.json` containing only `{"app":{"windows":[{"decorations":false}]}}` produced a window titled "Tauri App" at the default 800 × 600, losing the configured title and size. Copy the complete window object and change only what differs:

```json
{ "app": { "windows": [{ "title": "My App", "width": 900, "height": 600, "decorations": false }] } }
```

Put platform-only permissions in a capability file with `"platforms": ["linux"]` (or `["macOS"]`).

## Linux

**Verified** on Ubuntu 24.04, X11 (Xvfb + openbox), WebKitGTK 2.52.6, tauri 2.12.0, verified 2026-09-27. GNOME, KDE and Wayland were not tested.

### `decorations: true` (default)

The window manager draws its own title bar. The page's title bar renders as a toolbar row below it, using the CSS fallback height. Web content cannot enter a server-side title bar; this is a platform boundary, not a missing API.

### `decorations: false` (the page draws everything)

Set this in `tauri.linux.conf.json` with the full window object, then draw your own buttons.

```json
{ "identifier": "linux-window-controls", "platforms": ["linux"], "windows": ["main"],
  "permissions": ["core:window:allow-minimize", "core:window:allow-toggle-maximize",
                  "core:window:allow-close", "core:window:allow-start-dragging"] }
```

```js
import { getCurrentWindow } from '@tauri-apps/api/window';
import { isWindows, enableDragRegion } from './titlebar.js';

const appWindow = getCurrentWindow();
if (!isWindows && !(await appWindow.isDecorated())) {
  showOwnControls();                       // render your min / max / close buttons
  minBtn.onclick = () => appWindow.minimize();
  maxBtn.onclick = () => appWindow.toggleMaximize();
  closeBtn.onclick = () => appWindow.close();
  enableDragRegion(document.querySelector('.titlebar'), appWindow);
}
```

Leave space on the right for the buttons. The fallback `var(--titlebar-right, 8px)` from `frontend.md` keeps them off the edge.

| Behaviour | Result |
|---|---|
| Minimize / maximize-restore / close through `minimize()` / `toggleMaximize()` / `close()` | Works |
| Drag with `enableDragRegion(bar)` | Works (moves after 3 px of travel) |
| Double-click the bar with `enableDragRegion(bar)` | Maximizes / restores |
| Drag with `data-tauri-drag-region` | Works |
| Double-click with `data-tauri-drag-region` | **Does nothing.** The first press starts the window manager's move grab, so the second press never reaches the page (only a `detail=1` mousedown was logged). This is why `enableDragRegion` exists. |
| `app-region: drag` | Ignored by WebKitGTK; no drag |
| Edge resize | Works from the 5 px inset that Tauri adds on the webview (`undecorated_resizing.rs`): right and top edges verified. Disabled while maximized, by design. |
| Right-click on the bar | WebKit's page context menu (Back / Forward / Reload / Inspect Element); there is no system menu. Suppress it with a `contextmenu` handler if needed (not tested). |
| Shadow, snap integration, system menu | Not available (`shadow` is unsupported on Linux) |

**Wayland** (from source, not tested): tao 0.36 (tao#1218) fixed `decorations: false` being ignored on KDE. Changing decorations on a window that already exists is still unsupported on Wayland.

## macOS

**Not verified.** No Mac was available. Everything below comes from Tauri 2.12 source and docs, checked 2026-09-27. Tell the user it is untested, and verify it on a Mac before calling it done.

```json
{ "app": { "windows": [{
  "title": "My App", "width": 900, "height": 600,
  "titleBarStyle": "Overlay", "hiddenTitle": true,
  "trafficLightPosition": { "x": 16, "y": 20 }
}] } }
```

- **`titleBarStyle`** accepts `"Visible"`, `"Transparent"` or `"Overlay"`. With `"Overlay"`, the page extends under the title bar and the system draws the traffic lights over it. These keys are ignored on Windows (verified: the Windows verification script still passes with them set).
- **`hiddenTitle: true`** hides the system title text.
- **`trafficLightPosition`** is a logical position. It requires `"Overlay"` and `decorations: true`, and was added in Tauri 2.4.0 (the builder equivalent is `WebviewWindowBuilder::traffic_light_position`).
- **Reserve space on the left for the traffic lights**, for example `padding-left: 78px`, and measure it against your `trafficLightPosition`. The system title bar height varies across macOS versions (Tauri docs).
- **Drag region:** WKWebView does not implement `app-region`. Use `data-tauri-drag-region` (Tauri's `drag.js` maximizes on mouseup on macOS and cancels if the mouse moved) or `enableDragRegion`, plus `core:window:allow-start-dragging`. Which one behaves better on macOS is unverified.
- **The app menu belongs in the system menu bar** (Tauri menu API).
- **Known issues:**
  - Setting the title resets the traffic-light position (tauri-apps/tauri#13044).
  - `trafficLightPosition` does not work with the `unstable` feature (tauri-apps/tauri#14072).
  - The window cannot be dragged while it is unfocused in Overlay mode (tauri-apps/tauri#9503, #4316).
