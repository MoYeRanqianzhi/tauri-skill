# TODO

- Verify the tauri-custom-titlebar macOS section on a real Mac. See [macos-titlebar-unverified](memory/macos-titlebar-unverified.md) and [docs/poc-harness.md](docs/poc-harness.md).
- Verify on Windows 10: no `DWMWA_CAPTION_COLOR`; check that the buttons still show and the hover clears.
- Verify changing DPI at runtime by moving the window between monitors with different scales (`WM_DPICHANGED` path).
- Verify Linux on GNOME and KDE, and on Wayland (only X11 + openbox tested).
- Verify touch and pen on the caption buttons and the resize band; verify several windows at once.
- tauri-windows-mica on a real Windows 10 machine: `detectMica()` must return off and nothing may be see-through; and on Windows 11 21H2, where window-vibrancy uses the undocumented `DWMWA_MICA_EFFECT`. See [docs/mica-poc-harness.md](docs/mica-poc-harness.md).
- tauri-windows-mica manual checks, which need the user because scripts must not change global settings: a live Windows theme switch, Transparency effects off, battery saver, high contrast.
- tauri-windows-mica: run the `tauri.windows.conf.json` variant of the recipe, and a DPI change across monitors.
