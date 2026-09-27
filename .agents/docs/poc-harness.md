# POC and verification harness for tauri-custom-titlebar

This document is for agents maintaining the skill. It explains how `poc/` proves the skill's code works on each platform, and how to rerun that proof. Results recorded here are as of 2026-09-27.

## Layout

| Path | Purpose |
|---|---|
| `poc/titlebar-poc/` | Tauri 2.12 app (Vite frontend, `withGlobalTauri: false`). Consumes the skill assets as byte-identical copies: `src-tauri/src/titlebar.rs` and `src/titlebar.js`. |
| `poc/titlebar-poc/index.html`, `src/main.js` | Demo page: modern minimal title bar, 5 themes (light, dark, indigo, emerald, sand), a min-height toggle, and Linux self-drawn controls. It logs `[page] rects {...}` (element rects in device px) and `[page] insets ...` to stderr through the `log` command. |
| `poc/titlebar-poc/src-tauri/src/lib.rs` | Installs the title bar. Extra commands: `log` and `poc_env(name)`. `POC_NO_TITLEBAR=1` skips `install` (baseline / negative control). `POC_DRAG=tauri\|threshold\|none` selects the Linux drag mode. |
| `poc/titlebar-poc/src-tauri/tauri.linux.conf.json`, `capabilities/linux.json` | Linux: `decorations: false` with the full window object, plus the window-control permissions. |
| `poc/probe.py` | Win32 helpers (DPI aware): window tree, `WM_NCHITTEST`, `WindowFromPoint`, real mouse input, screenshots, `launch(env)`, `rects(h)`. |
| `poc/*.py` (Windows) | Focused checks: `hoverstats.py` (hover shown / stuck per button), `matrix.py` (resize band, drag, clicks, double-click, maximized hits, system menu), `edges.py` / `cursorpath.py` / `cursortimeline.py` (resize band cursor and hit codes), `basics.py` (minimize, Aero Snap to the left edge, Alt+Space, close), `themes.py` (5 themes × active / inactive / maximized strip), `glyphs.py` (caption glyph contrast), `ablate.py` (screenshots for ablations), `clickmax.py` / `blacktest.py` (maximize race). |
| `poc/linux_matrix.py` | X11 checks through `xdotool` / `xprop` / `scrot`: drag, double-click, max toggle, edge and corner resize, minimize, right-click screenshot, close, and app-region-only drag. |
| `poc/shots/` | Screenshots (git-ignored). |

## Windows run

1. `cd poc/titlebar-poc`, then `npx vite build`.
2. Kill `titlebar-poc.exe`, then run `cargo build` in `src-tauri`.
3. From `poc/`:
   - `python -c "import probe as p; p.launch()"`;
   - `python ../.claude/skills/tauri-custom-titlebar/scripts/verify_windows_titlebar.py titlebar-poc` (expect `ALL PASS`);
   - `python hoverstats.py 4`, `python matrix.py`, `python basics.py`, `python themes.py`.

Last results (Win11 25H2, 150%): verify `ALL PASS`, and the negative control (`POC_NO_TITLEBAR=1`) reported 7 failures. The matrix passed except for artifacts explained in the skill's troubleshooting § Testing traps. Themes showed the caption area matching in every state.

## Linux run (any X11 host with a desktop)

Requirements: Rust, the WebKitGTK 4.1 dev packages, `xdotool`, `xprop`, `xwininfo`, `scrot` and `python3`. Node is not needed on the host.

1. Build `dist/` locally with `npx vite build`.
2. Copy `poc/titlebar-poc` to the host without `src-tauri/target`, `node_modules` or `src-tauri/gen`, and run `cargo build` in `src-tauri`. The first build takes about 4 minutes on 10 cores.
3. Run `DISPLAY=:<n> python3 linux_matrix.py <app dir>`, and again with `MODE=threshold`.
   - The script sets `NO_AT_BRIDGE=1`. Without an a11y bus, GTK can wait about 25 s before mapping the window.
   - Kill the app with `pkill -x titlebar-poc`. `pkill -f` matches the remote shell's own command line.

Last results (Ubuntu 24.04, Xvfb + openbox, WebKitGTK 2.52.6):

| Mode | Drag | Double-click | Buttons | Edge resize |
|---|---|---|---|---|
| `POC_DRAG=tauri` | (120, 60) | did not maximize (only a `detail=1` mousedown reached the page) | worked | right and top worked |
| `POC_DRAG=threshold` (`enableDragRegion`) | (112, 56) | maximized | worked | worked |
| `POC_DRAG=none` (app-region only) | (0, 0) | – | – | – |

Right-click showed WebKit's page context menu.

## Blind test (does the skill alone prevent the pitfalls?)

Run this after any substantial skill change.

1. Give a fresh subagent only the skill directory. Forbid reading `poc/`, because that would spoil the test.
2. Have it create a new create-tauri-app project in a new, git-ignored directory (`poc-blind/`), implement the title bar from the skill alone, run `scripts/verify_windows_titlebar.py`, take a screenshot, and report every friction point.
3. Speed up builds with `CARGO_TARGET_DIR` inside that directory.

Last run (2026-09-27, template `vanilla-ts`): `ALL PASS` on the first try, with the Rust module unchanged. The friction points it reported were fixed:
- TS7016 on `titlebar.js`: `assets/titlebar.d.ts` added, verified under `strict` without `allowJs`, including a `@ts-expect-error` probe;
- merging `generate_handler!` instead of replacing it;
- the window label;
- template CSS leaking into the bar;
- the manual checklist needing a human;
- the verify script's Alt/Escape keystrokes and unchecked clicks: rewritten with `AttachThreadInput` and ownership checks, and it now finds the window by class + title;
- the cursor left on the maximize button;
- the Win11 border line in screenshots.

## Keeping the skill honest

- After changing an asset: copy it into the POC and check with `cmp`, then rerun both the Windows and Linux runs before editing the skill's claims.
- Keep "not verified" labels in the skill until a run like the ones above exists for that platform or feature. Open items are in `.agents/TODO.md`.
