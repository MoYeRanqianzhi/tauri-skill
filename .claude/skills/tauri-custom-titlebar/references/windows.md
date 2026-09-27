# Windows: how the recipe works

This covers the design behind `assets/windows_titlebar.rs`: what each part does, the measurements it depends on, the alternatives that were ruled out and why, and how to verify it. Measurements come from Windows 11 25H2 at 150% scale unless noted.

## Contents

1. Window structure
2. Message handling
3. Geometry and native parity
4. Ruled-out alternatives
5. Verification
6. Limits and upgrades

## 1. Window structure

After `install`, the tree looks like this. It was dumped with `EnumChildWindows` / `GetWindow`.

```
Tauri Window                     tao top-level: native frame kept, subclassed by titlebar.rs
├─ TAURI_TITLEBAR_TOP_RESIZE     transparent band, full width, 9 px tall; hidden while maximized
└─ WRY_WEBVIEW                   wry container; window region = client area minus the caption-button rect
   └─ Chrome_WidgetWin_0         WebView2 host (the browser-process windows sit below it)
      └─ Chrome_WidgetWin_0      WebView2's own overlay over `app-region: drag` areas
```

Two facts make this work:

- **wry parents the WebView2 controller to an in-process container** (`WRY_WEBVIEW`, created in `wry/src/webview2/mod.rs::create_container_hwnd`). A window region on that container also clips every WebView2 child window. Cutting a hole there reveals the top-level window's own pixels.
- **Tauri already uses this "child HWND with a region" pattern.** Its undecorated-resize border (`TAURI_DRAG_RESIZE_BORDERS` in `tauri-runtime-wry/src/undecorated_resizing.rs`) works the same way.

## 2. Message handling

`subclass_proc` runs before wry's and tao's handlers, because the subclass is installed last.

| Message | Handling | Why |
|---|---|---|
| every message | `DwmDefWindowProc` first; return its result if it handled the message | DWM runs the caption buttons' hover, press and leave state from these messages. Calling it only for `WM_NCHITTEST` left buttons highlighted after the mouse moved into the page: reproduced 2 of 3 buttons stuck before the fix, 0 of 15 after. |
| `WM_NCCALCSIZE` (wParam=TRUE) | Let the default compute the rect, then restore `rgrc[0].top` | Removes the caption and top border. Side and bottom borders stay native, which keeps the shadow, resize edges and Win11 rounded corners. |
| `WM_NCHITTEST` | Default first. `HTCLIENT` becomes `HTCAPTION` | Only the button hole reaches this window, and DWM has already claimed the buttons. |
| `WM_ERASEBKGND` | Fill the button band with `BLACK_BRUSH` | The extended DWM frame shows only through black (alpha 0) pixels. The ablation without it showed a white block with no buttons. |
| `WM_SIZE`, `WM_DPICHANGED` | Default, then `refresh()` | Button bounds, region, frame extent and band size depend on size, DPI and maximized state. |

`refresh()` does three things:

1. It calls `DwmExtendFrameIntoClientArea` with `cyTopHeight` equal to the bottom of the buttons.
2. It calls `SetWindowRgn(WRY_WEBVIEW, client minus buttons)`. The system owns the region handle afterwards.
3. It positions the resize band, and hides it while maximized.

**The resize band** returns `HTTOP`, or `HTTOPLEFT`/`HTTOPRIGHT` within one band-height of either end. It forwards `WM_NCLBUTTONDOWN` / `WM_NCLBUTTONDBLCLK` to the top-level window, so the system runs its native size loop. Double-clicking the top edge also triggers vertical maximize. The band never paints, so the webview and the DWM buttons stay visible under it.

**Two commands** are exposed:

- `titlebar_insets` returns `{top, height, right}` in CSS px:
  - `top` is the rows hidden above the work area while maximized;
  - `height` is the visible button height;
  - `right` is the width of the button block.
- `set_caption_color(color | null)` sets `DWMWA_CAPTION_COLOR`. DWM then picks glyph and hover colors by contrast. Measured on a `#3140b8` caption: glyph luminance was 255 (white) whether `DWMWA_USE_IMMERSIVE_DARK_MODE` was 0 or 1; on `#f3f3f3` it was 0 (black) either way.

**Why not `setTheme()` for the glyphs:** in `tauri-runtime-wry`, a window `ThemeChanged` event calls `webview.set_theme`, which is `ICoreWebView2Profile::SetPreferredColorScheme` in wry. That flips the page's `prefers-color-scheme`. `setTheme()` is still fine when the user's real light/dark choice should drive the whole page.

## 3. Geometry and native parity

All figures are in physical px at 150%. CSS px = physical / 1.5.

| Quantity | This recipe | Stock Win32 window (Tk) |
|---|---|---|
| Caption buttons, restored | 220 × 44 (`insets.right` 146, `height` 29.33 CSS px) | 220 × 44 |
| Visible button height, maximized | 33 (`insets.top` 7.33 + `height` 22 CSS px) | 33 |
| Maximized window rect | (-11, -11, 2571, 1539) on a 2560 × 1528 work area | same |
| Top resize band | 9 (= invisible side border, `DWMWA_EXTENDED_FRAME_BOUNDS.left - GetWindowRect.left`) | 9 (`HTTOP` for y 0–8, `HTCAPTION` from 9) |
| Top corners | band-height wide | about 9–10 wide |
| Top band above the buttons | `HTTOP` | `HTTOP` (buttons start below the band) |

- **The title bar is shorter when maximized.** This is native behaviour. Windows places a maximized window's frame off-screen and DWM keeps its button rect relative to the window, so the top 11 px are hidden. It was verified against a stock window.
- **`WM_GETMINMAXINFO` cannot change this.** Setting `ptMaxPosition`/`ptMaxSize` to the work area was tested: Windows still put the window at (-11, -11), and DWM stopped hit-testing its buttons.

## 4. Ruled-out alternatives

| Alternative | Result | Evidence |
|---|---|---|
| `decorations: false` + HTML buttons | No Snap Layouts flyout, no native hover or press, no system menu | tauri-apps/tauri#4531 is open. Maintainers say `WM_NCHITTEST` never reaches the window over the webview. |
| tauri-plugin-decorum | Presses Win+Z (via enigo) on hover to fake the flyout. The flyout is misplaced and does not close. | Plugin source (`src/commands.rs`); plugin issue #29 |
| WebView2 composition hosting (the previous version of this skill) | Needs a wry fork; not merged upstream | tauri-apps/wry#1762 is open (2026-09) |
| WebView2 `app-region` MINIMIZE/MAXIMIZE/CLOSE or Window Controls Overlay | Composition hosting only; WCO is prerelease SDK only | WebView2 `ICoreWebView2CompositionController4` docs; tauri-apps/wry#1650 |
| Moving the client top down to the screen edge when maximized | Buttons are drawn, but DWM does not hit-test them: no hover, no Snap Layouts | Local test: `WM_NCHITTEST` returned `HTCAPTION` over every button |
| Returning `HTMAXBUTTON` etc. yourself while maximized | Clicks work, but DWM draws no hover | Local test (pixel unchanged on hover) |
| Invisible native child over an HTML maximize button (e.g. dunkyl/tauri-snap-layout, Zbrooklyn/tauri-snap-layouts) | Reportedly gives the flyout for custom-drawn buttons | Not tested here. Consider it only when the buttons must be custom-drawn. |

## 5. Verification

### Automated

`scripts/verify_windows_titlebar.py "<title>"` checks:

- the band and region exist;
- the `WM_NCHITTEST` result for each button, restored and maximized;
- that `WindowFromPoint` over each button is the top-level window and not the webview;
- the top edge hit code;
- that hover clears after sliding into the page;
- maximize and restore with real clicks.

It exits with code 0 only if every check passes. A negative control (running without `install`) reported 7 failures.

### Manual checklist (not covered by the script)

- [ ] Hovering maximize shows the Snap Layouts flyout, both restored and maximized.
- [ ] Dragging the title bar moves the window. Dragging to the left screen edge snaps it to the left half.
- [ ] Double-clicking the title bar maximizes and restores.
- [ ] Right-clicking the title bar opens the system menu, and so does Alt+Space.
- [ ] Title bar buttons and inputs receive clicks and focus.
- [ ] Minimize minimizes. Close closes (the process exits if it is the last window).
- [ ] Deactivating the window dims the button glyphs, and the page dims its own title text if designed to.
- [ ] Every theme: the area behind the buttons matches the title bar color. There is no seam or white block.
- [ ] Maximized: no title bar content is cut off at the top; controls fit the shorter bar.
- [ ] The window resizes from all four edges and all four corners.

All of these passed on the verified setup.

### Harness pitfalls

Automation traps are listed in `troubleshooting.md` § Testing traps. Two of them caused damage or false results here: acting on the foreground window, and the Alt-tap menu mode.

## 6. Limits and upgrades

- **Windows 10 is not tested.** `DWMWA_CAPTION_COLOR` does not exist there, so the button area keeps the system caption color.
- **Changing DPI at runtime (moving to another monitor) is not tested.** `WM_DPICHANGED` triggers `refresh`, and the page gets a `resize` event.
- **Several windows** should work, since the band class is shared and the subclass is per window, but this is not tested. **Several webviews in one window** (Tauri's `unstable` multi-webview): only the first `WRY_WEBVIEW` gets the hole. Not tested.
- **The container class is wry's `WRY_WEBVIEW`.** `install` returns an error if it is missing. After upgrading Tauri, wry or WebView2, rerun the verification script and the checklist.
