"""Cursor shape after moving onto the top resize band from different starting widgets."""
import probe as p, time, ctypes
class CI(ctypes.Structure): _fields_ = [('cb', ctypes.c_uint), ('flags', ctypes.c_uint), ('h', ctypes.c_void_p), ('x', ctypes.c_long), ('y', ctypes.c_long)]
names = {32512: 'ARROW', 32513: 'IBEAM', 32645: 'SIZENS', 32642: 'SIZENWSE', 32643: 'SIZENESW'}
m = {p.u32.LoadCursorW(None, k): v for k, v in names.items()}
def cur():
    ci = CI(); ci.cb = ctypes.sizeof(CI); p.u32.GetCursorInfo(ctypes.byref(ci)); return m.get(ci.h, hex(ci.h or 0))
h = p.find('titlebar-poc'); p.foreground(h)
if p.u32.IsZoomed(h): p.u32.ShowWindow(h, 9); time.sleep(1)
R = p.rects(h); l, t, r, b = p.rect(h, True)
gx = (R['menu-file'][2] + R['search'][0]) // 2 + 80
for tag, (x0, y0) in {'drag area': (gx, t + 25), 'File button': p.center(R['menu-file']), 'page body': (gx, t + 200)}.items():
    for steps in (1, 5):
        p.move(x0, y0); time.sleep(0.4); before = cur()
        for i in range(1, steps + 1): p.move(x0, y0 + (t + 3 - y0) * i // steps); time.sleep(0.03)
        time.sleep(0.5); print(f'{tag:12} steps={steps} before={before:7} on-band={cur()}  under={p.hit(h, x0, t + 3)["under"]}')
