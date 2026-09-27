"""Sample the cursor every 20 ms after jumping from the page onto the resize band."""
import probe as p, time, ctypes
class CI(ctypes.Structure): _fields_ = [('cb', ctypes.c_uint), ('flags', ctypes.c_uint), ('h', ctypes.c_void_p), ('x', ctypes.c_long), ('y', ctypes.c_long)]
names = {32512: 'A', 32513: 'I', 32645: 'NS'}
m = {p.u32.LoadCursorW(None, k): v for k, v in names.items()}
def cur():
    ci = CI(); ci.cb = ctypes.sizeof(CI); p.u32.GetCursorInfo(ctypes.byref(ci)); return m.get(ci.h, '?')
h = p.find('titlebar-poc'); p.foreground(h)
l, t, r, b = p.rect(h, True)
for start in ((l + 700, t + 200), (l + 700, t + 25)):
    p.move(*start); time.sleep(0.6); p.move(l + 700, t + 3); t0 = time.time(); seq = []
    while time.time() - t0 < 1.0: seq.append(cur()); time.sleep(0.02)
    p.move(l + 702, t + 3); time.sleep(0.3)
    print(start[1] - t, ' '.join(seq), '| after 2nd move:', cur())
