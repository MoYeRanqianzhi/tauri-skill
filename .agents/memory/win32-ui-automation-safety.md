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
- If you use the Alt-tap trick to get foreground, send Escape right after. Otherwise the window stays in system-menu mode and every mouse-based check gives false results.
- Maximize with real clicks, not cross-process `ShowWindow`.
- More traps: `.claude/skills/tauri-custom-titlebar/references/troubleshooting.md` § Testing traps.

**Evidence:** the incident above, reported to the user in-session on 2026-09-27. Alt-menu-mode diagnosis: zero band messages were logged until Escape was sent, and afterwards the cursor was SIZENS within 20 ms.

**Recheck when:** the harness gains a sandboxed desktop (VM or separate session) where these precautions do not apply.

Related: [[skill-assets-verified-by-poc]].
