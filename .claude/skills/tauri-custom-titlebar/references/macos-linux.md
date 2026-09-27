# macOS and Linux

**Not verified locally.** Everything here comes from Tauri 2.12 source and docs, checked 2026-09-27. Tell the user it is untested, and verify it on the target platform before you call it done.

Use the same markup as `frontend.md`. The Windows helpers do nothing on these platforms.

## Per-platform config

Tauri merges `tauri.macos.conf.json`, `tauri.linux.conf.json` and `tauri.windows.conf.json` over `tauri.conf.json`. Put platform-only window settings there, instead of branching in code.

## macOS: Overlay title bar

```json
{ "app": { "windows": [{
  "label": "main",
  "titleBarStyle": "Overlay",
  "hiddenTitle": true,
  "trafficLightPosition": { "x": 16, "y": 20 }
}] } }
```

- **`titleBarStyle`** accepts `"Visible"`, `"Transparent"` or `"Overlay"`. With `"Overlay"`, the page extends under the title bar and the system draws the traffic lights over it. These settings are ignored on Windows (verified: the Windows verification script still passes with them set).
- **`hiddenTitle: true`** hides the system title text.
- **`trafficLightPosition`** is a logical position. It requires `"Overlay"` and `decorations: true`, and was added in Tauri 2.4.0 (the builder equivalent is `WebviewWindowBuilder::traffic_light_position`).
- **Reserve space for the traffic lights:** pad the bar's left edge, for example `padding-left: 78px` on macOS, and measure it against your `trafficLightPosition`. The system title bar height differs between macOS versions (Tauri docs), so do not hard-code the button center; measure it.
- **Drag region:** WKWebView does not implement `app-region`. Add `data-tauri-drag-region` to the bar, with the permissions `core:window:allow-start-dragging` and `core:window:allow-internal-toggle-maximize`. Tauri's `drag.js` handles macOS double-click maximize on mouseup and cancels it if the mouse moved.
- **The app menu belongs in the system menu bar** (Tauri menu API), not in the page.
- **Known issues:**
  - Setting the title resets the traffic-light position (tauri-apps/tauri#13044).
  - `trafficLightPosition` does not work with the `unstable` feature (tauri-apps/tauri#14072).
  - In Overlay mode the window cannot be dragged while it is unfocused (tauri-apps/tauri#9503, #4316).

## Linux

- **`decorations: true` (recommended default).** The window manager or GTK draws the frame. Web content cannot enter the server-side title bar; that is a platform boundary, not a missing API.
- **`decorations: false`** (put it only in `tauri.linux.conf.json`). You draw the whole bar, including the buttons: `getCurrentWindow().minimize()`, `.toggleMaximize()` and `.close()`, with `core:window:allow-minimize`, `allow-toggle-maximize`, `allow-close`, `allow-start-dragging` and `allow-internal-toggle-maximize`.
  - Tauri provides:
    - drag through `data-tauri-drag-region` (GTK `begin_move_drag`);
    - double-click maximize;
    - edge resizing through a 5px inset handled on the webview (`tauri-runtime-wry/src/undecorated_resizing.rs`).
  - You do not get a system menu, snap integration or a shadow (`shadow` is unsupported on Linux).
- **Wayland:** tao 0.36 (tao#1218) fixed `decorations: false` being ignored on KDE. Changing decorations on a window that already exists is still unsupported on Wayland.
