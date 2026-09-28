# Styling a page on Mica

## The rule

Every pixel the page leaves transparent shows Mica, and every opaque pixel hides it. So the page root stays transparent, and each surface on top of Mica uses a translucent fill. Translucent fills composite over the material, so they also follow it into the inactive state (measured below).

## Tokens (`assets/mica.css`)

The values come from WinUI 3: microsoft-ui-xaml `controls/dev/CommonStyles/Common_themeresources_any.xaml`, converted from `#AARRGGBB`. The dark column applies under `prefers-color-scheme: dark`. In a Tauri window that query follows the window theme, which is also what tints Mica.

| Token | WinUI resource | Light | Dark | Use |
|---|---|---|---|---|
| `--mica-text` | TextFillColorPrimary | `rgb(0 0 0 / .894)` | `#ffffff` | body text |
| `--mica-text-secondary` | TextFillColorSecondary | `rgb(0 0 0 / .62)` | `rgb(255 255 255 / .773)` | hints, labels |
| `--mica-text-tertiary` | TextFillColorTertiary | `rgb(0 0 0 / .447)` | `rgb(255 255 255 / .529)` | disabled, input underline |
| `--mica-layer` | LayerFillColorDefault | `rgb(255 255 255 / .5)` | `rgb(58 58 58 / .298)` | the content area |
| `--mica-card` | CardBackgroundFillColorDefault | `rgb(255 255 255 / .702)` | `rgb(255 255 255 / .051)` | cards |
| `--mica-stroke` | CardStrokeColorDefault | `rgb(0 0 0 / .059)` | `rgb(0 0 0 / .098)` | card and layer borders |
| `--mica-control` | ControlFillColorDefault | `rgb(255 255 255 / .702)` | `rgb(255 255 255 / .059)` | buttons, inputs |
| `--mica-control-hover` | ControlFillColorSecondary | `rgb(249 249 249 / .502)` | `rgb(255 255 255 / .082)` | control hover |
| `--mica-control-stroke` | ControlStrokeColorDefault | `rgb(0 0 0 / .059)` | `rgb(255 255 255 / .071)` | control borders |
| `--mica-subtle-hover` | SubtleFillColorSecondary | `rgb(0 0 0 / .035)` | `rgb(255 255 255 / .059)` | nav and list item hover, selection |
| `--mica-subtle-pressed` | SubtleFillColorTertiary | `rgb(0 0 0 / .024)` | `rgb(255 255 255 / .039)` | pressed |
| `--mica-fallback` | SolidBackgroundFillColorBase | `#f3f3f3` | `#202020` | only for `data-mica="off"` |

mica.css contains no accent color, because that is the brand's. The demo uses the Windows default blue: `#005fb8` (light) and `#60cdff` (dark), with `#fff` / `#000` text on it.

## A layout that reads as a Windows 11 app

The verified demo (`poc/mica-poc`) follows WinUI's NavigationView pattern:
- Title bar and navigation pane: bare Mica, with no background. Nav items use `--mica-subtle-hover` for hover and selection, and the selected item has a 3 px accent pill.
- Content area: one `--mica-layer` surface with a hairline border and a rounded top-left corner.
- Cards on the layer: `--mica-card` with a `--mica-stroke` border, 4 px apart.
- Controls: `--mica-control` fill, `--mica-control-stroke` border, `--mica-control-hover` on hover.

```css
body { margin: 0; height: 100vh; display: flex; }
.nav { width: 240px; padding: 8px 4px; }            /* no background: bare Mica */
.nav-item:hover, .nav-item[aria-current] { background: var(--mica-subtle-hover); }
.content {
  flex: 1; overflow: auto; padding: 28px 40px;
  background: var(--mica-layer);
  border: 1px solid var(--mica-stroke); border-width: 1px 0 0 1px; border-top-left-radius: 8px;
}
.card { background: var(--mica-card); border: 1px solid var(--mica-stroke); border-radius: 6px; margin-bottom: 4px; }
```

Measured compositing, light theme, active window: bare Mica `rgb(249,241,236)`, and `--mica-layer` over it `rgb(252,248,246)`. Inactive, the same pixels are `#f3f3f3` and `#f9f9f9`. The layer tracks the material in both states.

## Fallback (`data-mica="off"`)

`detectMica()` sets `data-mica="off"` unless `navigator.userAgentData` reports Windows with `platformVersion` ≥ 13, which is Windows 11 per Microsoft's UA-CH documentation. For `"off"`, mica.css paints `--mica-fallback` on `:root`.
- Measured with a faked Windows 10 value on a window with no effect: nothing was see-through, and the page showed `#f3f3f3` (light) and `#202020` (dark).
- Until `detectMica()` resolves, the page stays transparent, so Windows 11 never shows the fallback color. In every run it resolved before the first paint was recorded (0.4–44 ms after the call).
- WebKit webviews (macOS, Linux) have no `navigator.userAgentData`, so they get `"off"` too.

## Mica Alt

Set `"effects": ["tabbed"]` to get DWM's stronger variant. Microsoft suggests it for apps with a tabbed title bar.
- The same tokens work on it: the page matched the caption in every state.
- Its inactive fallback here was `#e8e8e8` (light) and `#202020` (dark). WinUI's `SolidBackgroundFillColorBaseAlt` (`#dadada` / `#0a0a0a`) is not what DWM paints, so mica.css keeps the Mica fallback colors.

## Custom title bar

With the tauri-custom-titlebar skill, decorations stay on, the caption row is removed and the native caption buttons stay:
- Keep the page's title bar background transparent. Mica then runs under the bar and under the caption buttons. The buttons' hover and pressed states draw on Mica: that skill's verify script passed all 20 checks on a Mica window.
- Do not call `setTitlebarColor(color)`. It sets `DWMWA_CAPTION_COLOR`, which paints a solid band over Mica across the whole bar area, and the page's bar text does not adapt to it. `setTitlebarColor(null)` restores Mica.
- Controls in the bar, such as a search box, use `--mica-control`.

`decorations: false` also shows Mica across the window (verified). You lose the native caption buttons, Snap Layouts and the system menu, though, so prefer tauri-custom-titlebar.
