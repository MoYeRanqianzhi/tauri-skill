"""Button strip visuals across restore / maximize / resize / activation for a given env knob set."""
import probe as p, time, sys, json, tkinter as tk
from PIL import Image
env = json.loads(sys.argv[1]); tag = sys.argv[2]
h = p.launch(env); p.foreground(h); time.sleep(0.5)
shots = []
def grab():
    l, t, r, b = p.rect(h, True); p.move(l + 300, t + 400); time.sleep(0.6)
    shots.append(p.ImageGrab.grab(bbox=(r - 330, max(t, 0), r, max(t, 0) + 50), all_screens=True))
grab()
l, t, r, b = p.rect(h, True); p.drag(r + 5, t + 300, r - 200, t + 300); grab()           # resize from right edge
p.click(r - 200 - 100, t + 20); time.sleep(1.5); grab()                                # maximize via DWM button
p.click(2560 - 100, 12); time.sleep(1.5); grab()                                       # restore via DWM button
tkr = tk.Tk(); tkr.geometry('200x100+60+1300'); tkr.update(); p.foreground(int(tkr.wm_frame(), 16)); tkr.update(); time.sleep(0.8); grab()
p.foreground(h); time.sleep(0.8); grab(); tkr.destroy()
out = Image.new('RGB', (330, len(shots) * 56), (255, 0, 255))
for i, s in enumerate(shots): out.paste(s, (0, i * 56))
out.save(f'shots/ablate_{tag}.png')
