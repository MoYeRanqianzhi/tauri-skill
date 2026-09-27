# Troubleshooting

Every row is a failure that was reproduced during development and fixed. Each fix was confirmed with an ablation or control run on the setup listed in SKILL.md.

## Symptoms

| Symptom | Cause | Fix |
|---|---|---|
| A white block where the buttons should be; the buttons are invisible | The extended DWM frame shows only where the window's own pixels are black (alpha 0) | Keep the `WM_ERASEBKGND` black fill over the button band. |
| Buttons invisible or not reacting; no Snap Layouts | The webview (`WRY_WEBVIEW` and its WebView2 children) covers the buttons | Keep the window-region hole. If `install` returns "WRY_WEBVIEW container not found", wry renamed its container: find the new class with a window-tree dump and update `WRY_CONTAINER_CLASS`. |
| A button stays highlighted after the mouse moves into the page, and clears only when another button is hovered or the mouse leaves the window | DWM runs button hover/leave from messages it sees in `DwmDefWindowProc` | Call `DwmDefWindowProc` first for **every** message, not only `WM_NCHITTEST`. |
| Maximized: buttons are drawn but give no hover and no Snap Layouts | `WM_NCCALCSIZE` moved the client top down to the screen edge; DWM then stops hit-testing its buttons | Keep the client top at the window top when maximized. The rows pushed off-screen come back as `insets.top` / `--titlebar-top`. |
| Maximized: title bar is shorter (29.3 → 22 CSS px at 150%) | Native: Windows pushes a maximized window's top frame off-screen, and stock Win32 buttons shrink the same way | Not a bug. Size controls from `--titlebar-height`, or use the min-height variant (`frontend.md`). `WM_GETMINMAXINFO` cannot change it: Windows ignores it, and DWM hit-testing breaks. |
| Maximized: top of the title bar content is cut off | The page ignores `--titlebar-top` | Pad the title bar top by `var(--titlebar-top)`. |
| Top edge does not resize, or has no resize cursor | The client area now starts at the window top, so no `HTTOP` reaches the frame | Keep the transparent resize band (full width, `HTTOP` / `HTTOPLEFT` / `HTTOPRIGHT`). |
| Separator line under the buttons is missing, or a tooltip/popup is cut in the top-right corner | The hole clips every web layer inside the button rect | Use `box-sizing: content-box` for the title bar so its border sits below the hole. Keep popups out of the `--titlebar-right` × (`--titlebar-top` + `--titlebar-height`) corner. |
| Area behind the buttons has a different color from the title bar | The DWM caption keeps the system color | Call `setTitlebarColor(<title bar background>)` on start-up and on every theme change. Windows 10 has no caption-color attribute (not tested). |
| Page CSS switches to dark after a dark or colored title bar is set | `setTheme()` also changes WebView2's `prefers-color-scheme` | Don't call `setTheme()` to style buttons. DWM picks contrasting glyph and hover colors from the caption color by itself. |
| Title bar controls ignore clicks | Elements under `app-region: drag` never get mouse events | Mark them `app-region: no-drag`. |
| Title bar does not drag, double-click, or open the system menu | No `app-region: drag` on the bar, or it is overridden by `no-drag` | Put `app-region: drag` on the bar itself. wry enables WebView2 non-client region support, and that gives the native behaviours. |
| Linux: double-click on the bar does not maximize | `data-tauri-drag-region` starts the window manager's move grab on the first press; the second press never reaches the page | Use `enableDragRegion(bar)`: it starts the move only after 3 px of travel, and handles `dblclick` itself. |
| Linux: bar does not drag at all | WebKitGTK ignores `app-region: drag` | Use `enableDragRegion(bar)` (or `data-tauri-drag-region`), plus `core:window:allow-start-dragging`. |
| Linux: window title or size reset to "Tauri App" / 800 × 600 | `tauri.linux.conf.json` replaced the whole `windows` array | Repeat the complete window object in the platform config file. |
| Linux: edges do not resize | Window is maximized (Tauri disables the inset then), or the press is more than 5 px inside the edge | Restore first; press within 5 px of the edge. |
| Unused-variable warning or error for `app` in `setup` on non-Windows targets | `app` is only used inside `#[cfg(windows)]` | Add `let _ = app;` after the Windows block. |
| A thin translucent line along the top edge in screenshots | Windows 11's own window border; the left and right edges show the same line | Not a gap; nothing to fix. |
| Title bar buttons or inputs look oversized or shadowed | Template global styles (create-tauri-app: `button, input { padding: .6em 1.2em; box-shadow … }`, 16px/24px root font) | Scope the template CSS to `main`, or reset `padding`, `box-shadow` and `line-height` inside `.titlebar`. |
| Search box or tabs look squeezed when maximized | Fixed pixel heights inside a bar that shrinks | Use `height: min(28px, calc(var(--titlebar-height) - 8px))`, or the min-height variant. |

## Do not add

- **Removed after ablation showed no effect:**
  - re-extending the frame on `WM_ACTIVATE`;
  - `TrackMouseEvent(TME_LEAVE | TME_NONCLIENT)`;
  - a custom `WM_SETCURSOR` on the resize band;
  - a `dark` flag or `DWMWA_USE_IMMERSIVE_DARK_MODE` handling for the glyphs.
- **Tested and insufficient:** returning `HTMINBUTTON` / `HTMAXBUTTON` / `HTCLOSE` yourself while maximized. Clicks work, but DWM draws no hover and shows no Snap Layouts.
- **Not needed** (the recipe passes without them, and they were not tested): `WS_EX_NOREDIRECTIONBITMAP`, WebView2 composition hosting, or a wry fork.
- **Page-side window controls:** no `minimize()` / `toggleMaximize()` / `close()` calls, and no `core:window:*` permissions. The buttons are native.

## Testing traps

These produced false failures or real damage while the harness was being built.

| Trap | What happened | Do this |
|---|---|---|
| Acting on `GetForegroundWindow()` | The probe maximized and closed the user's browser window | Find the target by exact title, plus class `Tauri Window`, plus a `WRY_WEBVIEW` child (or by the PID you launched). |
| Alt tap to win `SetForegroundWindow` | The Alt keystroke reached whatever app was in front. It also left the target in system-menu mode: the cursor stayed an arrow, nothing hovered, and no messages reached the band | Never inject keys. Call `AttachThreadInput` to the foreground thread, then `SetForegroundWindow` and `BringWindowToTop`, as the verify script does. |
| Win32 calls through ctypes without `argtypes` | `SetWindowPos(HWND_TOPMOST)` silently failed on x64, because `-1` was passed as a 32-bit int | Declare `argtypes`, and pass `wintypes.HWND(-1)`. |
| Finding the window by title alone | An Explorer window with the same name can match | Find by class `Tauri Window` plus a unique title. |
| `ShowWindow(SW_MAXIMIZE)` from the test process | About half of the runs left the webview at its old size (black area). Plain Tauri windows do the same | Maximize and restore by clicking the real maximize button (0 of 10 failures). |
| Not DPI-aware | Coordinates and screenshots are off by the scale factor | Call `SetProcessDpiAwarenessContext(-4)` before anything else. |
| Hovering maximize and moving on | The Snap Layouts flyout covers later screenshots | Send Escape after each maximize hover. |
| First hover right after programmatic activation | Sometimes no highlight was captured | Take the evidence from later samples. |
| Checking the cursor without moving the mouse | No `WM_SETCURSOR` is sent, so the reading is stale | Move onto the target point before reading `GetCursorInfo`. |
| `pkill -f <binary path>` inside a remote ssh command | It matched the ssh session's own command line and killed it (exit 255) | Use `pkill -x <process name>`. |
| Linux on Xvfb without an a11y bus | GTK waited up to ~25 s for AT-SPI before mapping the window | Set `NO_AT_BRIDGE=1`. Wait for both the mapped window and the page's first log line before acting. |
| Clicking "the bar" at a computed point | The point landed on a `no-drag` menu button, so the drag was a false negative | Log the `mousedown` target, and pick points from measured element rects. |
| Assuming window state between steps | A step toggled maximize in the wrong direction; the resize tests then ran while maximized | Read the state (`IsZoomed`, `_NET_WM_STATE`) before each step. |
| Top-edge resize dragged up to the screen top | Windows vertical-maximized the window (native), so the resulting size looked wrong | Start edge-drag tests well away from the screen edges. |
