"""Runs the skill's scripts/verify_windows_mica.py against poc/mica-poc variants (positive and negative).

Usage: python mica_verify_matrix.py [variant ...]   (default: all)
Safety: same as the verify script (no mouse, no keys); it launches and kills only mica-poc.exe.
"""
import os
import subprocess
import sys
import time

import mica_probe as mp

VERIFY = os.path.join(mp.HERE, '..', '.claude', 'skills', 'tauri-windows-mica', 'scripts', 'verify_windows_mica.py')
VARIANTS = {  # name: (env, title to verify, log line to wait for, expected exit code)
    'recipe': ({}, 'mica-poc', None, 0),
    'dark': ({'POC_THEME': 'dark'}, 'mica-poc', None, 0),
    'tabbed': ({'POC_EFFECT': 'tabbed'}, 'mica-poc', None, 0),
    'titlebar': ({'POC_TITLEBAR': '1'}, 'mica-poc', None, 0),
    'titlebar-dark': ({'POC_TITLEBAR': '1', 'POC_THEME': 'dark'}, 'mica-poc', None, 0),
    'hidden-show': ({'POC_VISIBLE': '0', 'POC_SHOW': 'direct'}, 'mica-poc', '[page] shown', 0),
    'second': ({'POC_SECOND': '1'}, 'mica-poc second', '[page] (second) status', 0),
    'neg-not-transparent': ({'POC_TRANSPARENT': '0'}, 'mica-poc', None, 1),
    'neg-no-effect': ({'POC_EFFECT': 'none'}, 'mica-poc', None, 1),
    'neg-micadark': ({'POC_EFFECT': 'micaDark'}, 'mica-poc', None, 1),
    'neg-background-color': ({'POC_BG': '#ffffff'}, 'mica-poc', None, 1),
    'neg-opaque-page': ({'POC_ACTIONS': 'opaque=toggle'}, 'mica-poc', '[page] opaque page true', 1),
    'neg-never-shown': ({'POC_VISIBLE': '0', 'POC_SHOW': 'never'}, 'mica-poc', '[page] hidden at startup', 1),
}


def main():
    names = sys.argv[1:] or list(VARIANTS)
    summary = []
    for name in names:
        env_extra, title, wait_for, expected = VARIANTS[name]
        subprocess.run(['taskkill', '/IM', 'mica-poc.exe', '/F'], capture_output=True)
        time.sleep(0.5)
        env = dict(os.environ, NO_AT_BRIDGE='1', **env_extra)
        proc = subprocess.Popen([mp.EXE], stdout=open(mp.LOG, 'w', encoding='utf-8'), stderr=subprocess.STDOUT, env=env)
        try:
            ready = mp.wait_log(wait_for or '[page] status ', 30)
            time.sleep(1.0)
            print(f'=== {name} {env_extra or "(recipe)"}' + ('' if ready else ' (page never reported ready)'))
            res = subprocess.run([sys.executable, VERIFY, title], capture_output=True, text=True, encoding='utf-8')
            print(res.stdout.rstrip() or res.stderr.rstrip())
            ok = res.returncode == expected
            summary.append(f"{'OK ' if ok else 'BAD'} {name}: exit {res.returncode}, expected {expected}")
        finally:
            proc.kill()
    print('\n'.join(['', 'summary:'] + summary))


if __name__ == '__main__':
    main()
