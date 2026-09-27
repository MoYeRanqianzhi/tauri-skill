"""Behaviour matrix for the titlebar POC. Moves the real mouse; do not touch input while it runs."""
import probe as p, time, ctypes
h = p.find('titlebar-poc'); p.foreground(h)
if p.u32.IsZoomed(h): p.u32.ShowWindow(h, 9); time.sleep(0.8)
class CI(ctypes.Structure): _fields_ = [('cb', ctypes.c_uint), ('flags', ctypes.c_uint), ('h', ctypes.c_void_p), ('x', ctypes.c_long), ('y', ctypes.c_long)]
def cursor():
    ci = CI(); ci.cb = ctypes.sizeof(CI); p.u32.GetCursorInfo(ctypes.byref(ci)); return ci.h
SIZENS = p.u32.LoadCursorW(None, 32645)
res = {}
def geo():
    R = p.rects(h); cy = p.center(R['titlebar'])[1]
    return R, p.rect(h, True), cy, (R['menu-file'][2] + R['search'][0]) // 2 + 80
R, (l, t, r, b), cy, gx = geo()
p.move(gx, t + 12); time.sleep(0.2); p.move(gx + 1, t + 3); time.sleep(0.4)
res['top edge cursor is SIZENS'] = cursor() == SIZENS
w0 = p.rect(h); p.drag(gx, t + 3, gx, t - 60); w1 = p.rect(h)
res['top edge resize'] = (w1[1] < w0[1] and w1[3] == w0[3], w0, w1)
R, (l, t, r, b), cy, gx = geo()
w0 = p.rect(h); p.drag(gx, cy, gx - 80, cy + 60); w1 = p.rect(h)
res['drag moves window'] = (w1[0] - w0[0], w1[1] - w0[1])
R, (l, t, r, b), cy, gx = geo()
n0 = sum('menu-file clicked' in x for x in p.log_lines()); p.click(*p.center(R['menu-file'])); time.sleep(0.4)
res['File button click reaches page'] = sum('menu-file clicked' in x for x in p.log_lines()) == n0 + 1
p.click(gx, cy, double=True); time.sleep(1.2)
res['double-click maximizes'] = bool(p.u32.IsZoomed(h))
time.sleep(0.5); R, (l, t, r, b), cy, gx = geo()
mon = p.rect(h, True)
res['maximized client'] = mon
res['maximized hits (close,max,min,page-bar)'] = [p.hit(h, x, max(t, 0) + 4)['nchittest'] for x in (r - 30, r - 100, r - 170)] + [p.hit(h, gx, max(t, 0) + 4)['under']]
p.move(gx, t + 400); time.sleep(0.4); p.shot('shots/max_top.png', (r - 700, t, r, t + 90))
p.move(r - 100, t + 15); time.sleep(0.3); p.move(r - 99, t + 15); time.sleep(1.8); p.shot('shots/max_snap.png', (r - 900, t, r, t + 450))
p.key(0x1B); p.key(0x1B, True); p.move(gx, t + 400); time.sleep(0.3)
p.click(gx, cy, double=True); time.sleep(1.2)
res['double-click restores'] = not p.u32.IsZoomed(h)
R, (l, t, r, b), cy, gx = geo()
p.click(gx, cy, button='right'); time.sleep(0.8); p.shot('shots/sysmenu.png', (gx - 50, cy - 20, gx + 450, cy + 450))
menu = p.u32.FindWindowW('#32768', None); res['right-click opens system menu (#32768)'] = bool(menu and p.u32.IsWindowVisible(menu))
p.key(0x1B); p.key(0x1B, True); time.sleep(0.3)
for k, v in res.items(): print(f'{k}: {v}')
