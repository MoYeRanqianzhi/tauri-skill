"""Linux (X11) behaviour matrix for decorations:false + self-drawn controls. Run on the remote host.

Usage: DISPLAY=:99 python3 linux_matrix.py <app dir>   (starts and stops the app itself)
"""
import json, os, subprocess, sys, time

APP_DIR = sys.argv[1]
EXE = os.path.join(APP_DIR, 'src-tauri/target/debug/titlebar-poc')
LOG = os.path.join(APP_DIR, 'app.log')


def sh(*a):
    return subprocess.run(a, capture_output=True, text=True).stdout.strip()


def launch(env=None):
    subprocess.run(['pkill', '-x', 'titlebar-poc'])
    for _ in range(40):  # wait for the old instance's WebKit helper processes to go away
        if not sh('pgrep', '-f', 'webkit2gtk-4.1/WebKit'):
            break
        time.sleep(0.25)
    subprocess.Popen([EXE], stdout=open(LOG, 'w'), stderr=subprocess.STDOUT, env=dict(os.environ, NO_AT_BRIDGE='1', **(env or {})))  # no a11y bus on Xvfb: GTK waits ~25 s for it otherwise
    for _ in range(120):  # start-up on this Xvfb host varies from ~5 s to ~25 s
        time.sleep(0.5)
        for w in sh('xdotool', 'search', '--name', '^titlebar-poc$').split():
            if 'IsViewable' in sh('xwininfo', '-id', w) and geo(w)[2] > 100 and '[page] rects' in open(LOG).read():
                time.sleep(1)
                return w
    sys.exit('app window did not appear')


def geo(w):
    d = dict(l.split('=') for l in sh('xdotool', 'getwindowgeometry', '--shell', w).splitlines())
    return int(d['X']), int(d['Y']), int(d['WIDTH']), int(d['HEIGHT'])


def state(w):
    return sh('xprop', '-id', w, '_NET_WM_STATE')


def rects():
    line = [l for l in open(LOG).read().splitlines() if l.startswith('[page] rects ')][-1]
    return json.loads(line[len('[page] rects '):])


def at(w, r):  # centre of a page rect (CSS px == device px at scale 1) in screen coords
    x, y, _, _ = geo(w)
    return x + (r[0] + r[2]) // 2, y + (r[1] + r[3]) // 2


def move(x, y): sh('xdotool', 'mousemove', str(x), str(y))


def click(x, y, n=1):
    move(x, y); time.sleep(0.2)
    sh('xdotool', 'click', '--repeat', str(n), '--delay', '80', '1'); time.sleep(0.8)


def drag(x0, y0, x1, y1):
    move(x0, y0); time.sleep(0.3); sh('xdotool', 'mousedown', '1'); time.sleep(0.3)
    for i in range(1, 16):
        move(x0 + (x1 - x0) * i // 15, y0 + (y1 - y0) * i // 15); time.sleep(0.03)
    time.sleep(0.3); sh('xdotool', 'mouseup', '1'); time.sleep(0.8)


res = {}
w = launch({'POC_DRAG': os.environ.get('MODE', 'tauri')})
R = rects()
bar_x = R['search'][0] - 30  # empty bar area just left of the search box
bar_y = (R['titlebar'][1] + R['titlebar'][3]) // 2
x, y, W, H = geo(w)
res['window'] = (x, y, W, H, sh('xdotool', 'getwindowname', w))
g0 = geo(w); drag(x + bar_x, y + bar_y, x + bar_x + 120, y + bar_y + 60); g1 = geo(w)
res['drag bar (data-tauri-drag-region)'] = (g1[0] - g0[0], g1[1] - g0[1])
def maximized(): return 'MAXIMIZED' in state(w)
def downs(): return [l for l in open(LOG).read().splitlines() if 'mousedown target=titlebar' in l]
x, y, W, H = geo(w)
n0 = len(downs()); click(x + bar_x, y + bar_y, 2)
res['double-click bar -> maximized'] = (maximized(), geo(w), downs()[n0:])
if maximized(): click(*at(w, rects()['wc-max']))
click(*at(w, rects()['wc-max'])); m1 = maximized(); g_max = geo(w)
click(*at(w, rects()['wc-max'])); m2 = maximized()
res['max button toggles'] = (m1, g_max, not m2, geo(w))
x, y, W, H = geo(w)
g0 = geo(w); drag(x + W - 2, y + H // 2, x + W + 80, y + H // 2); g1 = geo(w)
res['right edge resize (inset 2px)'] = (g1[2] - g0[2], g1[3] - g0[3], 'maximized' if maximized() else 'restored')
x, y, W, H = geo(w)
g0 = geo(w); drag(x + W // 2, y + 2, x + W // 2, y - 50); g1 = geo(w)
res['top edge resize (inset 2px)'] = (g1[1] - g0[1], g1[3] - g0[3])
x, y, W, H = geo(w)
g0 = geo(w); drag(x + W - 2, y + H - 2, x + W + 40, y + H + 40); g1 = geo(w)
res['bottom-right corner resize'] = (g1[2] - g0[2], g1[3] - g0[3])
click(*at(w, rects()['wc-min']))
res['min button -> hidden'] = ('HIDDEN' in state(w), state(w))
sh('xdotool', 'windowactivate', w); time.sleep(1)
x, y, W, H = geo(w)
sh('xdotool', 'mousemove', str(x + bar_x), str(y + bar_y), 'click', '3'); time.sleep(1)
subprocess.run(['scrot', '-o', '/tmp/linux_rightclick.png'])
sh('xdotool', 'key', 'Escape')
subprocess.run(['scrot', '-o', '/tmp/linux_modeB.png'])
click(*at(w, rects()['wc-close'])); time.sleep(1)
res['close button -> exited'] = sh('pgrep', '-x', 'titlebar-poc') == ''

w = launch({'POC_DRAG': 'none'})
R = rects(); x, y, W, H = geo(w)
g0 = geo(w); drag(x + bar_x, y + bar_y, x + bar_x + 120, y + bar_y + 60); g1 = geo(w)
res['drag bar with app-region only'] = (g1[0] - g0[0], g1[1] - g0[1])
subprocess.run(['pkill', '-x', 'titlebar-poc'])
for k, v in res.items():
    print(f'{k}: {v}')
