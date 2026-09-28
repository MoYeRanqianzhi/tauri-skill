"""Startup and resize behaviour of poc/mica-poc (tauri-windows-mica skill). Windows 11 only.

Usage:  python mica_timing.py <run name> [VAR=value ...]

startup: grabs the app window as fast as possible for 2 s after it appears and reports, per frame,
         the share of pure-white pixels in the client area (a white flash shows up as a spike) and
         saves a strip of the first frames to poc/shots/mica-<run>-startup.png.
resize:  puts our own magenta window behind the app, grows the app with SetWindowPos in 12 quick
         steps and grabs right after each step. Magenta inside the frame = see-through while the
         webview catches up; pure black = unpainted area.

Safety: no mouse movement, no keystrokes; only the app it launched (by PID) and its own Tk window.
"""
import os
import subprocess
import sys
import time
import tkinter as tk

from PIL import Image

import mica_probe as mp

u32 = mp.u32


def share(img, pred):
    px = img.get_flattened_data() if hasattr(img, "get_flattened_data") else img.getdata()
    return sum(1 for p in px if pred(p)) / len(px)


def main():
    run = sys.argv[1]
    env = dict(os.environ, NO_AT_BRIDGE='1')
    env.update(kv.split('=', 1) for kv in sys.argv[2:])
    subprocess.run(['taskkill', '/IM', 'mica-poc.exe', '/F'], capture_output=True)
    time.sleep(0.5)
    proc = subprocess.Popen([mp.EXE], stdout=open(mp.LOG, 'w', encoding='utf-8'), stderr=subprocess.STDOUT, env=env)
    try:
        h, t0 = None, time.time()
        while time.time() - t0 < 20 and not h:
            wins = [w for w in mp.windows_of(proc.pid) if u32.IsWindowVisible(w)]
            h = wins[0] if wins else None
        if not h:
            print('no window')
            return
        u32.SetWindowPos(h, mp.TOPMOST, 0, 0, 0, 0, 0x3 | 0x10)
        frames = []
        start = time.time()
        while time.time() - start < 2.0:
            box = mp.client_origin(h)
            frames.append((time.time() - start, mp.grab(box)))
        white = [(t, share(f.resize((f.width // 4, f.height // 4)), lambda p: p == (255, 255, 255))) for t, f in frames]
        print(f'[{run}] startup: {len(frames)} frames in 2 s after the window appeared')
        print('  white share per frame:', ' '.join(f'{t:.2f}s={w:.0%}' for t, w in white[:12]), '...', f'last={white[-1][1]:.0%}')
        strip = Image.new('RGB', (6 * 240, 160))
        for i, (_, f) in enumerate(frames[:6]):
            strip.paste(f.resize((240, 160)), (i * 240, 0))
        strip.save(os.path.join(mp.SHOTS, f'mica-{run}-startup.png'))

        if not mp.wait_log('[page] status ', 20):
            print('page never reported status')
            return
        time.sleep(0.5)
        root = tk.Tk()
        root.overrideredirect(True)
        l, t, r, b = mp.rect(h)
        root.geometry(f'{r - l + 600}x{b - t + 400}+{l}+{t}')
        root.configure(bg='#ff00ff')
        root.update()
        back = int(root.wm_frame(), 16)
        u32.SetWindowPos(back, mp.TOPMOST, 0, 0, 0, 0, 0x3 | 0x10)
        u32.SetWindowPos(h, mp.TOPMOST, 0, 0, 0, 0, 0x3 | 0x10)
        mp.activate(h)
        time.sleep(0.8)
        root.update()
        mp.keep_below(h, back)
        worst = (0, 0, None)
        for step in range(1, 13):
            w, hh = r - l + step * 40, b - t + step * 25
            u32.SetWindowPos(h, None, 0, 0, w, hh, 0x2 | 0x4 | 0x10)  # NOMOVE|NOZORDER|NOACTIVATE
            img = mp.grab(mp.frame(h))
            inner = img.crop((4, 4, img.width - 4, img.height - 4))
            magenta = share(inner, lambda p: p[0] > 200 and p[1] < 70 and p[2] > 200)
            black = share(inner, lambda p: p == (0, 0, 0))
            if magenta + black > worst[0] + worst[1]:
                worst = (magenta, black, img)
            print(f'  resize step {step:2d} -> {w}x{hh}: see-through {magenta:.1%}, black {black:.1%}')
        if worst[2] is not None:
            worst[2].save(os.path.join(mp.SHOTS, f'mica-{run}-resize-worst.png'))
        time.sleep(0.8)
        img = mp.grab(mp.frame(h))
        inner = img.crop((4, 4, img.width - 4, img.height - 4))
        print(f'  settled: see-through {share(inner, lambda p: p[0] > 200 and p[1] < 70 and p[2] > 200):.1%}')
        u32.SetWindowPos(h, mp.NOTOPMOST, 0, 0, 0, 0, 0x3 | 0x10)
        root.destroy()
    finally:
        proc.kill()


if __name__ == '__main__':
    main()
