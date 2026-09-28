# How Tauri applies Mica, and what changes it

Source references are to tauri 2.12.0, tao 0.37.1, wry 0.57.0 and window-vibrancy 0.8.1.

## The chain

1. Config windows are built with `WebviewWindowBuilder::from_config` (`tauri/src/app.rs`, `setup`).
2. `transparent: true` changes two layers:
   - tao calls `DwmEnableBlurBehindWindow` with an empty region, so DWM honors the window's per-pixel alpha (`tao/src/platform_impl/windows/window.rs`, `on_create`);
   - wry sets the WebView2 `DefaultBackgroundColor` to transparent, and ignores `backgroundColor` for the webview (`wry/src/webview2/mod.rs`).
3. Once the window exists, Tauri applies `windowEffects` on the main thread (`tauri/src/window/mod.rs`). That calls `window_vibrancy::apply_mica` (`tauri/src/vibrancy/windows.rs`):
   - on build 22523 or newer it sets `DWMWA_SYSTEMBACKDROP_TYPE` to `DWMSBT_MAINWINDOW` (2), or `DWMSBT_TABBEDWINDOW` (4) for Mica Alt;
   - on builds 22000–22522 it sets the undocumented `DWMWA_MICA_EFFECT` (1029) instead (not verified);
   - on older builds it returns an error. Tauri discards it (`match effect { … };` and `let _ = set_window_effects(…)`), and nothing is logged.
4. Only the first Windows effect in `effects` is used. There is no fallback chain: `["mica", "acrylic"]` does not fall back to Acrylic on Windows 10.
5. DWM draws the backdrop behind the whole window, and the transparent webview lets it through.

## Tint and theme

- The Mica tint follows `DWMWA_USE_IMMERSIVE_DARK_MODE` (20).
- tao sets that attribute from the window theme: `theme` in the config, `setTheme()`, or the system (`tao/src/platform_impl/windows/dark_mode.rs`, `try_window_theme`).
- On **every** `WM_SETTINGCHANGE`, tao re-applies it, unless the window or the app has a preferred theme (`event_loop.rs`, `update_theme`).
- `micaDark` / `micaLight` set the attribute once, inside `apply_mica(Some(dark))`. Measured on a light system:
  - the page's `prefers-color-scheme` stayed `light` under dark Mica;
  - one `WM_SETTINGCHANGE` flipped the attribute from 1 to 0.
  - With `"theme": "Dark"` instead, it stayed 1.
- The page's `prefers-color-scheme` follows the window theme. `setTheme('dark')` switched it and the Mica tint together (measured).

## Startup flash

Measured by grabbing the client area every 60 ms or so after the window appeared:

| Variant | White frames |
|---|---|
| Recipe without `visible: false`, light | 0.09–0.63 s, with 97–100% of the client area pure white |
| Same, dark theme | 0.08–0.77 s |
| `visible: false` + `show()` called directly by the page script | none, light and dark |
| `visible: false` + `show()` in `requestAnimationFrame` | none |

The measurements are the facts. The likely cause is an inference: the window is shown before the asynchronously created WebView2 controller is attached, and the unpainted window surface appears white.

A hidden Tauri window still reports `document.visibilityState === 'visible'`, so the page's scripts and `requestAnimationFrame` run normally before `show()`.

## Runtime changes

These are JS calls on `getCurrentWindow()`; the effects were measured:

| Call | Permission | Effect |
|---|---|---|
| `setTheme('dark' \| 'light' \| null)` | `core:window:allow-set-theme` | The tint and the page's `prefers-color-scheme` switch together. `null` follows Windows. |
| `setEffects({ effects: [Effect.Mica] })` (or `Effect.Tabbed`) | `core:window:allow-set-effects` | The backdrop switches; the page is untouched. |
| `clearEffects()` | `core:window:allow-set-effects` | Sets `DWMSBT_NONE`: 91% of the window became see-through. Set `data-mica="off"` first. |
| `show()` | `core:window:allow-show` | Needed with `visible: false`. |

Without the permission the promise rejects, for example with `window.set_theme not allowed. Permissions associated with this command: core:window:allow-set-theme`.

## More windows

- Windows created from JS take the same options: `new WebviewWindow('settings', { transparent: true, windowEffects: { effects: [Effect.Mica] }, … })`. This was verified on Windows with Tauri 2.12. In tauri-apps/tauri#13422 the options were ignored, but that report was for macOS and has a linked fix.
- The new label needs a capability (`"windows": ["main", "settings"]`) and `core:webview:allow-create-webview-window`. With `visible: false`, its page must call `show()` too.

## Measurements

Windows 11 25H2 at 150%, one wallpaper:

| State | Caption / bare Mica | Page on `--mica-layer` |
|---|---|---|
| Mica, light, active | `rgb(249,241,236)` | `rgb(252,248,246)` |
| Mica, light, inactive | `#f3f3f3` | `#f9f9f9` |
| Mica, dark, active / inactive | `rgb(36,31,28)` / `#202020` | – |
| Mica Alt, light, active / inactive | `rgb(227,215,208)` / `#e8e8e8` | – |
| Mica Alt, dark, active / inactive | `rgb(19,7,0)` / `#202020` | – |

- With the recipe, 0.00% of the frame was see-through. The border and rounded corners blend with what is behind on every window, about 0.7%.
- Maximized, minimized and restored: the backdrop stayed Mica and nothing was see-through.
- 12 quick `SetWindowPos` resizes (+40×25 px each): nothing was see-through. Strips the webview had not reached yet showed Mica. One frame had a thin black strip at the growing edge (0.5%).
- `DWMWA_SYSTEMBACKDROP_TYPE` and `DWMWA_USE_IMMERSIVE_DARK_MODE` can be read from another process with `DwmGetWindowAttribute`. The verify script relies on this.
