"""Maximize right after activation; sample content pixels to detect a black (unpainted) webview."""
import probe as p, time, sys
px = lambda x, y: p.ImageGrab.grab(bbox=(x, y, x + 1, y + 1), all_screens=True).getpixel((0, 0))
import os, json; h = p.launch(json.loads(os.environ.get("ENVJSON", "{}")))
for i in range(int(sys.argv[1]) if len(sys.argv) > 1 else 4):
    p.u32.ShowWindow(h, 9); time.sleep(1.2)
    p.foreground(h); p.u32.ShowWindow(h, 3); time.sleep(1.5)
    s = [px(x, y) for x, y in ((500, 100), (1300, 700), (2400, 1400))]
    black = any(c == (0, 0, 0) for c in s)
    print(i, 'BLACK' if black else 'ok', s)
    if black: p.shot(f'shots/black_{i}.png', (0, 0, 2560, 1528))
