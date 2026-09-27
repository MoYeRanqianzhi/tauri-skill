---
name: win32-ui-automation-safety
description: Recall before writing or running any script that moves the mouse, sends window messages or takes screenshots on the user's desktop.
metadata:
  type: feedback
  scope: any UI automation on a contributor's real desktop (Windows harness in poc/, the skill's verify script)
  status: active
  last_verified: 2026-09-27
---

Only automate windows that your own test launched. Identify them by exact title plus class (`Tauri Window`) plus a `WRY_WEBVIEW` child, or by PID. Never act on `GetForegroundWindow()`, and never on a process you did not start.

**Why:** on 2026-09-27, a probe launched `notepad.exe` and then used the foreground window as "the notepad". The foreground window was actually the user's Chromium-based browser or Electron app. The probe maximized it and posted `WM_CLOSE` to it. Win11 Notepad is single-instance, so the launch only opened a tab in the user's existing, unsaved Notepad. For native baselines, use a window created inside the test's own process (a Tk window, with the PID asserted).

**How to apply:**
- Warn the user before any run that moves the real mouse. Keep runs short. Drop `HWND_TOPMOST` afterwards.
- **Never inject keystrokes to get foreground.** An Alt tap reaches whatever app is in front, and leaves the target in system-menu mode, so mouse checks give false results. Instead, call `AttachThreadInput` to the foreground thread, then `SetForegroundWindow` and `BringWindowToTop` (as in `scripts/verify_windows_titlebar.py` and `poc/probe.py`).
- **Declare ctypes `argtypes` for HWND parameters.** Otherwise `HWND_TOPMOST` (-1) is passed as a 32-bit int and `SetWindowPos` silently fails on x64.
- **Check that every click point belongs to your window** (`GetAncestor(WindowFromPoint(pt), GA_ROOT)`) before clicking.
- Maximize with real clicks, not cross-process `ShowWindow`.
- More traps: `.claude/skills/tauri-custom-titlebar/references/troubleshooting.md` § Testing traps.

**Evidence:**
- The incident above, reported to the user in-session on 2026-09-27.
- Alt-menu-mode diagnosis: zero band messages were logged until Escape was sent, and afterwards the cursor was SIZENS within 20 ms.
- Blind-test review (2026-09-27) flagged that the verify script's Alt and Escape presses went to the foreground app.
- The `AttachThreadInput` rewrite passed with the user's browser in front, with no keys sent. `SetWindowPos` returned 0 before `argtypes` were declared.

**Recheck when:** the harness gains a sandboxed desktop (VM or separate session) where these precautions do not apply.

Related: [[skill-assets-verified-by-poc]].
