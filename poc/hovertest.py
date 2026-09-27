"""Hover each caption button, move into web content, check the button background returns to caption color."""
import probe as p, time, sys
from PIL import ImageGrab
h = p.find('titlebar-poc'); p.foreground(h)
if p.u32.IsZoomed(h): p.u32.ShowWindow(h, 9); time.sleep(0.8)
l, t, r, b = p.rect(h, True)
def px(x, y): return ImageGrab.grab(bbox=(x, y, x + 1, y + 1), all_screens=True).getpixel((0, 0))
ok = True
for name, x in [('close', r - 30), ('max', r - 80), ('min', r - 150)]:
    y = t + 8
    p.move(700, t + 300); time.sleep(0.5); base = px(x, y)
    p.move(x, t + 20); time.sleep(0.2); p.move(x + 1, t + 20); time.sleep(0.6); hot = px(x, y)
    for step in range(1, 11):  # slide down into the page like a user would
        p.move(x, t + 20 + step * 10); time.sleep(0.02)
    time.sleep(0.8); after = px(x, y)
    res = after == base
    ok &= res
    print(f'{name}: base={base} hover={hot} after-leave={after} -> {"OK" if res else "STUCK"}')
    p.u32.keybd_event(0x1B, 0, 0, 0); p.u32.keybd_event(0x1B, 0, 2, 0); time.sleep(0.3)  # dismiss snap flyout
print('PASS' if ok else 'FAIL')
