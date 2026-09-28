"""Verify the Mica backdrop of a running Tauri window. Windows 11 only.

Usage:  python verify_windows_mica.py "<exact window title>" [window class, default "Tauri Window"]
Needs:  Python 3.9+ with tkinter, and Pillow (pip install pillow).

What it does (about 8 s, no mouse movement, no keystrokes):
  1. finds the window by class + title and refuses anything without a WRY_WEBVIEW child;
  2. reads DWMWA_SYSTEMBACKDROP_TYPE (must be Mica or Mica Alt);
  3. puts its own solid window (magenta, then green) right behind the app and compares two
     screenshots: any pixel that follows the color behind means the window is see-through;
  4. checks that the page lets the backdrop through: bare Mica along the page's top edge must
     match the native caption right above it (or the caption-button band with a custom title
     bar), or most of the page must change with the backdrop when the window goes inactive;
  5. makes its own 1x1 window active to see the inactive state, then sends WM_SETTINGCHANGE to the
     app only and checks that the dark-mode attribute (the Mica tint) does not flip.
The app is made topmost for the checks and put back afterwards. Give the app a unique title.

Exit code 0 when every check passes. Each line prints PASS/FAIL with the measured values.
"""
import ctypes
import ctypes.wintypes as wt
import sys
import time
import tkinter as tk
import winreg

from PIL import ImageChops, ImageGrab

u32 = ctypes.windll.user32
dwm = ctypes.windll.dwmapi
u32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))  # per-monitor v2: all coordinates are physical
u32.FindWindowW.restype = wt.HWND
u32.FindWindowExW.restype = wt.HWND
u32.FindWindowExW.argtypes = [wt.HWND, wt.HWND, wt.LPCWSTR, wt.LPCWSTR]
u32.GetForegroundWindow.restype = wt.HWND
u32.WindowFromPoint.restype = wt.HWND
u32.WindowFromPoint.argtypes = [wt.POINT]
u32.GetAncestor.restype = wt.HWND
u32.GetAncestor.argtypes = [wt.HWND, wt.UINT]
# Without argtypes ctypes passes ints as 32-bit, so HWND_TOPMOST (-1) would arrive as 0xFFFFFFFF and fail.
u32.SetWindowPos.argtypes = [wt.HWND, wt.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wt.UINT]
u32.SetForegroundWindow.argtypes = [wt.HWND]
u32.BringWindowToTop.argtypes = [wt.HWND]
u32.GetWindowThreadProcessId.argtypes = [wt.HWND, ctypes.c_void_p]
u32.AttachThreadInput.argtypes = [wt.DWORD, wt.DWORD, wt.BOOL]
u32.SendMessageTimeoutW.argtypes = [wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM, wt.UINT, wt.UINT, ctypes.c_void_p]
dwm.DwmGetWindowAttribute.argtypes = [wt.HWND, wt.DWORD, ctypes.c_void_p, wt.DWORD]
HWND_TOPMOST, HWND_NOTOPMOST = wt.HWND(-1), wt.HWND(-2)
BACKDROP = {0: 'auto (no effect applied)', 1: 'none (effect cleared)', 2: 'Mica', 3: 'Acrylic', 4: 'Mica Alt'}
failures = []


def check(name, ok, detail):
    print(f"{'PASS' if ok else 'FAIL'}  {name}: {detail}")
    if not ok:
        failures.append(name)


def dwm_int(h, attr):
    v = ctypes.c_int(-1)
    return v.value if dwm.DwmGetWindowAttribute(h, attr, ctypes.byref(v), 4) == 0 else None


def window_rect(h):
    r = wt.RECT()
    u32.GetWindowRect(h, ctypes.byref(r))
    return r.left, r.top, r.right, r.bottom


def frame(h):
    r = wt.RECT()
    dwm.DwmGetWindowAttribute(h, 9, ctypes.byref(r), 16)  # DWMWA_EXTENDED_FRAME_BOUNDS: the visible frame
    return r.left, r.top, r.right, r.bottom


def client(h):
    p = wt.POINT(0, 0)
    u32.ClientToScreen(h, ctypes.byref(p))
    r = wt.RECT()
    u32.GetClientRect(h, ctypes.byref(r))
    return p.x, p.y, p.x + r.right, p.y + r.bottom


def caption_buttons(h):
    b = wt.RECT()
    dwm.DwmGetWindowAttribute(h, 5, ctypes.byref(b), 16)  # DWMWA_CAPTION_BUTTON_BOUNDS, window-relative
    left, top, _, _ = window_rect(h)
    return b.left + left, b.top + top, b.right + left, b.bottom + top


def activate(h):
    # Bring a window to the front without injecting input into other apps: Alt-tap tricks would
    # send the key to whatever app is in front. AttachThreadInput to the foreground thread lets
    # SetForegroundWindow pass the foreground lock.
    fg = u32.GetForegroundWindow()
    if fg == h:
        return
    me = ctypes.windll.kernel32.GetCurrentThreadId()
    other = u32.GetWindowThreadProcessId(fg, None) if fg else 0
    if other:
        u32.AttachThreadInput(me, other, True)
    u32.SetForegroundWindow(h)
    u32.BringWindowToTop(h)
    if other:
        u32.AttachThreadInput(me, other, False)


def keep_below(h, back):
    """Keep our backdrop window directly below the app; True once the app is what is on screen."""
    for _ in range(10):
        u32.SetWindowPos(back, h, 0, 0, 0, 0, 0x1 | 0x2 | 0x10)  # insert after the app; NOSIZE|NOMOVE|NOACTIVATE
        cl, ct, cr, cb = client(h)
        under = u32.WindowFromPoint(wt.POINT((cl + cr) // 2, (ct + cb) // 2))
        if under and u32.GetAncestor(under, 2) == h:  # GA_ROOT
            return True
        time.sleep(0.2)
    return False


def grab(box):
    return ImageGrab.grab(bbox=box, all_screens=True).convert('RGB')


def see_through(a, b):
    """Share of pixels inside the frame that followed the color behind the window.

    Skips the 3 px frame ring and the 16 px corner squares: the Win11 border and the rounded corners
    blend with what is behind on every window.
    """
    mask = ImageChops.difference(a, b).convert('L').point(lambda v: 255 if v > 24 else 0)
    inner = mask.crop((3, 3, mask.width - 3, mask.height - 3))
    for x0, y0 in ((0, 0), (inner.width - 13, 0), (0, inner.height - 13), (inner.width - 13, inner.height - 13)):
        inner.paste(0, (x0, y0, x0 + 13, y0 + 13))
    return sum(inner.histogram()[255:]) / (inner.width * inner.height)


def bare_backdrop_run(h, img, box, custom):
    """Longest run of sample columns where the page's top edge equals the backdrop right beside it.

    Native title bar: the caption row 3 px above the client area vs the page row 2 px below it,
    every 2nd column up to the caption buttons (title text columns never match).
    Custom title bar: inside the minimize button (DWM draws only the backdrop there at rest) vs
    the page bar 6 px left of the buttons, every 3rd row.
    """
    cl, ct, _, _ = client(h)
    bl, bt, _, bb = caption_buttons(h)
    px = lambda x, y: img.getpixel((x - box[0], y - box[1]))
    if custom:
        pairs = [(px(bl + 4, y), px(bl - 6, y)) for y in range(max(bt, box[1]) + 4, bb - 4, 3)]
    else:
        pairs = [(px(x, ct - 3), px(x, ct + 2)) for x in range(max(cl, box[0]) + 4, bl - 16, 2)]
    run = best = 0
    for a, b in pairs:
        run = run + 1 if max(abs(p - q) for p, q in zip(a, b)) <= 3 else 0
        best = max(best, run)
    return best, len(pairs)


def changed_share(a, b, box, h):
    """Share of client-area pixels that changed by >= 2 levels between two screenshots."""
    cl, ct, cr, cb = client(h)
    crop = (max(cl, box[0]) - box[0], max(ct, box[1]) - box[1], min(cr, box[2]) - box[0], min(cb, box[3]) - box[1])
    diff = ImageChops.difference(a.crop(crop), b.crop(crop)).convert('L').point(lambda v: 255 if v >= 2 else 0)
    return sum(diff.histogram()[255:]) / (diff.width * diff.height)


def transparency_enabled():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Themes\Personalize') as k:
            return winreg.QueryValueEx(k, 'EnableTransparency')[0] == 1
    except OSError:
        return True


def main():
    if len(sys.argv) not in (2, 3):
        sys.exit(__doc__)
    title, klass = sys.argv[1], sys.argv[2] if len(sys.argv) == 3 else 'Tauri Window'
    h = u32.FindWindowW(klass, title)
    if not h:
        sys.exit(f'no window of class {klass!r} titled {title!r}')
    if not u32.FindWindowExW(h, None, 'WRY_WEBVIEW', None):
        sys.exit('refusing: the window has no WRY_WEBVIEW child, so it is not a Tauri webview window')

    visible = bool(u32.IsWindowVisible(h))
    check('window visible', visible, 'shown' if visible else
          'still hidden: with "visible": false the page must call getCurrentWindow().show() and the '
          'capability must grant core:window:allow-show')
    if not visible:
        sys.exit(1)
    if u32.IsIconic(h):
        sys.exit('the window is minimized; restore it and rerun')

    kind = dwm_int(h, 38)  # DWMWA_SYSTEMBACKDROP_TYPE
    check('backdrop is Mica', kind in (2, 4), f'DWMWA_SYSTEMBACKDROP_TYPE = {kind} ({BACKDROP.get(kind, "?")})')
    if not transparency_enabled():
        print('note  Transparency effects are off in Settings > Personalization > Colors: Windows draws '
              'the solid fallback instead of Mica, so the checks below only see the fallback color.')
    custom = bool(u32.FindWindowExW(h, None, 'TAURI_TITLEBAR_TOP_RESIZE', None)) or client(h)[1] <= frame(h)[1] + 1

    # Our own windows: a solid backdrop right behind the app, and a 1x1 window that takes focus.
    root = tk.Tk()
    root.overrideredirect(True)
    left, top, right, bottom = window_rect(h)
    root.geometry(f'{right - left}x{bottom - top}+{left}+{top}')
    root.configure(bg='#ff00ff')
    sink = tk.Toplevel(root)
    sink.overrideredirect(True)
    sink.geometry('1x1+0+0')
    root.update()
    back, sink_h = int(root.wm_frame(), 16), int(sink.wm_frame(), 16)
    try:
        u32.SetWindowPos(back, HWND_TOPMOST, 0, 0, 0, 0, 0x3 | 0x10)
        u32.SetWindowPos(h, HWND_TOPMOST, 0, 0, 0, 0, 0x3 | 0x10)
        activate(h)
        time.sleep(1.0)
        root.update()
        box = frame(h)
        if not keep_below(h, back) or u32.GetForegroundWindow() != h:
            sys.exit('could not bring the window to the front; click it once and rerun')

        active = grab(box)
        root.configure(bg='#00ff00')
        root.update()
        time.sleep(0.5)
        keep_below(h, back)
        share = see_through(active, grab(box))
        check('not see-through', share <= 0.001,
              f'{share:.2%} of the window follows the color behind it' + (
                  '' if share <= 0.001 else ': transparent window without a backdrop (effect missing, '
                  'cleared, unsupported, or Acrylic)'))

        run_active, cols = bare_backdrop_run(h, active, box, custom)
        activate(sink_h)
        time.sleep(1.2)
        root.update()
        keep_below(h, back)
        inactive = grab(box)
        run_inactive, _ = bare_backdrop_run(h, inactive, box, custom)
        moved = changed_share(active, inactive, box, h)
        ok = min(run_active, run_inactive) >= 12 or moved >= 0.2
        where = 'caption-button band' if custom else 'native caption'
        check('page shows the backdrop', ok,
              f'bare Mica along the top edge matches the {where} over {run_active}/{cols} samples active, '
              f'{run_inactive}/{cols} inactive; {moved:.0%} of the page follows the backdrop into the '
              'inactive state' + ('' if ok else ': something opaque covers the page (transparent: false, '
                                   'backgroundColor, or an html/body/#app background)'))

        activate(h)
        time.sleep(0.5)
        before = dwm_int(h, 20)  # DWMWA_USE_IMMERSIVE_DARK_MODE: the Mica tint
        u32.SendMessageTimeoutW(h, 0x1A, 0, 0, 0x2, 2000, None)  # WM_SETTINGCHANGE, to this window only
        time.sleep(0.8)
        after = dwm_int(h, 20)
        check('tint survives WM_SETTINGCHANGE', before == after,
              f'dark mode {before} -> {after}' + ('' if before == after else
                                                  ': "micaDark"/"micaLight" is reset by Tauri on every '
                                                  'settings broadcast; use "mica" plus the window "theme"'))
        print(f'info  tint: {"dark" if after else "light"}, title bar: {"custom" if custom else "native"}')
    finally:
        u32.SetWindowPos(h, HWND_NOTOPMOST, 0, 0, 0, 0, 0x3 | 0x10)
        root.destroy()
        activate(h)
    print('\nALL PASS' if not failures else f'\n{len(failures)} FAILED: {failures}')
    sys.exit(1 if failures else 0)


if __name__ == '__main__':
    main()
