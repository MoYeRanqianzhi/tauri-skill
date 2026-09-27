---
name: tauri-custom-titlebar
description: Build a custom title bar for a Tauri 2 app, where web content (menus, tabs, search) fills the title bar strip while Windows keeps its real caption buttons, with Snap Layouts on hover, native hover and press, the system menu, double-click maximize, Aero Snap drag and edge resizing. Ships verified Rust and JS files plus a verification script. Use whenever the user wants a custom, frameless, overlay or "Electron titleBarOverlay"-style title bar in Tauri, custom window controls or decorations, or content inside the title bar. Also use when they report missing Snap Layouts, stuck caption-button hover, buttons hidden behind the webview, broken top-edge resize, or wrong title bar height when maximized. Windows is verified. macOS and Linux configuration is included.
---

# Tauri custom title bar

On Windows, keep the native frame. Remove only the caption, let DWM keep drawing and hit-testing its real minimize/maximize/close buttons, and let web content fill the rest. This keeps Snap Layouts, native hover and press, the system menu, double-click maximize, Aero Snap and every resize edge. Neither Tauri nor WebView2 has an API for this (tauri-apps/tauri#4531 is still open). The verified implementation is in `assets/`.

## Choose the approach

- **Windows, app content in the title bar:** follow the recipe below. Do not use `decorations: false` and do not draw HTML caption buttons.
- **Buttons must be custom-drawn:** use `decorations: false` + HTML buttons + `data-tauri-drag-region`. Before building it, tell the user they lose the Snap Layouts flyout, native hover and the system menu. See `references/windows.md` §4.
- **macOS / Linux:** see `references/macos-linux.md`. Both use the same frontend markup.

## Windows recipe

1. **Config:** leave `decorations` at its default (`true`). `"titleBarStyle": "Overlay", "hiddenTitle": true` (for macOS) is harmless on Windows.
2. **Rust:** copy `assets/windows_titlebar.rs` to `src-tauri/src/titlebar.rs` unchanged. Add the dependency, using the same `windows` version as Tauri (`cargo tree -p wry --depth 1`; Tauri 2.12 uses 0.62):

   ```toml
   [target.'cfg(windows)'.dependencies]
   windows = { version = "0.62", features = [
     "Win32_Foundation", "Win32_Graphics_Dwm", "Win32_Graphics_Gdi", "Win32_System_LibraryLoader",
     "Win32_UI_Controls", "Win32_UI_HiDpi", "Win32_UI_Shell", "Win32_UI_WindowsAndMessaging",
   ] }
   ```

   ```rust
   #[cfg(windows)]
   mod titlebar;
   // in run():
   .setup(|app| {
       #[cfg(windows)]
       {
           use tauri::Manager;
           titlebar::install(&app.get_webview_window("main").expect("main window"))?;
       }
       Ok(())
   })
   .invoke_handler(tauri::generate_handler![
       #[cfg(windows)] titlebar::titlebar_insets,
       #[cfg(windows)] titlebar::set_caption_color,
   ])
   ```

   `serde` with `derive` must be a dependency (the template has it). No capability or `core:window:*` permission is needed.
3. **Frontend:** copy `assets/titlebar.js`, call `watchTitlebarInsets()` once, and call `setTitlebarColor(<title bar background>)` on every theme change. Lay out the title bar exactly as in `references/frontend.md`.
4. **Verify before reporting success:** run `python scripts/verify_windows_titlebar.py "<window title>"` against the running app. It needs Pillow and moves the real mouse for about 15 s, so warn the user first. It must print `ALL PASS`. Then walk through the manual checklist in `references/windows.md` §5.

## Hard rules

Breaking any of these reproduces a bug that was already hit and fixed. `references/troubleshooting.md` lists each symptom with its cause.

- **Don't trim the Rust module.** Every part is load-bearing: `DwmDefWindowProc` runs first for **every** message, the black `WM_ERASEBKGND` fill, the region hole in `WRY_WEBVIEW`, the top resize band, and leaving the client top unmoved when maximized.
- **Size the title bar from `--titlebar-height`, never a fixed height.** It is about 22 CSS px shorter when maximized; that is native Windows behaviour. Controls inside must scale with it too.
- **Mark interactive children `app-region: no-drag`.** Nothing drawn inside the top-right button rect is visible, including borders, shadows and popups.
- **Color the buttons with `setTitlebarColor` only.** Calling `setTheme()` for that also flips the page's `prefers-color-scheme`.
- **Test automation acts only on the app's own window.** Maximize with real clicks, not `ShowWindow`.

## Verified scope

- **Verified:** Windows 11 25H2, 150% scale, WebView2 153, tauri 2.12.0 / wry 0.57.0 / tao 0.37.1 / windows 0.62.2, verified 2026-09-27.
- **Not verified:**
  - Windows 10;
  - moving between monitors with different DPI;
  - touch or pen input;
  - several windows;
  - macOS and Linux.

State the unverified parts when they matter. `install` depends on wry's `WRY_WEBVIEW` container class, so rerun the verification script after any Tauri or wry upgrade.

## References

- `references/frontend.md`: the layout contract, a complete example, sizing large controls, colors and themes.
- `references/troubleshooting.md`: symptom, cause and fix for every known failure; code that must not be added; testing traps.
- `references/windows.md`: how the Win32 side works, measurements, ruled-out alternatives, the verification checklist.
- `references/macos-linux.md`: macOS Overlay title bar and Linux options.
