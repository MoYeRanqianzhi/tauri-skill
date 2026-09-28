"""Harness for poc/mica-poc (tauri-windows-mica skill). Windows 11 only.

Usage:  python mica_probe.py <run name> [VAR=value ...]     e.g.  python mica_probe.py dark POC_THEME=dark

Launches mica-poc.exe with the given POC_* env vars, waits for the page, then:
  - reads DWMWA_SYSTEMBACKDROP_TYPE / DWMWA_USE_IMMERSIVE_DARK_MODE cross-process;
  - puts our own solid Tk window (magenta, then green) right behind the app and diffs two
    screenshots: pixels that change are see-through (no backdrop behind a transparent page);
  - compares the native caption row with the page's top row (bare Mica must match);
  - repeats the caption/page comparison with the app inactive (a 1x1 Tk window takes focus);
  - with POC_ACTIONS, screenshots after each page action.
Screenshots go to poc/shots/mica-<run>-*.png.

Safety: no mouse movement, no keystrokes. It only touches windows it created: the app it launched
(found by PID) and its own Tk windows. Topmost is dropped and the app is killed at the end.
"""
import ctypes
import ctypes.wintypes as wt
import json
import os
import subprocess
import sys
import time
import tkinter as tk

from PIL import ImageChops, ImageGrab

u32 = ctypes.windll.user32
dwm = ctypes.windll.dwmapi
u32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))  # per-monitor v2: physical px everywhere
u32.SetWindowPos.argtypes = [wt.HWND, wt.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wt.UINT]
u32.SetForegroundWindow.argtypes = [wt.HWND]
u32.BringWindowToTop.argtypes = [wt.HWND]
u32.GetForegroundWindow.restype = wt.HWND
u32.GetWindowThreadProcessId.argtypes = [wt.HWND, ctypes.c_void_p]
u32.AttachThreadInput.argtypes = [wt.DWORD, wt.DWORD, wt.BOOL]
u32.FindWindowExW.restype = wt.HWND
u32.FindWindowExW.argtypes = [wt.HWND, wt.HWND, wt.LPCWSTR, wt.LPCWSTR]
u32.SendMessageTimeoutW.argtypes = [wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM, wt.UINT, wt.UINT, ctypes.c_void_p]
dwm.DwmGetWindowAttribute.argtypes = [wt.HWND, wt.DWORD, ctypes.c_void_p, wt.DWORD]
TOPMOST, NOTOPMOST = wt.HWND(-1), wt.HWND(-2)
HERE = os.path.dirname(os.path.abspath(__file__))
EXE = os.path.join(HERE, 'mica-poc', 'src-tauri', 'target', 'debug', 'mica-poc.exe')
LOG = os.path.join(HERE, 'app.log')
SHOTS = os.path.join(HERE, 'shots')
BACKDROP = {0: 'auto', 1: 'none', 2: 'mica', 3: 'acrylic', 4: 'mica alt'}


def log_lines():
    return open(LOG, encoding='utf-8', errors='replace').read().splitlines()


def wait_log(prefix, timeout=20, after=0):
    end = time.time() + timeout
    while time.time() < end:
        hits = [l for l in log_lines()[after:] if l.startswith(prefix)]
        if hits:
            return hits[-1]
        time.sleep(0.2)
    return None


def windows_of(pid):
    """Top-level 'Tauri Window' windows owned by pid (our launched app only)."""
    found = []
    proc = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)

    def cb(h, _):
        p = wt.DWORD()
        u32.GetWindowThreadProcessId(h, ctypes.byref(p))
        buf = ctypes.create_unicode_buffer(64)
        u32.GetClassNameW(h, buf, 64)
        if p.value == pid and buf.value == 'Tauri Window' and u32.FindWindowExW(h, None, 'WRY_WEBVIEW', None):
            found.append(h)
        return True
    u32.EnumWindows(proc(cb), 0)
    return found


def title(h):
    buf = ctypes.create_unicode_buffer(256)
    u32.GetWindowTextW(h, buf, 256)
    return buf.value


def rect(h):
    r = wt.RECT()
    u32.GetWindowRect(h, ctypes.byref(r))
    return r.left, r.top, r.right, r.bottom


def frame(h):
    r = wt.RECT()
    dwm.DwmGetWindowAttribute(h, 9, ctypes.byref(r), 16)  # DWMWA_EXTENDED_FRAME_BOUNDS (visible frame)
    return r.left, r.top, r.right, r.bottom


def client_origin(h):
    p = wt.POINT(0, 0)
    u32.ClientToScreen(h, ctypes.byref(p))
    r = wt.RECT()
    u32.GetClientRect(h, ctypes.byref(r))
    return p.x, p.y, p.x + r.right, p.y + r.bottom


def dwm_int(h, attr):
    v = ctypes.c_int(-1)
    hr = dwm.DwmGetWindowAttribute(h, attr, ctypes.byref(v), 4)
    return v.value if hr == 0 else f'hr={hr & 0xFFFFFFFF:#x}'


def buttons(h):
    b = wt.RECT()
    dwm.DwmGetWindowAttribute(h, 5, ctypes.byref(b), 16)  # DWMWA_CAPTION_BUTTON_BOUNDS, window-relative
    l, t, _, _ = rect(h)
    return b.left + l, b.top + t, b.right + l, b.bottom + t


def activate(h):
    fg = u32.GetForegroundWindow()
    if fg != h:
        me = ctypes.windll.kernel32.GetCurrentThreadId()
        other = u32.GetWindowThreadProcessId(fg, None) if fg else 0
        if other:
            u32.AttachThreadInput(me, other, True)
        u32.SetForegroundWindow(h)
        u32.BringWindowToTop(h)
        if other:
            u32.AttachThreadInput(me, other, False)


def grab(box):
    return ImageGrab.grab(bbox=box, all_screens=True).convert('RGB')


def keep_below(h, back):
    """Put our backdrop window directly below the app and confirm the app is what is on screen.

    Tk can re-raise its window while processing events, so this runs before every screenshot.
    """
    u32.GetAncestor.restype = wt.HWND
    u32.GetAncestor.argtypes = [wt.HWND, wt.UINT]
    u32.WindowFromPoint.restype = wt.HWND
    u32.WindowFromPoint.argtypes = [wt.POINT]
    for _ in range(10):
        u32.SetWindowPos(back, h, 0, 0, 0, 0, 0x1 | 0x2 | 0x10)  # insert after the app: NOSIZE|NOMOVE|NOACTIVATE
        cl, ct, cr, cb = client_origin(h)
        under = u32.WindowFromPoint(wt.POINT((cl + cr) // 2, (ct + cb) // 2))
        if under and u32.GetAncestor(under, 2) == h:
            return True
        time.sleep(0.2)
    print('  WARNING: could not keep the backdrop window below the app')
    return False


def diff(a, b):
    return max(abs(x - y) for x, y in zip(a, b))


def see_through(a, b):
    """(whole-window share, inner share) of pixels that changed with the color behind the window.

    "inner" skips the 3 px frame ring and the 16 px corner squares: the Win11 border and the rounded
    corners let the color behind blend in on every window, transparent or not.
    """
    mask = ImageChops.difference(a, b).convert('L').point(lambda v: 255 if v > 24 else 0)
    w, hgt = mask.size
    whole = sum(mask.histogram()[255:])
    inner = mask.crop((3, 3, w - 3, hgt - 3))
    for x0, y0 in ((0, 0), (inner.width - 13, 0), (0, inner.height - 13), (inner.width - 13, inner.height - 13)):
        inner.paste(0, (x0, y0, x0 + 13, y0 + 13))
    return whole / (w * hgt), sum(inner.histogram()[255:]) / (inner.width * inner.height)


def caption_vs_page(h, img, box, mode):
    """Fraction of sampled columns where the page's top row matches the backdrop reference.

    native mode: reference = the caption row 3 px above the client area, page = 2 px below it,
                 every 2nd column from the left edge to the caption buttons. Title text columns
                 never match, so a page that shows bare Mica anywhere along its top edge matches
                 in a long contiguous run; the longest run is returned too.
    custom mode: reference = inside the minimize button 4 px from its left edge (DWM draws only the
                 backdrop there at rest), page = 6 px left of the buttons, several rows.
    """
    cl, ct, cr, _ = client_origin(h)
    bl, bt, br, bb = buttons(h)
    px = lambda x, y: img.getpixel((x - box[0], y - box[1]))
    pairs = []
    if mode == 'native':
        for x in range(cl + 4, bl - 16, 2):
            pairs.append((px(x, ct - 3), px(x, ct + 2)))
    else:
        for y in range(max(bt, box[1]) + 4, bb - 4, 3):
            pairs.append((px(bl + 4, y), px(bl - 6, y)))
    hits = [diff(a, b) <= 3 for a, b in pairs]
    run = best = 0
    for hit in hits:
        run = run + 1 if hit else 0
        best = max(best, run)
    sample = next((p for p, hit in zip(pairs, hits) if hit), pairs[len(pairs) // 2] if pairs else None)
    return f'{sum(hits)}/{len(hits)} (longest run {best})', sample


def run_actions(h, box, mode, root, back, actions, run):
    """Screenshot after each POC_ACTIONS step (the page runs step i at 5 s + 4 s * i)."""
    for i, a in enumerate(actions):
        line = wait_log(f'[page] action {i} ', 30)
        if not line:
            print(f'  action {i} {a}: never ran')
            return
        time.sleep(1.2)
        if u32.IsIconic(h):
            print(f'  action {i} {a}: minimized | backdrop={BACKDROP.get(dwm_int(h, 38), dwm_int(h, 38))} dark={dwm_int(h, 20)}')
            continue
        box = frame(h)
        l, t, r, b = rect(h)
        root.geometry(f'{r - l}x{b - t}+{l}+{t}')
        root.configure(bg='#ff00ff')
        root.update()
        time.sleep(0.3)
        keep_below(h, back)
        m1 = grab(box)
        m1.save(os.path.join(SHOTS, f'mica-{run}-action{i}.png'))
        root.configure(bg='#00ff00')
        root.update()
        time.sleep(0.4)
        keep_below(h, back)
        m2 = grab(box)
        whole, inner = see_through(m1, m2)
        ok, sample = caption_vs_page(h, m1, box, mode)
        res = [l for l in log_lines() if l.startswith(('[page] theme ', '[page] backdrop ', '[page] opaque ', '[page] window '))]
        print(f'  action {i} {a}: {res[-1][7:] if res else "?"} | backdrop={BACKDROP.get(dwm_int(h, 38), dwm_int(h, 38))} '
              f'dark={dwm_int(h, 20)} | see-through inner {inner:.2%} | page-top match {ok} sample {sample}')


def finish(h, root):
    for l in log_lines():
        if l.startswith('[page] ') and ('failed' in l or 'rejection' in l or 'shown' in l):
            print('  page :', l)
    status = [l for l in log_lines() if l.startswith('[page] status ')]
    if status:
        print('  last status:', status[-1][len('[page] status '):])
    u32.SetWindowPos(h, NOTOPMOST, 0, 0, 0, 0, 0x3 | 0x10)
    root.destroy()


def main():
    run = sys.argv[1]
    env = dict(os.environ, NO_AT_BRIDGE='1')
    env.update(kv.split('=', 1) for kv in sys.argv[2:])
    os.makedirs(SHOTS, exist_ok=True)
    subprocess.run(['taskkill', '/IM', 'mica-poc.exe', '/F'], capture_output=True)
    time.sleep(0.5)
    proc = subprocess.Popen([EXE], stdout=open(LOG, 'w', encoding='utf-8'), stderr=subprocess.STDOUT, env=env)
    try:
        target = env.get('POC_TARGET', 'main')
        tag = '' if target == 'main' else f'({target}) '
        if not wait_log(f'[page] {tag}status ', 25):
            print('page never reported status; log tail:', *log_lines()[-15:], sep='\n  ')
            return
        want = 'mica-poc' if target == 'main' else f'mica-poc {target}'
        wins = [w for w in windows_of(proc.pid) if title(w) == env.get('POC_TITLE', want)]
        if len(wins) != 1:
            print('expected one app window titled', want, 'found', [(w, title(w)) for w in windows_of(proc.pid)])
            return
        h = wins[0]
        time.sleep(0.8)
        mode = 'custom' if u32.FindWindowExW(h, None, 'TAURI_TITLEBAR_TOP_RESIZE', None) or client_origin(h)[1] <= frame(h)[1] + 1 else 'native'
        print(f'[{run}]', ' '.join(sys.argv[2:]) or '(recipe)')
        print('  rust :', next((l for l in log_lines() if l.startswith('[rust] window')), '?'))
        print('  page :', next((l for l in log_lines() if l.startswith(f'[page] {tag}mica ')), '?'))

        # Our own solid windows: a backdrop right behind the app, and a 1x1 focus sink in a corner.
        root = tk.Tk()
        root.overrideredirect(True)
        l, t, r, b = rect(h)
        root.geometry(f'{r - l}x{b - t}+{l}+{t}')
        root.configure(bg='#ff00ff')
        sink = tk.Toplevel(root)
        sink.overrideredirect(True)
        sink.geometry('1x1+0+0')
        root.update()
        back = int(root.wm_frame(), 16)
        sink_h = int(sink.wm_frame(), 16)
        u32.SetWindowPos(back, TOPMOST, 0, 0, 0, 0, 0x3 | 0x10)
        u32.SetWindowPos(h, TOPMOST, 0, 0, 0, 0, 0x3 | 0x10)
        activate(h)
        time.sleep(1.0)
        root.update()
        box = frame(h)
        print('  dwm  : backdrop =', BACKDROP.get(dwm_int(h, 38), dwm_int(h, 38)), '| dark mode =', dwm_int(h, 20),
              '| foreground =', u32.GetForegroundWindow() == h, '| mode =', mode)

        actions = [a for a in env.get('POC_ACTIONS', '').split(',') if a]
        keep_below(h, back)
        magenta = grab(box)
        magenta.save(os.path.join(SHOTS, f'mica-{run}-active.png'))
        if actions:  # the page's actions start 5 s after launch; skip the baseline so they don't overlap
            run_actions(h, box, mode, root, back, actions, run)
            return finish(h, root)
        root.configure(bg='#00ff00')
        root.update()
        time.sleep(0.6)
        keep_below(h, back)
        green = grab(box)
        whole, inner = see_through(magenta, green)
        print(f'  see-through: {whole:.2%} of the window changed with the color behind it ({inner:.2%} inside the frame ring)')
        ok, sample = caption_vs_page(h, magenta, box, mode)
        print(f'  active  : page top matches backdrop in {ok} columns; sample backdrop/page = {sample}')

        activate(sink_h)
        time.sleep(1.2)
        root.update()
        keep_below(h, back)
        inactive = grab(box)
        inactive.save(os.path.join(SHOTS, f'mica-{run}-inactive.png'))
        ok, sample = caption_vs_page(h, inactive, box, mode)
        print(f'  inactive: page top matches backdrop in {ok} columns; sample backdrop/page = {sample}',
              '| foreground is sink =', u32.GetForegroundWindow() == sink_h)

        if env.get('POC_SETTINGCHANGE') == '1':
            before = dwm_int(h, 20)
            u32.SendMessageTimeoutW(h, 0x1A, 0, 0, 0x2, 2000, None)  # WM_SETTINGCHANGE, our app only
            time.sleep(0.8)
            print(f'  WM_SETTINGCHANGE: dark mode {before} -> {dwm_int(h, 20)}')
            grab(box).save(os.path.join(SHOTS, f'mica-{run}-settingchange.png'))

        finish(h, root)
    finally:
        if os.environ.get('KEEP') != '1':
            proc.kill()


if __name__ == '__main__':
    main()
