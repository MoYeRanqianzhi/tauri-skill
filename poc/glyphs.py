"""Indigo theme: glyph brightness before/after WM_SETTINGCHANGE, and the page's prefers-color-scheme."""
import probe as p, time, ctypes
h = p.find('titlebar-poc'); p.foreground(h)
if p.u32.IsZoomed(h): p.u32.ShowWindow(h, 9); time.sleep(1)
p.click(*p.center(p.rects(h)['theme-indigo'])); time.sleep(0.8)
l, t, r, b = p.rect(h, True); p.move(l + 400, t + 400); time.sleep(0.4)
def glyph_max():  # brightest pixel inside the minimize button = glyph color on a dark bar
    im = p.ImageGrab.grab(bbox=(r - 200, t + 5, r - 140, t + 40), all_screens=True).convert('L')
    return max(im.get_flattened_data())
print('after theme: glyph max luminance', glyph_max())
buf = ctypes.create_unicode_buffer('ImmersiveColorSet')
p.u32.SendMessageTimeoutW.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_size_t, ctypes.c_void_p, ctypes.c_uint, ctypes.c_uint, ctypes.c_void_p]
p.u32.SendMessageTimeoutW(h, 0x1A, 0, ctypes.addressof(buf), 0, 2000, None); time.sleep(0.5)
import tkinter as tk  # repaint the caption: deactivate (to our own Tk window) and re-activate
tkr = tk.Tk(); tkr.geometry('200x100+60+1300'); tkr.update(); p.foreground(int(tkr.wm_frame(), 16)); tkr.update(); time.sleep(0.6)
p.foreground(h); tkr.destroy(); p.move(l + 400, t + 400); time.sleep(0.8)
print('after WM_SETTINGCHANGE: glyph max luminance', glyph_max())
print([l for l in p.log_lines() if 'theme indigo' in l or 'changed' in l][-3:])
p.shot('shots/glyphs.png', (r - 300, t, r, t + 50))
