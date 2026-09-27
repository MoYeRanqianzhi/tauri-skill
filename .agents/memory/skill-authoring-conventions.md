---
name: skill-authoring-conventions
description: Recall before writing or restructuring any skill in this repo, or its demo/POC UI.
metadata:
  type: feedback
  scope: all skills under .claude/skills/ and their POC/demo apps in this repo
  status: active
  last_verified: 2026-09-27
---

Skills in this repo must be written in English only. They follow the standard skill layout: frontmatter, a lean SKILL.md, details in `references/`, and verified code in `assets/`. Every instruction must have been exercised in a real build, not assumed to work. The purpose of a skill is to stop the consuming agent from hitting known pitfalls, which saves development time and tokens.

Demo and POC UIs used to verify a skill must look modern and minimal. They must be tested across several color themes, and colors must be consistent across the whole title bar, including the native button area.

**Evidence:** user statements on 2026-09-27:
- the previous `tauri-native-chrome` skill "mixed Chinese", did not follow the format, and agents kept hitting pitfalls despite reading it;
- the first POC components were "too ugly" and the title bar colors did not match;
- "SKILL.md is too big; move content into references".

**Why:** the old skill described an approach (a WebView2 composition-hosting wry fork) that was never validated. Agents followed it and still failed. A skill is only worth its token cost if following it is sufficient.

**How to apply:**
- Keep SKILL.md to the decision, the minimal steps and the hard rules. Put symptom tables, measurements and rationale in references.
- Mark anything not run on real hardware as "not verified" in the skill itself.
- For UI verification, capture screenshots across themes and states (active, inactive, maximized) before claiming success.

**Recheck when:** the user states a different convention for skills, or a skill targets an audience that needs another language.

Related: [[skill-assets-verified-by-poc]], [[macos-titlebar-unverified]].
