---
name: win32-ui-automation-safety
description: Recall before writing or running any script that moves the mouse, sends window messages, shows helper windows or takes screenshots on the user's desktop.
metadata:
  type: feedback
  scope: any UI automation on a contributor's real desktop (the poc/ harnesses, the skills' verify scripts)
  status: active
  last_verified: 2026-09-28
---

Only automate windows that your own test launched. Identify them by one of:
- exact title plus class (`Tauri Window`) plus a `WRY_WEBVIEW` child;
- the PID.

Never act on `GetForegroundWindow()`, and never on a process you did not start. The user's desktop can run other Tauri apps with the same window class; one was seen running minimized on 2026-09-28.

**Why:** on 2026-09-27 a probe launched `notepad.exe` and then treated the foreground window as "the notepad". The foreground window was actually the user's Chromium-based browser or Electron app. The probe maximized it and posted `WM_CLOSE` to it. Win11 Notepad is single-instance, so the launch had only opened a tab in the user's existing, unsaved Notepad. For native baselines, use a window created inside the test's own process (a Tk window, with the PID asserted).

**How to apply:**
- Before a run, warn the user about anything they will see:
  - real mouse movement;
  - helper windows. On 2026-09-28 the user stopped a Mica run because the harness's magenta and green backdrop windows looked as if the app itself kept changing color. Say up front that colored windows will flash behind the app.
- Keep runs short, and drop `HWND_TOPMOST` afterwards.
- Prefer checks that need no input. The Mica checks use only screenshots, a Tk backdrop window behind the app, and a 1×1 Tk window that takes focus for the inactive state.
- **Re-assert z-order before every screenshot.** Tk can re-raise its window while it processes events. Confirm with `WindowFromPoint` at the client center that the app is on top; a raised backdrop once produced an all-magenta shot.
- **Never inject keystrokes to get foreground.** An Alt tap reaches whatever app is in front, and leaves the target in system-menu mode, so mouse checks give false results. Instead call `AttachThreadInput` to the foreground thread, then `SetForegroundWindow` and `BringWindowToTop`.
- **Declare ctypes `argtypes` for HWND parameters,** or `HWND_TOPMOST` (-1) is passed as a 32-bit int and `SetWindowPos` silently fails on x64. Compare HWNDs as ints; a `wt.HWND` object never equals an int.
- **Check that every click point belongs to your window** (`GetAncestor(WindowFromPoint(pt), GA_ROOT)`) before clicking.
- Maximize with real clicks or the app's own API, not with cross-process `ShowWindow`.
- Never change global settings (theme, Transparency effects, wallpaper) from a script. Ask the user to toggle them.
- More traps: tauri-custom-titlebar `references/troubleshooting.md` and tauri-windows-mica `references/troubleshooting.md`, each under § Testing traps.

**Evidence:**
- The Notepad incident above, reported to the user in-session on 2026-09-27.
- Alt-menu-mode diagnosis: zero band messages were logged until Escape was sent, and afterwards the cursor was SIZENS within 20 ms.
- Blind-test review (2026-09-27) flagged that the titlebar verify script's Alt and Escape presses went to the foreground app.
- The `AttachThreadInput` rewrite passed with the user's browser in front, and sent no keys. `SetWindowPos` returned 0 before `argtypes` were declared.
- 2026-09-28: the all-magenta Mica screenshot disappeared once z-order was re-asserted before each grab, and the user stopped the rerun over the flashing backdrop windows.

**Recheck when:** the harness gains a sandboxed desktop (a VM or a separate session) where these precautions do not apply.

Related: [[skill-assets-verified-by-poc]].
