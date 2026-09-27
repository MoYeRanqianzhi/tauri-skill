---
name: macos-titlebar-unverified
description: Recall before touching or relying on the macOS section of the tauri-custom-titlebar skill, or when a Mac becomes available for testing.
metadata:
  type: project
  scope: .claude/skills/tauri-custom-titlebar/references/macos-linux.md § macOS; Tauri 2.12
  status: active
  last_verified: 2026-09-27
---

The macOS guidance in the tauri-custom-titlebar skill has **not been run on a Mac**. Everything in it comes from Tauri 2.12 source and docs:
- the `titleBarStyle: "Overlay"`, `hiddenTitle` and `trafficLightPosition` config;
- the left padding for the traffic lights;
- `data-tauri-drag-region` versus `enableDragRegion`;
- the listed upstream issues.

The skill says so explicitly. A collaborator with a Mac is expected to finish it.

**Why:** the user decided on 2026-09-27 to verify Linux on a remote X11 host now, and to record macOS as unfinished for a later collaborator instead of shipping it as if verified. The previous skill failed precisely because it presented unverified platform claims as working.

**How to apply:** when a Mac is available:
1. Build `poc/titlebar-poc` on it. It needs `tauri.macos.conf.json` with the full window object, since arrays are replaced (see [[skill-assets-verified-by-poc]]), plus `"titleBarStyle": "Overlay"`, `"hiddenTitle": true` and `trafficLightPosition`.
2. Verify and record measured values for:
   - the traffic lights sit over the page and do not overlap the brand;
   - the padding needed on the left;
   - the bar height that lines up with the traffic lights;
   - drag with `data-tauri-drag-region` and with `enableDragRegion`, including double-click zoom and whether dragging an unfocused window works (tauri#9503);
   - whether setting the title resets `trafficLightPosition` (tauri#13044).
3. Screenshot light and dark themes.
4. Update the skill's macOS section with the verified results, change "Not verified" in SKILL.md, set this memory to `superseded`, and remove the TODO item.

Until then, keep telling users that macOS is untested.

**Evidence:** user instruction in-session, 2026-09-27: "macOS 写入记忆，说明未完成验证，后续会有协作者继续完成" ("write macOS into memory, note that verification is unfinished, and a collaborator will continue it later"). No macOS machine was available.

**Recheck when:** someone runs the POC on macOS, or Tauri changes its macOS title bar options.

Related: [[skill-authoring-conventions]].
