# Frontend contract

`assets/titlebar.js` connects the page to the Rust module. The page owns the whole title bar except the native button block in the top-right corner.

## CSS variables

`watchTitlebarInsets()` writes these on `<html>`. It re-reads them on every window `resize` event, which fires on maximize/restore, resize and DPI change. On non-Windows platforms it does nothing, so the CSS fallbacks apply.

| Variable | Meaning | 150% scale, restored / maximized |
|---|---|---|
| `--titlebar-top` | Rows hidden above the screen; pad the bar by this much | 0 / 7.33px |
| `--titlebar-height` | Visible button height = the bar's row height | 29.33px / 22px |
| `--titlebar-right` | Width of the native button block; keep content out of it | 146px / 147.33px |

Nothing the page draws inside the top-right `--titlebar-right` × (`--titlebar-top` + `--titlebar-height`) rectangle is visible. That includes backgrounds, borders, shadows, tooltips and dropdowns: the native buttons own that rectangle.

## Complete example

This markup and CSS is what the verified POC runs.

```html
<body>
  <header class="titlebar">
    <div class="brand"><svg>…</svg> Workbench</div>
    <button class="tb-btn">File</button>
    <button class="tb-btn">Edit</button>
    <input class="search" placeholder="Search or run a command" />
  </header>
  <main>…</main>
  <script type="module" src="/src/main.js"></script>
</body>
```

```css
:root { --titlebar-bg: #f3f3f3; --titlebar-fg: #1b1b1f; --titlebar-muted: #8a8a92; }
html, body { margin: 0; height: 100%; }
body { display: flex; flex-direction: column; }

.titlebar {
  --bar: var(--titlebar-height, 32px);        /* min-height variant: max(var(--titlebar-height, 32px), 40px) */
  box-sizing: content-box;                    /* border-bottom stays below the button hole */
  flex: none;
  height: var(--bar);
  padding: var(--titlebar-top, 0px) var(--titlebar-right, 0px) 0 10px;
  display: flex; align-items: center; gap: 2px;
  background: var(--titlebar-bg);
  color: var(--titlebar-fg);
  border-bottom: 1px solid rgb(0 0 0 / .08);
  app-region: drag;                           /* drag, double-click maximize, right-click system menu, Aero Snap */
  user-select: none;
}
.titlebar :is(button, input, select, textarea, a, [role="button"], [contenteditable]) { app-region: no-drag; }
body.inactive .titlebar { color: var(--titlebar-muted); }

/* Controls scale with the bar: it is ~22px tall when maximized at 150%. */
.tb-btn { height: calc(var(--bar) - 8px); padding: 0 9px; border: 0; border-radius: 5px; background: transparent; color: inherit; font: inherit; }
.tb-btn:hover { background: rgb(0 0 0 / .06); }
.search { margin: 0 auto; width: min(360px, 40%); height: min(28px, calc(var(--bar) - 8px)); }

main { flex: 1; overflow: auto; }
```

```js
// src/main.js
import { watchTitlebarInsets, setTitlebarColor } from './titlebar.js';

watchTitlebarInsets();
setTitlebarColor(getComputedStyle(document.documentElement).getPropertyValue('--titlebar-bg').trim());
addEventListener('focus', () => document.body.classList.remove('inactive'));
addEventListener('blur', () => document.body.classList.add('inactive'));
```

Key points:

- **The drag region is `app-region: drag` on the bar**, with `no-drag` on every interactive child. wry turns on WebView2's non-client region support, so drag, double-click maximize and restore, the right-click system menu and Aero Snap all come from Windows. All of these were verified.
  - `data-tauri-drag-region` drags and double-clicks through JavaScript and has no system menu, so prefer `app-region`.
  - Adding `data-tauri-drag-region` to the same bar (for macOS/Linux) is harmless on Windows (verified): WebView2's drag overlay takes the mouse first, so double-click still toggles only once. On other platforms it needs `core:window:allow-start-dragging` and `core:window:allow-internal-toggle-maximize`.
- **`setTitlebarColor` takes `#rrggbb` only.** Other formats (`rgb()`, names, 3-digit hex) make the command return an error.
- **Do not call `getCurrentWindow().minimize()`, `toggleMaximize()` or `close()`** for the native buttons, and add no `core:window:*` permissions for them.

## Sizing title bar content

The bar follows the native button height, so it is shorter when maximized. That matches stock Windows windows. Two layouts were verified:

1. **Default: bar = `--titlebar-height`.** Button hover fills the full bar height. Controls must scale, as in the example: `calc(var(--bar) - 8px)`, and `min(28px, …)` for inputs. Otherwise a fixed-height search box overflows the 22px maximized bar and looks broken.
2. **Min-height variant: `--bar: max(var(--titlebar-height, 32px), 40px)`.** Use it for large content such as a tab strip or a big search field. The bar stays at least 40px tall. The DWM buttons keep their own height and stay aligned to the top; their hover covers only the upper part of the bar. Tell the user about this visual tradeoff.

## Colors and themes

- **Call `setTitlebarColor(bg)` at start-up and whenever the title bar background changes.**
  - DWM then chooses glyph and hover colors by contrast: white glyphs and a light hover overlay on dark or saturated colors, dark glyphs on light colors, red close hover. This was verified on `#f3f3f3`, `#202024`, `#3140b8`, `#0f5e56` and `#efe6d8`, both active and inactive.
  - Pass `null` to return to the system caption color.
- **Following the OS light/dark setting:** choose the palette with `matchMedia('(prefers-color-scheme: dark)')` and call `setTitlebarColor` again in its `change` listener. Switching the OS theme live was not tested.
- **`getCurrentWindow().setTheme()`** sets the window's light/dark mode and also WebView2's preferred color scheme. Use it only when that is exactly what you want for the whole page, never just to recolor the buttons.
- **The inactive state is native:** DWM dims the glyphs. Dim your own title text through `focus`/`blur` as in the example (verified).

## Other platforms in the same markup

- **Windows 10:** the helpers run, but the caption color has no effect. Not tested.
- **macOS and Linux:** `watchTitlebarInsets` and `setTitlebarColor` return immediately, so the CSS fallbacks (`32px`, `0px`) apply. See `macos-linux.md` for the traffic-light inset on macOS and for Linux options. Keep `app-region: drag` and add `data-tauri-drag-region` to the same bar, plus the two permissions above, so that platforms without `app-region` support can still drag.
