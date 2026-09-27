import { invoke } from '@tauri-apps/api/core';
import { getCurrentWindow } from '@tauri-apps/api/window';
import { watchTitlebarInsets, setTitlebarColor, isWindows, enableDragRegion } from './titlebar.js';
const $ = (id) => document.getElementById(id);
addEventListener('unhandledrejection', (e) => invoke('log', { msg: 'unhandled rejection: ' + (e.reason?.message ?? e.reason) }));
addEventListener('mousedown', (e) => invoke('log', { msg: `mousedown target=${e.target.id || e.target.tagName} detail=${e.detail} button=${e.button}` }), true);
const log = (m) => { $('log').textContent = m + '\n' + $('log').textContent; invoke('log', { msg: m }); };

const THEMES = {
  light:   { scheme: 'light', tbBg: '#f3f3f3', tbFg: '#1b1b1f', tbMuted: '#8a8a92', bg: '#fafafa', card: '#ffffff', fg: '#1b1b1f', muted: '#6b6b73', accent: '#3b5bdb' },
  dark:    { scheme: 'dark',  tbBg: '#202024', tbFg: '#ececf1', tbMuted: '#7c7c85', bg: '#18181b', card: '#222226', fg: '#ececf1', muted: '#9a9aa3', accent: '#7c93ff' },
  indigo:  { scheme: 'dark',  tbBg: '#3140b8', tbFg: '#ffffff', tbMuted: '#aab3ec', bg: '#f6f7fc', card: '#ffffff', fg: '#1b1b1f', muted: '#6b6b73', accent: '#3140b8' },
  emerald: { scheme: 'dark',  tbBg: '#0f5e56', tbFg: '#f0fdfa', tbMuted: '#8fc7c0', bg: '#f5faf9', card: '#ffffff', fg: '#1b1b1f', muted: '#6b6b73', accent: '#0f766e' },
  sand:    { scheme: 'light', tbBg: '#efe6d8', tbFg: '#3b2f22', tbMuted: '#9c8b76', bg: '#faf7f2', card: '#ffffff', fg: '#3b2f22', muted: '#7d6f5e', accent: '#b4561d' },
};

async function applyTheme(name) {
  const t = THEMES[name];
  const s = document.documentElement.style;
  s.setProperty('--titlebar-bg', t.tbBg); s.setProperty('--titlebar-fg', t.tbFg); s.setProperty('--titlebar-muted', t.tbMuted);
  s.setProperty('--tb-hover', t.scheme === 'dark' ? 'rgb(255 255 255 / .1)' : 'rgb(0 0 0 / .06)');
  s.setProperty('--bg', t.bg); s.setProperty('--card', t.card); s.setProperty('--fg', t.fg);
  s.setProperty('--muted', t.muted); s.setProperty('--accent', t.accent);
  s.setProperty('--line', t.fg === '#ececf1' ? 'rgb(255 255 255 / .08)' : 'rgb(0 0 0 / .08)');
  document.querySelectorAll('.swatch').forEach((b) => b.setAttribute('aria-pressed', b.dataset.theme === name));
  await setTitlebarColor(t.tbBg);
  log('theme ' + name + ', page prefers dark: ' + matchMedia('(prefers-color-scheme: dark)').matches);
}
for (const [name, t] of Object.entries(THEMES)) {
  const b = document.createElement('button');
  b.className = 'swatch'; b.dataset.theme = name; b.id = 'theme-' + name;
  b.innerHTML = `<i style="background:${t.tbBg}"></i>${name[0].toUpperCase() + name.slice(1)}`;
  b.onclick = () => applyTheme(name);
  $('themes').append(b);
}

function reportRects() {
  const r = {};
  for (const id of ['titlebar', 'brand', 'menu-file', 'search', 'min40', 'wc-min', 'wc-max', 'wc-close', ...Object.keys(THEMES).map((n) => 'theme-' + n)]) {
    const b = $(id).getBoundingClientRect();
    r[id] = [b.left, b.top, b.right, b.bottom].map((v) => Math.round(v * devicePixelRatio));
  }
  invoke('log', { msg: 'rects ' + JSON.stringify(r) });
}
function showInsets() {
  const v = (n) => parseFloat(getComputedStyle(document.documentElement).getPropertyValue(n)).toFixed(2);
  invoke('log', { msg: `insets top=${v('--titlebar-top')} height=${v('--titlebar-height')} right=${v('--titlebar-right')} zoomed-dpr=${devicePixelRatio}` });
  $('insets').textContent = `top ${v('--titlebar-top')}px, height ${v('--titlebar-height')}px, right ${v('--titlebar-right')}px`;
  $('dpr').textContent = devicePixelRatio;
  reportRects();
}
watchTitlebarInsets();
addEventListener('resize', () => setTimeout(showInsets, 300));
setTimeout(showInsets, 300);
const mq = matchMedia('(prefers-color-scheme: dark)');
const showScheme = () => { $('scheme').textContent = mq.matches ? 'dark' : 'light'; };
mq.onchange = () => { showScheme(); log('page prefers-color-scheme changed: ' + (mq.matches ? 'dark' : 'light')); };
showScheme();
$('min40').onchange = (e) => document.documentElement.style.setProperty('--tb-min', e.target.checked ? '40px' : '0px');
addEventListener('focus', () => { document.body.classList.remove('inactive'); $('focus').textContent = 'active'; });
addEventListener('blur', () => { document.body.classList.add('inactive'); $('focus').textContent = 'inactive'; });
['menu-file', 'menu-edit', 'menu-view'].forEach((id) => $(id).onclick = () => log(id + ' clicked'));
$('search').oninput = (e) => log('search: ' + e.target.value);
applyTheme('light');

// Linux (or any platform) with decorations: false: draw our own controls and use Tauri's JS drag region.
const appWindow = getCurrentWindow();
if (!isWindows && !(await appWindow.isDecorated())) {
  $('wc').hidden = false;
  $('wc-min').onclick = () => appWindow.minimize();
  $('wc-max').onclick = () => appWindow.toggleMaximize();
  $('wc-close').onclick = () => appWindow.close();
  const dragMode = await invoke('poc_env', { name: 'POC_DRAG' }); // "tauri" (default) | "threshold" | "none"
  if (dragMode === 'threshold') enableDragRegion($('titlebar'), appWindow);
  else if (dragMode !== 'none') $('titlebar').setAttribute('data-tauri-drag-region', '');
  log('drag mode ' + (dragMode ?? 'tauri'));
  log('custom window controls enabled');
}

