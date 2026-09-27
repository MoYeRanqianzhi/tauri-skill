# TODO

- Verify the tauri-custom-titlebar macOS section on a real Mac. See [macos-titlebar-unverified](memory/macos-titlebar-unverified.md) and [docs/poc-harness.md](docs/poc-harness.md).
- Verify on Windows 10: no `DWMWA_CAPTION_COLOR`; check that the buttons still show and the hover clears.
- Verify changing DPI at runtime by moving the window between monitors with different scales (`WM_DPICHANGED` path).
- Verify Linux on GNOME and KDE, and on Wayland (only X11 + openbox tested).
- Verify touch and pen on the caption buttons and the resize band; verify several windows at once.
