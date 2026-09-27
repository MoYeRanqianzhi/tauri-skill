"""Verify a running Tauri window that uses assets/windows_titlebar.rs. Windows only.

Usage:  python verify_windows_titlebar.py "<exact window title>" [window class, default "Tauri Window"]
Needs:  Python 3.9+, Pillow (pip install pillow).

MOVES THE REAL MOUSE for ~15 s and clicks the app's own maximize/restore button. Tell the user not
to touch the mouse. Safety: it sends no keystrokes. It clicks or sends messages only after checking
that the point belongs to the target window, and it refuses windows that are not Tauri windows with
a WRY_WEBVIEW child. Give the app a unique title.

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
u32.GetAncestor.restype = wt.HWND
u32.GetForegroundWindow.restype = wt.HWND
u32.FindWindowW.restype = wt.HWND
u32.FindWindowExW.restype = wt.HWND
# Without argtypes ctypes passes ints as 32-bit, so HWND_TOPMOST (-1) would arrive as 0xFFFFFFFF and fail.
u32.SetWindowPos.argtypes = [wt.HWND, wt.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wt.UINT]
u32.SetForegroundWindow.argtypes = [wt.HWND]
u32.GetAncestor.argtypes = [wt.HWND, wt.UINT]
u32.GetWindowThreadProcessId.argtypes = [wt.HWND, ctypes.c_void_p]
u32.AttachThreadInput.argtypes = [wt.DWORD, wt.DWORD, wt.BOOL]
u32.BringWindowToTop.argtypes = [wt.HWND]
HWND_TOPMOST, HWND_NOTOPMOST = wt.HWND(-1), wt.HWND(-2)
HT = {1: 'CLIENT', 2: 'CAPTION', 8: 'MINBUTTON', 9: 'MAXBUTTON', 12: 'TOP', 13: 'TOPLEFT', 14: 'TOPRIGHT', 20: 'CLOSE'}
GA_ROOT = 2
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


def client_center(h):
    r = wt.RECT()
    u32.GetClientRect(h, ctypes.byref(r))
    p = wt.POINT(r.right // 2, r.bottom // 2)
    u32.ClientToScreen(h, ctypes.byref(p))
    return p.x, p.y


def button_rects(h):
    """Screen rects of (min, max, close) from DWMWA_CAPTION_BUTTON_BOUNDS, split into equal thirds."""
    b = wt.RECT()
    dwm.DwmGetWindowAttribute(h, 5, ctypes.byref(b), 16)
    wl, wtop, _, _ = rect(h)
    left, top, right, bottom = b.left + wl, b.top + wtop, b.right + wl, b.bottom + wtop
    if u32.IsZoomed(h):
        top = max(top, 0)  # skip rows pushed above the screen
    w = (right - left) / 3
    return [(int(left + w * i), top, int(left + w * (i + 1)), bottom) for i in range(3)]


def center(r):
    return (r[0] + r[2]) // 2, (r[1] + r[3]) // 2


def under(x, y):
    return u32.WindowFromPoint(wt.POINT(x, y))


def owned(target, x, y):
    """True if the window under (x, y) is `target` or one of its children."""
    w = under(x, y)
    return bool(w) and u32.GetAncestor(w, GA_ROOT) == target


def nchittest(h, x, y):
    return HT.get(u32.SendMessageW(h, 0x84, 0, (y & 0xFFFF) << 16 | (x & 0xFFFF)), '?')


def pixel(x, y):
    return ImageGrab.grab(bbox=(x, y, x + 1, y + 1), all_screens=True).getpixel((0, 0))


def move(x, y):
    u32.SetCursorPos(x, y)


def click(target, x, y):
    if not owned(target, x, y):
        sys.exit(f'refusing to click {(x, y)}: the point does not belong to the target window')
    move(x, y)
    time.sleep(0.2)
    u32.mouse_event(0x2, 0, 0, 0, 0)
    u32.mouse_event(0x4, 0, 0, 0, 0)


def activate(h):
    # Bring the target to the front without injecting input into other apps: Alt-tap tricks would
    # send the key to whatever app is in front (and leave the target in system-menu mode).
    # AttachThreadInput to the foreground thread lets SetForegroundWindow pass the foreground lock.
    u32.SetWindowPos(h, HWND_TOPMOST, 0, 0, 0, 0, 0x3 | 0x10)
    fg = u32.GetForegroundWindow()
    if fg and fg != h:
        me = ctypes.windll.kernel32.GetCurrentThreadId()
        other = u32.GetWindowThreadProcessId(fg, None)
        u32.AttachThreadInput(me, other, True)
        u32.SetForegroundWindow(h)
        u32.BringWindowToTop(h)
        u32.AttachThreadInput(me, other, False)
    time.sleep(0.4)
    return u32.GetForegroundWindow() == h and owned(h, *client_center(h))


def hit_checks(h, state):
    for name, r in zip(['MINBUTTON', 'MAXBUTTON', 'CLOSE'], button_rects(h)):
        x, y = center(r)
        got = nchittest(h, x, y)
        check(f'{state}: {name} hit-test', got == name, f'WM_NCHITTEST at {(x, y)} = {got}')
        top = under(x, y)
        check(f'{state}: {name} not covered by webview', top == h, f'WindowFromPoint = {cls(top)}')


def main():
    if len(sys.argv) not in (2, 3):
        sys.exit(__doc__)
    title, klass = sys.argv[1], sys.argv[2] if len(sys.argv) == 3 else 'Tauri Window'
    h = u32.FindWindowW(klass, title)
    if not h:
        sys.exit(f'no window of class {klass!r} titled {title!r}')
    container = u32.FindWindowExW(h, None, 'WRY_WEBVIEW', None)
    if not container:
        sys.exit('refusing: the window has no WRY_WEBVIEW child, so it is not a Tauri webview window')

    if not activate(h):
        sys.exit('could not bring the window to the front; click it once and rerun')
    check('window activated', True, 'foreground = target and on top')
    if u32.IsZoomed(h):
        click(h, *center(button_rects(h)[1]))  # restore with the real button
        time.sleep(1.5)

    band = u32.FindWindowExW(h, None, 'TAURI_TITLEBAR_TOP_RESIZE', None)
    check('resize band exists', bool(band), 'TAURI_TITLEBAR_TOP_RESIZE child found' if band else 'missing: install() not called?')
    region = u32.GetWindowRgnBox(container, ctypes.byref(wt.RECT()))
    check('WRY_WEBVIEW has a window region', region in (2, 3), f'GetWindowRgnBox = {region} (2/3 = region set)')

    hit_checks(h, 'restored')

    vis = wt.RECT()
    dwm.DwmGetWindowAttribute(h, 9, ctypes.byref(vis), 16)  # DWMWA_EXTENDED_FRAME_BOUNDS
    mid, y = (vis.left + vis.right) // 2, vis.top + 2
    if owned(h, mid, y):
        over = under(mid, y)
        ht = HT.get(u32.SendMessageW(over, 0x84, 0, (y & 0xFFFF) << 16 | (mid & 0xFFFF)), '?')
        check('top edge resizes', cls(over) == 'TAURI_TITLEBAR_TOP_RESIZE' and ht == 'TOP', f'{cls(over)} -> {ht}')
    else:
        check('top edge resizes', False, 'top edge is covered by another window')

    # Hover must clear when the mouse slides from a button down into the page.
    mn, mx, _ = button_rects(h)
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
        for i in range(1, 11):  # sliding into the page also closes the Snap Layouts flyout
            move(x, y + i * 15)
            time.sleep(0.02)
        time.sleep(0.8)
        after = pixel(*sample)
        check(f'{name} hover clears on leave', after == base, f'base={base} hover={hot} after-leave={after}')
        if hot == base:
            print(f'      note: no hover change seen on {name}; rerun if the mouse was moved')

    # Maximize with a real click (ShowWindow from another process can leave the webview unresized).
    click(h, *center(mx))
    time.sleep(1.8)
    check('maximize button maximizes', bool(u32.IsZoomed(h)), f'IsZoomed = {bool(u32.IsZoomed(h))}')
    if u32.IsZoomed(h):
        move(center(mx)[0], 400)
        time.sleep(0.4)
        hit_checks(h, 'maximized')
        click(h, *center(button_rects(h)[1]))
        time.sleep(1.5)
        check('restore button restores', not u32.IsZoomed(h), f'IsZoomed = {bool(u32.IsZoomed(h))}')

    move(*client_center(h))  # leave the cursor in the page, away from the buttons
    u32.SetWindowPos(h, HWND_NOTOPMOST, 0, 0, 0, 0, 0x3 | 0x10)  # drop topmost
    print('\nALL PASS' if not failures else f'\n{len(failures)} FAILED: {failures}')
    sys.exit(1 if failures else 0)


if __name__ == '__main__':
    main()
