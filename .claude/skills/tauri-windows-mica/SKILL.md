---
name: tauri-windows-mica
description: Gives a Tauri 2 window the Windows 11 Mica (or Mica Alt) backdrop across the whole window, title bar included, with a page that stays readable in light and dark, no white flash at startup, and an opaque fallback on Windows 10. Use when asked for Mica, Mica Alt, a Windows 11 material or backdrop, or a translucent window background on Windows, or when a Mica attempt shows a white page, a see-through window, a startup flash, or a tint that does not match the page theme. Verified on Windows 11 25H2; Windows 10 and 21H2 behavior is documented but not verified.
---

# Windows 11 Mica backdrop for Tauri 2

Tauri already ships Mica (`windowEffects`, implemented by window-vibrancy). What breaks is everything around it:
- the window must be transparent;
- the page must not paint over the material;
- the tint must follow the same theme as the page;
- the window must not show before WebView2 attaches;
- Windows 10 needs a fallback, because Tauri drops the error.

This recipe covers all five. Each step was run and measured on Windows 11; the few exceptions are listed under Verified scope.

## Recipe

### 1. Window config

Add these keys to the window object in `src-tauri/tauri.conf.json`:

```json
"transparent": true,
"visible": false,
"windowEffects": { "effects": ["mica"] }
```

- Mica Alt (a stronger tint, meant for tabbed title bars): use `"effects": ["tabbed"]`.
- Fixed theme: add `"theme": "Dark"` or `"theme": "Light"`. Never use `micaDark` / `micaLight`.
- Keep `decorations` on (the default). The native title bar then shows Mica too. For a custom title bar see [references/styling.md](references/styling.md) § Custom title bar.
- Cross-platform app: put these keys in `src-tauri/tauri.windows.conf.json` instead, as `{ "app": { "windows": [ … ] } }`. Repeat the **whole** window object there: platform files replace the `app.windows` array, so a file with only these keys loses the title and size.

### 2. Capability

Add `"core:window:allow-show"` to the permissions of the capability that covers the window (`src-tauri/capabilities/default.json` in the templates). Runtime switching needs more; see [references/internals.md](references/internals.md) § Runtime changes.

### 3. Page

1. Copy `assets/mica.css` and `assets/mica.js` next to the entry script. In a TypeScript project also copy `assets/mica.d.ts`.
2. Import `mica.css` before your own styles. Then delete every opaque background on `html`, `body` and the app root (`#app`, `#root`). The create-tauri-app stylesheets paint `:root` (`#f6f6f6` / `#2f2f2f`), which hides Mica completely.
3. Put this at the top of the entry script, before anything that can throw:

   ```js
   import { getCurrentWindow } from '@tauri-apps/api/window';
   import { detectMica } from './mica.js';

   getCurrentWindow().show(); // "visible": false: show once the page runs, not before WebView2 attaches
   detectMica(); // sets data-mica="off" (opaque fallback) where Mica is unavailable, e.g. Windows 10
   ```

4. Build the UI from the `--mica-*` tokens:
   - leave navigation and title areas bare (no background);
   - put the content area on `--mica-layer` and cards on `--mica-card`;
   - use `--mica-text*` for text.

   The layout and the token table are in [references/styling.md](references/styling.md).

### 4. Verify

1. Give the window a unique title and start the app.
2. Run `python scripts/verify_windows_mica.py "<title>"` from this skill's directory. It must print `ALL PASS`.
   - It moves no mouse and sends no keys, but it brings the window to the front for about 8 s.
   - Each FAIL line names the cause. [references/troubleshooting.md](references/troubleshooting.md) maps it to the fix.
3. Screenshot light and dark (for example via `"theme"`), each active and inactive.
4. Ask the user to do what a script must not: switch the Windows theme, and toggle Settings > Personalization > Colors > Transparency effects, while the app runs.

## Hard rules

- Set `transparent: true` **and** `windowEffects` together. Without `transparent` only the title bar gets Mica and the page is white. Without a working effect the window is see-through, and Tauri reports no error.
- Nothing opaque between the page and the window. No `backgroundColor` in the window config: it covers Mica even with `transparent`. No opaque `html` / `body` / root background. Surfaces use the translucent tokens.
- Set the theme through `"theme"` or `Window.setTheme()`, never `micaDark` / `micaLight`. Those tint only the backdrop, so the page keeps the system scheme, and Tauri resets them on the next `WM_SETTINGCHANGE` broadcast.
- Use `visible: false` + `show()`. Otherwise the window is white for 0.6–0.8 s at every start (measured), worst in dark mode. If the window never appears, the permission from step 2 is missing.
- `clearEffects()` at runtime makes the window see-through. Set `data-mica="off"` on `<html>` at the same time.
- An inactive window shows a flat `#f3f3f3` (light) or `#202020` (dark). Every window does the same when Transparency effects or battery saver are on. This is Windows' design; do not work around it.

## References

- [references/troubleshooting.md](references/troubleshooting.md): symptom → cause → fix, plus testing traps.
- [references/styling.md](references/styling.md): tokens, layout on Mica, fallback, Mica Alt, custom title bar.
- [references/internals.md](references/internals.md): how Tauri applies Mica, runtime changes and permissions, extra windows, measurements.

## Verified scope

Verified on Windows 11 25H2 (build 26200) at 150% scaling, with WebView2 153, tauri 2.12.0, wry 0.57.0, tao 0.37.1, window-vibrancy 0.8.1 and @tauri-apps/api 2.12.0. Covered:
- Mica and Mica Alt, light and dark, active and inactive;
- maximized, minimized and restored, and programmatic resizing;
- runtime `setTheme`, `setEffects` and `clearEffects`;
- a second window created from JS, and `decorations: false`;
- the combination with tauri-custom-titlebar.

Not verified:
- a real Windows 10 machine (the fallback path was run by faking the Windows 10 `platformVersion`);
- the `tauri.windows.conf.json` variant of step 1 (the array-replacement rule was verified with `tauri.linux.conf.json` in the tauri-custom-titlebar work);
- Windows 11 21H2, where window-vibrancy uses an undocumented attribute;
- live Windows theme switching and Transparency effects off (documented by Microsoft and the tao source);
- high contrast, and moving between monitors with different DPI;
- macOS and Linux.
