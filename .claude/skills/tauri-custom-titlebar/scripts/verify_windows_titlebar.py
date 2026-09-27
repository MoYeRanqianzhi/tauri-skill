"""Verify a running Tauri window that uses assets/windows_titlebar.rs. Windows only.

Usage:  python verify_windows_titlebar.py "<exact window title>"
Needs:  Python 3.9+, Pillow (pip install pillow).

MOVES THE REAL MOUSE AND CLICKS the window's own maximize button. Tell the user not to touch the mouse
for ~15 s. It refuses to touch any window that is not a Tauri window with a WRY_WEBVIEW child.

Exit code 0 when every check passes. Each line prints PASS/FAIL with the measured values.
"""
import ctypes
import ctypes.wintypes as wt
import sys
import time

from PIL import ImageGrab

u32 = ctypes.windll.user32
dwm = ctypes.windll.dwmapi
u32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))  # per-monitor v2: all coordinates are physical
u32.SendMessageW.restype = ctypes.c_ssize_t
u32.SendMessageW.argtypes = [wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM]
u32.WindowFromPoint.argtypes = [wt.POINT]
u32.WindowFromPoint.restype = wt.HWND
u32.FindWindowExW.restype = wt.HWND
u32.GetWindow.restype = wt.HWND
HT = {1: 'CLIENT', 2: 'CAPTION', 8: 'MINBUTTON', 9: 'MAXBUTTON', 12: 'TOP', 13: 'TOPLEFT', 14: 'TOPRIGHT', 20: 'CLOSE'}
failures = []


def check(name, ok, detail):
    print(f"{'PASS' if ok else 'FAIL'}  {name}: {detail}")
    if not ok:
        failures.append(name)


def cls(h):
    buf = ctypes.create_unicode_buffer(256)
    u32.GetClassNameW(h, buf, 256)
    return buf.value


def rect(h):
    r = wt.RECT()
    u32.GetWindowRect(h, ctypes.byref(r))
    return r.left, r.top, r.right, r.bottom


def button_rects(h):
    """Screen rects of (min, max, close) from DWMWA_CAPTION_BUTTON_BOUNDS, split into equal thirds."""
    b = wt.RECT()
    dwm.DwmGetWindowAttribute(h, 5, ctypes.byref(b), 16)
    wl, wtop, _, _ = rect(h)
    left, top, right, bottom = b.left + wl, b.top + wtop, b.right + wl, b.bottom + wtop
    top = max(top, 0 if u32.IsZoomed(h) else top)  # maximized: skip rows pushed above the screen
    w = (right - left) / 3
    return [(int(left + w * i), top, int(left + w * (i + 1)), bottom) for i in range(3)]


def center(r):
    return (r[0] + r[2]) // 2, (r[1] + r[3]) // 2


def nchittest(h, x, y):
    return HT.get(u32.SendMessageW(h, 0x84, 0, (y & 0xFFFF) << 16 | (x & 0xFFFF)), '?')


def under(x, y):
    return u32.WindowFromPoint(wt.POINT(x, y))


def pixel(x, y):
    return ImageGrab.grab(bbox=(x, y, x + 1, y + 1), all_screens=True).getpixel((0, 0))


def move(x, y):
    u32.SetCursorPos(x, y)


def click(x, y):
    move(x, y)
    time.sleep(0.2)
    u32.mouse_event(0x2, 0, 0, 0, 0)
    u32.mouse_event(0x4, 0, 0, 0, 0)


def activate(h):
    # Tapping Alt grants foreground rights, but leaves the window in system-menu keyboard mode, which
    # swallows mouse input; Escape leaves that mode. Topmost keeps other apps from covering it.
    u32.SetWindowPos(h, -1, 0, 0, 0, 0, 0x3 | 0x10)
    u32.keybd_event(0x12, 0, 0, 0)
    u32.SetForegroundWindow(h)
    u32.keybd_event(0x12, 0, 2, 0)
    time.sleep(0.2)
    u32.keybd_event(0x1B, 0, 0, 0)
    u32.keybd_event(0x1B, 0, 2, 0)
    time.sleep(0.3)


def hit_checks(h, state):
    names = ['MINBUTTON', 'MAXBUTTON', 'CLOSE']
    for name, r in zip(names, button_rects(h)):
        x, y = center(r)
        got = nchittest(h, x, y)
        check(f'{state}: {name} hit-test', got == name, f'WM_NCHITTEST at {(x, y)} = {got}')
        top = under(x, y)
        check(f'{state}: {name} not covered by webview', top == h, f'WindowFromPoint = {cls(top)}')


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    h = u32.FindWindowW(None, sys.argv[1])
    if not h:
        sys.exit(f'no window titled {sys.argv[1]!r}')
    container = u32.FindWindowExW(h, None, 'WRY_WEBVIEW', None)
    if cls(h) != 'Tauri Window' or not container:
        sys.exit(f'refusing: {cls(h)!r} is not a Tauri window with a WRY_WEBVIEW child')

    activate(h)
    if u32.IsZoomed(h):
        u32.ShowWindow(h, 9)
        time.sleep(1.5)

    band = u32.FindWindowExW(h, None, 'TAURI_TITLEBAR_TOP_RESIZE', None)
    check('resize band exists', bool(band), 'TAURI_TITLEBAR_TOP_RESIZE child found' if band else 'missing: install() not called?')
    region = u32.GetWindowRgnBox(container, ctypes.byref(wt.RECT()))
    check('WRY_WEBVIEW has a window region', region in (2, 3), f'GetWindowRgnBox = {region} (2/3 = region set)')

    hit_checks(h, 'restored')

    left, top, right, _ = rect(h)
    vis = wt.RECT()
    dwm.DwmGetWindowAttribute(h, 9, ctypes.byref(vis), 16)
    mid = (vis.left + vis.right) // 2
    over = under(mid, vis.top + 2)
    ht = HT.get(u32.SendMessageW(over, 0x84, 0, ((vis.top + 2) & 0xFFFF) << 16 | (mid & 0xFFFF)), '?')
    check('top edge resizes', cls(over) == 'TAURI_TITLEBAR_TOP_RESIZE' and ht == 'TOP', f'{cls(over)} -> {ht}')

    # Hover must clear when the mouse slides from a button down into the page.
    mn, mx, cl = button_rects(h)
    for name, r in (('minimize', mn), ('maximize', mx)):
        x, y = center(r)
        sample = (x, r[1] + 3)
        move(x, r[3] + 150)
        time.sleep(0.5)
        base = pixel(*sample)
        move(x, y)
        time.sleep(0.2)
        move(x + 1, y)
        time.sleep(0.8)
        hot = pixel(*sample)
        for i in range(1, 11):
            move(x, y + i * 15)
            time.sleep(0.02)
        time.sleep(0.8)
        after = pixel(*sample)
        u32.keybd_event(0x1B, 0, 0, 0)  # close the Snap Layouts flyout if it opened
        u32.keybd_event(0x1B, 0, 2, 0)
        check(f'{name} hover clears on leave', after == base, f'base={base} hover={hot} after-leave={after}')
        if hot == base:
            print(f'      note: no hover change seen on {name}; rerun if the mouse was moved')

    # Maximize with a real click (ShowWindow from another process can leave the webview unresized).
    click(*center(mx))
    time.sleep(1.8)
    check('maximize button maximizes', bool(u32.IsZoomed(h)), f'IsZoomed = {bool(u32.IsZoomed(h))}')
    if u32.IsZoomed(h):
        move(center(mx)[0], 400)
        time.sleep(0.4)
        hit_checks(h, 'maximized')
        click(*center(button_rects(h)[1]))
        time.sleep(1.5)
        check('restore button restores', not u32.IsZoomed(h), f'IsZoomed = {bool(u32.IsZoomed(h))}')

    u32.SetWindowPos(h, -2, 0, 0, 0, 0, 0x3 | 0x10)  # drop topmost
    print('\nALL PASS' if not failures else f'\n{len(failures)} FAILED: {failures}')
    sys.exit(1 if failures else 0)


if __name__ == '__main__':
    main()
