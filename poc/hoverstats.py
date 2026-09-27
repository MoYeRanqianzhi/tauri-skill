"""Enter each caption button from inside the webview and leave back into it, N times; count hover shown / stuck."""
import probe as p, time, sys
from PIL import ImageGrab
N = int(sys.argv[1]) if len(sys.argv) > 1 else 5
h = p.find("titlebar-poc"); p.foreground(h); time.sleep(1)
if p.u32.IsZoomed(h): p.u32.ShowWindow(h, 9); time.sleep(0.8)
l, t, r, b = p.rect(h, True)
def px(x, y): return ImageGrab.grab(bbox=(x, y, x + 1, y + 1), all_screens=True).getpixel((0, 0))
def slide(x0, y0, x1, y1, n=10):
    for i in range(1, n + 1): p.move(x0 + (x1 - x0) * i // n, y0 + (y1 - y0) * i // n); time.sleep(0.02)
stats = {}
for name, x in [('close', r - 30), ('max', r - 100), ('min', r - 170)]:
    shown = stuck = 0
    for _ in range(N):
        slide(x, t + 20, x, t + 140); time.sleep(0.4); base = px(x, t + 8)
        slide(x, t + 140, x, t + 20); time.sleep(0.6); hot = px(x, t + 8)
        slide(x, t + 20, x, t + 140); time.sleep(0.6); after = px(x, t + 8)
        shown += hot != base; stuck += after != base; print(name, "hot" if hot != base else "MISS", end=" ", flush=True)
        p.u32.keybd_event(0x1B, 0, 0, 0); p.u32.keybd_event(0x1B, 0, 2, 0)
    stats[name] = f'hover shown {shown}/{N}, stuck {stuck}/{N}'
print(stats)
