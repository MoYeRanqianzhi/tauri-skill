"""Win32 probe for the titlebar POC: window tree, hit-tests, real mouse input, screenshots."""
import ctypes, ctypes.wintypes as wt, sys, time, json
from PIL import ImageGrab

u32 = ctypes.windll.user32
u32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))  # per-monitor v2: physical px
dwm = ctypes.windll.dwmapi
LRESULT = ctypes.c_ssize_t
u32.SendMessageW.restype = LRESULT
u32.SendMessageW.argtypes = [wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM]
u32.WindowFromPoint.argtypes = [wt.POINT]
u32.WindowFromPoint.restype = wt.HWND
HT = {0: 'NOWHERE', 1: 'CLIENT', 2: 'CAPTION', 3: 'SYSMENU', 8: 'MINBUTTON', 9: 'MAXBUTTON', 20: 'CLOSE',
      10: 'LEFT', 11: 'RIGHT', 12: 'TOP', 13: 'TOPLEFT', 14: 'TOPRIGHT', 15: 'BOTTOM', -1: 'TRANSPARENT'}


def find(title):
    h = u32.FindWindowW(None, title)
    if not h:
        sys.exit(f'window {title!r} not found')
    return h


def rect(h, client=False):
    r = wt.RECT()
    if client:
        u32.GetClientRect(h, ctypes.byref(r))
        p = wt.POINT(0, 0); u32.ClientToScreen(h, ctypes.byref(p))
        return (p.x, p.y, p.x + r.right, p.y + r.bottom)
    u32.GetWindowRect(h, ctypes.byref(r))
    return (r.left, r.top, r.right, r.bottom)


def visible_frame(h):
    r = wt.RECT()
    dwm.DwmGetWindowAttribute(h, 9, ctypes.byref(r), 16)  # DWMWA_EXTENDED_FRAME_BOUNDS
    return (r.left, r.top, r.right, r.bottom)


def cls(h):
    b = ctypes.create_unicode_buffer(256); u32.GetClassNameW(h, b, 256); return b.value


def tree(h, depth=0, out=None):
    out = [] if out is None else out
    pid = wt.DWORD(); u32.GetWindowThreadProcessId(h, ctypes.byref(pid))
    out.append(f"{'  '*depth}{h:#x} {cls(h)} pid={pid.value} rect={rect(h)} vis={bool(u32.IsWindowVisible(h))}")
    child = u32.GetWindow(h, 5)  # GW_CHILD
    while child:
        tree(child, depth + 1, out); child = u32.GetWindow(child, 2)  # GW_HWNDNEXT
    return out


def hit(h, x, y):
    under = u32.WindowFromPoint(wt.POINT(x, y))
    lp = (y & 0xFFFF) << 16 | (x & 0xFFFF)
    r = u32.SendMessageW(h, 0x84, 0, lp)
    return {'pt': (x, y), 'under': cls(under) if under else None, 'nchittest': HT.get(r, r)}


def move(x, y): u32.SetCursorPos(x, y)


def click(x, y, button='left', double=False):
    move(x, y); time.sleep(0.15)
    down, up = (0x2, 0x4) if button == 'left' else (0x8, 0x10)
    for _ in range(2 if double else 1):
        u32.mouse_event(down, 0, 0, 0, 0); u32.mouse_event(up, 0, 0, 0, 0); time.sleep(0.05)


def drag(x0, y0, x1, y1):
    move(x0, y0); time.sleep(0.2); u32.mouse_event(0x2, 0, 0, 0, 0); time.sleep(0.2)
    for i in range(1, 21):
        move(x0 + (x1 - x0) * i // 20, y0 + (y1 - y0) * i // 20); time.sleep(0.02)
    time.sleep(0.2); u32.mouse_event(0x4, 0, 0, 0, 0); time.sleep(0.3)


def key(vk, up=False): u32.keybd_event(vk, 0, 2 if up else 0, 0)


def shot(path, box=None):
    ImageGrab.grab(bbox=box, all_screens=True).save(path)


def foreground(h):
    # Temporarily topmost so other apps cannot cover the window under test.
    u32.SetWindowPos(h, -1, 0, 0, 0, 0, 0x3 | 0x10)
    # Tapping Alt grants foreground rights but puts the window into system-menu keyboard mode, which
    # swallows mouse messages (cursor stuck on arrow, no hover). Escape leaves that mode.
    key(0x12); u32.SetForegroundWindow(h); key(0x12, True); time.sleep(0.2)
    key(0x1B); key(0x1B, True); time.sleep(0.2)


if __name__ == '__main__':
    h = find(sys.argv[1] if len(sys.argv) > 1 else 'titlebar-poc')
    print('\n'.join(tree(h)))
    print('window', rect(h), 'client', rect(h, True), 'frame', visible_frame(h))


EXE = r'G:\ClaudeProjects\tauri-skill\poc\titlebar-poc\src-tauri\target\debug\titlebar-poc.exe'
LOG = r'G:\ClaudeProjects\tauri-skill\poc\app.log'


def launch(env=None, wait=4):
    import subprocess, os
    subprocess.run(['taskkill', '/IM', 'titlebar-poc.exe', '/F'], capture_output=True)
    time.sleep(0.5)
    e = dict(os.environ, **(env or {}))
    subprocess.Popen([EXE], stdout=open(LOG, 'w'), stderr=subprocess.STDOUT, env=e)
    time.sleep(wait)
    return find('titlebar-poc')


def log_lines():
    return open(LOG, encoding='utf-8', errors='replace').read().splitlines()


def rects(h):
    """Element rects from the page, converted to screen physical px (centre helpers via center())."""
    line = [l for l in log_lines() if l.startswith('[page] rects ')][-1]
    l, t, _, _ = rect(h, True)
    return {k: (v[0] + l, v[1] + t, v[2] + l, v[3] + t) for k, v in json.loads(line[len('[page] rects '):]).items()}


def center(r): return ((r[0] + r[2]) // 2, (r[1] + r[3]) // 2)
