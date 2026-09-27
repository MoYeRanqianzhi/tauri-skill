"""Maximize/restore via real clicks on the DWM button and via double-click; detect unresized (black) webview."""
import probe as p, time, sys
px = lambda x, y: p.ImageGrab.grab(bbox=(x, y, x + 1, y + 1), all_screens=True).getpixel((0, 0))
h = p.launch(); p.foreground(h); time.sleep(0.5)
bad = 0
for i in range(int(sys.argv[1])):
    l, t, r, b = p.rect(h, True)
    if i % 2: p.click(r - 100, t + 20)            # DWM maximize button
    else: p.click((l + r) // 2 + 150, t + 20, double=True)  # empty title bar area
    time.sleep(1.2); p.move(r - 100 if p.u32.IsZoomed(h) else l + 300, 700); time.sleep(0.2)
    z = p.u32.IsZoomed(h); l, t, r, b = p.rect(h, True)
    s = [px(x, y) for x, y in ((max(l, 0) + 20, b - 20), (min(r, 2560) - 20, b - 20))]
    black = any(c == (0, 0, 0) for c in s); bad += black
    print(i, 'max' if z else 'restored', 'BLACK' if black else 'ok', s)
    # click restore/maximize back via the DWM button
    l, t, r, b = p.rect(h, True); p.click(r - 100, max(t, 0) + 15); time.sleep(1.2)
    l, t, r, b = p.rect(h, True)
    s = [px(x, y) for x, y in ((max(l, 0) + 20, b - 20), (min(r, 2560) - 20, b - 20))]
    black = any(c == (0, 0, 0) for c in s); bad += black
    print(i, 'max' if p.u32.IsZoomed(h) else 'restored', 'BLACK' if black else 'ok', s)
print('black frames:', bad)
