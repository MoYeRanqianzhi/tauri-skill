---
name: skill-assets-verified-by-poc
description: Recall before changing any asset, script or frontend contract of tauri-custom-titlebar or tauri-windows-mica (titlebar.rs/js, enableDragRegion, mica.css/js, the verify scripts).
metadata:
  type: project
  scope: .claude/skills/tauri-custom-titlebar with poc/titlebar-poc (Windows 11, Linux X11); .claude/skills/tauri-windows-mica with poc/mica-poc (Windows 11); Tauri 2.12
  status: active
  last_verified: 2026-09-28
---

A skill's shipped code is only trustworthy while its POC builds **byte-identical copies** of it and passes that POC's harness.

The copies are:
- tauri-custom-titlebar:
  - `assets/windows_titlebar.rs` = `poc/titlebar-poc/src-tauri/src/titlebar.rs`;
  - `assets/titlebar.js` = `poc/titlebar-poc/src/titlebar.js`, and also `poc/mica-poc/src/titlebar.js`;
  - `poc/mica-poc/src-tauri/src/titlebar.rs` is a third copy of `windows_titlebar.rs` (used for the Mica + custom title bar variant);
  - the example in `references/frontend.md` mirrors `poc/titlebar-poc/index.html`.
- tauri-windows-mica:
  - `assets/mica.css` = `poc/mica-poc/src/mica.css`;
  - `assets/mica.js` = `poc/mica-poc/src/mica.js`.

The `.d.ts` files have no POC copy, because both POCs are plain JS. They are type-checked with `tsc --strict` instead, without `allowJs` and with a `@ts-expect-error` probe.

The verify scripts are validated by running them against positive and negative POC variants. For tauri-windows-mica, `poc/mica_verify_matrix.py` runs 7 variants that must pass and 6 deliberately broken ones that must fail. A script change that has not been through its matrix is not verified.

**Why:** several plausible additions turned out wrong or useless only when measured:
- titlebar: `TrackMouseEvent`, a custom `WM_SETCURSOR`, the `dark` glyph flag, and maximized-state compensation, which broke DWM hit-testing;
- Mica: the startup white flash, which appears even with `transparent`, and `micaDark`, which flips back on `WM_SETTINGCHANGE`.

The previous skill failed because nothing it shipped had been run.

**How to apply:**
1. Edit the asset in the POC, run the checks, then copy it to the skill and confirm with `cmp`.
2. Rebuild:
   - run `npx vite build` in the POC directory, then `cargo build` in `src-tauri`;
   - kill the exe first (`titlebar-poc.exe` / `mica-poc.exe`), or the link step fails with "failed to remove file".
3. Run the harness. Commands and last results are in [../docs/poc-harness.md](../docs/poc-harness.md) and [../docs/mica-poc-harness.md](../docs/mica-poc-harness.md).
   - Titlebar: its verify script must print `ALL PASS`. Rerun `poc/linux_matrix.py` on an X11 host when `titlebar.js` or the Linux path changes.
   - Mica: `poc/mica_verify_matrix.py` must summarize every variant as `OK`.
4. Only then update the skill text, using the measured numbers.

Remove temporary `POC_*` env-var knobs from any shipped copy before comparing.

**Evidence:**
- 2026-09-27, titlebar:
  - `cmp` identical, verify `ALL PASS`, and the negative control (no `install`) reported 7 failures;
  - Linux matrix passed with `enableDragRegion`;
  - `titlebar.d.ts` passed `tsc --noEmit` in a `vanilla-ts` create-tauri-app project.
- 2026-09-28, Mica:
  - `cmp` identical for `mica.css` / `mica.js`;
  - the verify matrix was 13/13 as expected, with match tolerance ≤ 3. The shipped script is that version; a later ≤ 2 edit was reverted without being run;
  - `mica.d.ts` passed `tsc --strict` 6.0.3.
- Titlebar ablation results are summarized in the "POC: finalize..." commit and in that skill's `references/windows.md` §2.

**Recheck when:** Tauri, wry, tao, window-vibrancy or WebView2 is upgraded; a POC layout changes; or a harness is moved.

Related: [[skill-authoring-conventions]], [[win32-ui-automation-safety]].
