# POC and verification harness for tauri-windows-mica

This document is for agents maintaining the skill. It explains how `poc/mica-poc` and the `poc/mica_*.py` scripts prove the skill on Windows 11, and how to rerun them. Results are as of 2026-09-28: Windows 11 25H2 (26200) at 150%, WebView2 153.0.4234.48, tauri 2.12.0, wry 0.57.0, tao 0.37.1, window-vibrancy 0.8.1.

## Layout

| Path | Purpose |
|---|---|
| `poc/mica-poc/src-tauri/tauri.conf.json` | One window `"main"` with `transparent: true` and `windowEffects: ["mica"]`, plus `"create": false`. |
| `poc/mica-poc/src-tauri/src/lib.rs` | Builds `main` with `WebviewWindowBuilder::from_config`, the same call Tauri uses for config windows, after applying `POC_*` overrides to the `WindowConfig` through serde. Commands: `log`, `poc_env`, `dwm_attrs` (in-process `DWMWA_SYSTEMBACKDROP_TYPE` / `DWMWA_USE_IMMERSIVE_DARK_MODE`), and the tauri-custom-titlebar commands. |
| `poc/mica-poc/src-tauri/src/titlebar.rs`, `src/titlebar.js` | Byte-identical copies of the tauri-custom-titlebar assets, for `POC_TITLEBAR=1`. |
| `poc/mica-poc/src/mica.css`, `src/mica.js` | The originals of the skill assets; the skill holds byte-identical copies. |
| `poc/mica-poc/index.html`, `src/app.css`, `src/main.js` | Windows 11 Settings-like demo: a nav pane on bare Mica, a `--mica-layer` content area and cards. It has theme / backdrop / opaque-page controls and a status panel. It logs `[page] status {...}`, `[page] rects {...}`, `[page] mica on/off ...` and action results to stderr. |
| `poc/mica-poc/src-tauri/capabilities/default.json` | Windows `main` and `second`: `core:default` plus set-theme, set-effects, show, (un)maximize, (un)minimize and create-webview-window. |
| `poc/mica_probe.py` | Launch by PID, own Tk backdrop (magenta, then green) and focus sink, see-through share, caption-vs-page match (active and inactive), optional `WM_SETTINGCHANGE`, and screenshots after each `POC_ACTIONS` step. |
| `poc/mica_timing.py` | Startup white-flash timeline (client-area grabs for 2 s) and 12 quick `SetWindowPos` resizes with a magenta backdrop. |
| `poc/mica_verify_matrix.py` | Runs the skill's `scripts/verify_windows_mica.py` against 7 positive and 6 negative variants and checks each exit code. |
| `poc/shots/mica-*.png` | Screenshots (git-ignored). The first startup frame can contain other windows from the desktop. |

## `POC_*` switches

| Variable | Effect |
|---|---|
| `POC_TRANSPARENT=0/1` | overrides `transparent` |
| `POC_EFFECT=mica/micaDark/micaLight/tabbed/acrylic/none` | overrides `windowEffects` (`none` removes it) |
| `POC_THEME=dark/light` | window `theme` |
| `POC_DECORATIONS=0` | `decorations: false` |
| `POC_BG=#rrggbb` | window `backgroundColor` |
| `POC_VISIBLE=0` + `POC_SHOW=direct/never/(unset = rAF)` | the skill's hidden start; `direct` is what the skill ships |
| `POC_TITLE=...` | window title |
| `POC_TITLEBAR=1` | installs the tauri-custom-titlebar module and shows the page title bar |
| `POC_SECOND=1` (+ harness `POC_TARGET=second`) | the page creates a second window from JS with the same options |
| `POC_FAKE_PLATFORM_VERSION=10.0.0` | patches `NavigatorUAData.prototype.getHighEntropyValues` so `detectMica()` sees Windows 10 |
| `POC_ACTIONS=a,b,...` | page-driven steps at 5 s + 4 s·i: `theme=dark/light/system`, `backdrop=mica/tabbed/none`, `opaque=toggle`, `window=maximize/unmaximize/minimize/unminimize/second`, `caption=#rrggbb/null` |
| `POC_SETTINGCHANGE=1` (probe only) | sends `WM_SETTINGCHANGE` to the app and reports the dark-mode attribute before and after |

The skill's recipe corresponds to the default config plus `POC_VISIBLE=0 POC_SHOW=direct`. Without them the window starts visible and shows the startup flash.

## Run

1. In `poc/mica-poc`, run `npx vite build`. Kill `mica-poc.exe`, then run `cargo build` in `src-tauri`.
2. From `poc/`:
   - `python mica_verify_matrix.py`: every summary line must say `OK`;
   - `python mica_probe.py <name> [POC_*=...]` for screenshots and numbers;
   - `python mica_timing.py <name> [POC_*=...]` for startup and resize.
3. Before running, tell the user that magenta and green windows will flash right behind the app. On 2026-09-28 they stopped a run because it looked as if the app itself changed color. None of these scripts moves the mouse.
4. Combined check with tauri-custom-titlebar: launch with `POC_TITLEBAR=1`, then run that skill's `verify_windows_titlebar.py mica-poc`. This one **moves the mouse** for about 15 s.

## Last results (2026-09-28)

- Verify matrix, as expected in 13 of 13 variants:
  - pass: recipe, dark, Mica Alt, custom title bar light and dark, hidden start + `show()`, and a JS-created second window;
  - fail on the right check: `transparent: false`, no effect, `micaDark`, `backgroundColor`, opaque page CSS, and never shown.
- tauri-custom-titlebar verify on the Mica window: `ALL PASS` (20 checks). Caption-button hover on Mica went `(249,241,238)` → `(239,232,229)` and cleared.
- Runtime actions:
  - `setTheme` dark / light / system switched the tint and the page together;
  - `setEffects` tabbed → 4, `clearEffects` → 1 with 91% see-through, `setEffects` mica → 2;
  - each call failed with "not allowed" until its permission was granted;
  - `set_caption_color('#3140b8')` painted the whole bar band; `null` restored Mica.
- Window states: maximized, restored, minimized and restored again kept Mica, with 0% see-through.
- Startup: 0.6–0.8 s of pure-white client area without the hidden start; none with it.
- `decorations: false` showed Mica across the window.
- The per-state color numbers are in the skill's `references/internals.md` § Measurements.

## Not done

- No blind test. The user judged the POC matrix sufficient for this small skill (2026-09-28).
- Not run: a real Windows 10 machine, Windows 11 21H2, the `tauri.windows.conf.json` variant, a live Windows theme switch, Transparency effects off, battery saver, high contrast, and a DPI change across monitors. These are listed in [../TODO.md](../TODO.md).

## Keeping the skill honest

- After changing `mica.css` / `mica.js`: edit them in the POC, rerun the matrix, copy them to the skill and check with `cmp`.
- After changing `verify_windows_mica.py`: rerun the matrix before shipping. Thresholds matter: the shipped caption-match tolerance is ≤ 3, the value the matrix ran with.
