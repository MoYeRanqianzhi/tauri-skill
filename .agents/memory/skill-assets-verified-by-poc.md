---
name: skill-assets-verified-by-poc
description: Recall before changing assets/windows_titlebar.rs, assets/titlebar.js or the frontend contract of the tauri-custom-titlebar skill.
metadata:
  type: project
  scope: .claude/skills/tauri-custom-titlebar and poc/titlebar-poc (Windows 11, Tauri 2.12)
  status: active
  last_verified: 2026-09-27
---

The skill's shipped code is only trustworthy while `poc/titlebar-poc` builds **byte-identical copies** of it and passes the harness. The copies are:
- `src-tauri/src/titlebar.rs` = `assets/windows_titlebar.rs`;
- `src/titlebar.js` = `assets/titlebar.js`.

The frontend example in `references/frontend.md` mirrors the POC's `index.html`.

**Why:** several plausible additions turned out to be wrong or useless only when measured. Examples: `TrackMouseEvent`, a custom `WM_SETCURSOR`, and a `dark` glyph flag. Maximized-state compensation also broke DWM hit-testing. The previous skill failed because nothing it shipped had been run.

**How to apply:**
1. Edit the asset, then copy it into the POC and check with `cmp`.
2. `npx vite build` in `poc/titlebar-poc`, then `cargo build` in `src-tauri`. Kill `titlebar-poc.exe` first, or the link step fails with "failed to remove file".
3. Launch through `poc/probe.py` (`p.launch()`), run `scripts/verify_windows_titlebar.py titlebar-poc` (must print `ALL PASS`), and run the relevant `poc/*.py` checks (see [../docs/poc-harness.md](../docs/poc-harness.md)).
4. Only then update the skill text, with the measured numbers.

Remove temporary `POC_*` env-var knobs from the POC copy before comparing.

**Evidence:**
- 2026-09-27: `cmp` identical, verify script `ALL PASS`, negative control (no `install`) reported 7 failures.
- Ablations for `WM_ERASEBKGND` (required) and `WM_ACTIVATE` (not needed) are in git history (commit "POC: finalize...").

**Recheck when:** Tauri, wry, tao or WebView2 is upgraded; the POC layout changes; or the harness is moved.

Related: [[skill-authoring-conventions]], [[win32-ui-automation-safety]].
