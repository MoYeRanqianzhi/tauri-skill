"""Cursor shape + hit owner along the top edge/corners; drag top-right corner; screenshot the button strip."""
import probe as p, time, ctypes
class CI(ctypes.Structure): _fields_ = [('cb', ctypes.c_uint), ('flags', ctypes.c_uint), ('h', ctypes.c_void_p), ('x', ctypes.c_long), ('y', ctypes.c_long)]
names = {32512: 'ARROW', 32513: 'IBEAM', 32645: 'SIZENS', 32644: 'SIZEWE', 32642: 'SIZENWSE', 32643: 'SIZENESW', 32649: 'HAND'}
m = {p.u32.LoadCursorW(None, k): v for k, v in names.items()}
def cur():
    ci = CI(); ci.cb = ctypes.sizeof(CI); p.u32.GetCursorInfo(ctypes.byref(ci)); return m.get(ci.h, hex(ci.h or 0))
h = p.launch(); p.foreground(h); time.sleep(0.5)
l, t, r, b = p.rect(h, True)
p.move(l + 400, t + 300); time.sleep(0.5); p.shot('shots/edges_buttons.png', (r - 300, t, r, t + 60))
for dx, dy, tag in [(700, 0, 'top'), (700, 8, 'top+8'), (700, 9, 'top+9'), (2, 3, 'top-left'), (-2, 3, 'top-right'), (-30, 3, 'above close'), (-30, 12, 'close'), (-100, 12, 'max'), (700, 20, 'page')]:
    x = (l if dx > 0 else r) + dx; y = t + dy
    p.move(x, y + 3); time.sleep(0.15); p.move(x, y); time.sleep(0.35)
    print(f'{tag:12} under={p.hit(h, x, y)["under"]:28} cursor={cur()}')
p.move(l + 400, t + 300); time.sleep(0.4)
w0 = p.rect(h); p.drag(r - 2, t + 2, r + 60, t - 60); w1 = p.rect(h)
print('top-right corner drag', w0, '->', w1)
