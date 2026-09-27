"""Screenshot the title bar per theme: active, inactive (focus moved to our own Tk window), maximized."""
import probe as p, time, tkinter as tk, ctypes, os
from PIL import Image
h = p.launch(); p.foreground(h); time.sleep(0.5)
tkr = tk.Tk(); tkr.geometry('200x100+60+1300'); tkr.update()
tk_h = int(tkr.wm_frame(), 16)
rows = []
for name in ['light', 'dark', 'indigo', 'emerald', 'sand']:
    p.foreground(h); p.u32.ShowWindow(h, 9); time.sleep(0.8)
    p.click(*p.center(p.rects(h)[f'theme-{name}'])); time.sleep(0.6)
    l, t, r, b = p.rect(h, True); p.move(l + 600, t + 500); time.sleep(0.5)
    active = p.ImageGrab.grab(bbox=(l, t, r, t + 60), all_screens=True)
    p.foreground(tk_h); tkr.update(); time.sleep(0.8)
    inactive = p.ImageGrab.grab(bbox=(l, t, r, t + 60), all_screens=True)
    p.foreground(h); p.u32.ShowWindow(h, 3); time.sleep(1.5); p.move(1200, 900); time.sleep(0.4)
    maxed = p.ImageGrab.grab(bbox=(0, 0, 2560, 50), all_screens=True).resize((1280, 25))
    rows += [active, inactive, maxed]
tkr.destroy()
W = max(i.width for i in rows); out = Image.new('RGB', (W, sum(i.height + 6 for i in rows)), (255, 0, 255)); y = 0
for i in rows: out.paste(i, (0, y)); y += i.height + 6
out.save('shots/themes.png'); p.u32.ShowWindow(h, 9)
