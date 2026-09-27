"""Minimize click, Aero Snap by dragging to the left edge, Alt+Space system menu, close click."""
import probe as p, time, subprocess
h = p.launch(); p.foreground(h); time.sleep(0.5)
R = p.rects(h); l, t, r, b = p.rect(h, True)
gx = (R['menu-file'][2] + R['search'][0]) // 2 + 80; cy = p.center(R['titlebar'])[1]
p.click(r - 170, t + 20); time.sleep(1.0)
print('minimize button -> iconic:', bool(p.u32.IsIconic(h)))
p.u32.ShowWindow(h, 9); time.sleep(1.2); p.foreground(h)
R = p.rects(h); l, t, r, b = p.rect(h, True); cy = p.center(R['titlebar'])[1]; gx = (R['menu-file'][2] + R['search'][0]) // 2 + 80
p.drag(gx, cy, 0, 700); time.sleep(1.2)
p.key(0x1B); p.key(0x1B, True); time.sleep(0.5)  # dismiss Snap Assist if it shows other windows
print('drag to left edge -> window', p.rect(h), '(left half of 2560x1528 work area expected)')
p.foreground(h); p.key(0x12); p.key(0x20); p.key(0x20, True); p.key(0x12, True); time.sleep(0.8)
menu = p.u32.FindWindowW('#32768', None); print('Alt+Space -> system menu visible:', bool(menu and p.u32.IsWindowVisible(menu)))
p.key(0x1B); p.key(0x1B, True); time.sleep(0.3)
l, t, r, b = p.rect(h, True); p.click(r - 30, max(t, 0) + 15); time.sleep(1.5)
alive = 'titlebar-poc.exe' in subprocess.run(['tasklist'], capture_output=True, text=True).stdout
print('close button -> process exited:', not alive)
