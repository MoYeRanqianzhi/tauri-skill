// Demo + probe page for mica-poc. It logs "[page] ..." lines to stderr through the `log` command,
// which the harness (poc/mica_*.py) reads from poc/app.log.
import './mica.css';
import './app.css';
import { invoke } from '@tauri-apps/api/core';
import { getCurrentWindow, Effect } from '@tauri-apps/api/window';
import { WebviewWindow } from '@tauri-apps/api/webviewWindow';
import { detectMica } from './mica.js';
import { watchTitlebarInsets } from './titlebar.js';

const $ = (id) => document.getElementById(id);
const appWindow = getCurrentWindow();
const tag = appWindow.label === 'main' ? '' : `(${appWindow.label}) `;
const log = (msg) => invoke('log', { msg: tag + msg });
addEventListener('unhandledrejection', (e) => log('unhandled rejection: ' + (e.reason?.message ?? e.reason)));

const BACKDROP = { 0: 'auto', 1: 'none', 2: 'mica', 3: 'acrylic', 4: 'mica alt' };
const scheme = () => (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');

async function refresh() {
  const ua = navigator.userAgentData ? await navigator.userAgentData.getHighEntropyValues(['platformVersion']) : null;
  const dwm = await invoke('dwm_attrs').catch(() => null);
  const s = {
    platformVersion: ua?.platformVersion ?? 'n/a',
    'data-mica': document.documentElement.dataset.mica ?? '(unset)',
    'prefers-color-scheme': scheme(),
    focus: document.hasFocus() ? 'active' : 'inactive',
    'DWM backdrop': dwm ? `${BACKDROP[dwm[0]] ?? dwm[0]} (${dwm[0]})` : 'n/a',
    'DWM dark mode': dwm ? String(dwm[1]) : 'n/a',
    'device pixel ratio': String(devicePixelRatio),
    origin: `${location.origin} (secure: ${isSecureContext})`,
  };
  $('status').innerHTML = Object.entries(s).map(([k, v]) => `<dt>${k}</dt><dd>${v}</dd>`).join('');
  if (dwm) {
    const current = { 2: 'mica', 4: 'tabbed' }[dwm[0]] ?? 'none';
    $('backdrop').querySelectorAll('button').forEach((b) => b.setAttribute('aria-pressed', b.dataset.value === current));
  }
  log('status ' + JSON.stringify(s));
  reportRects();
}

// Element rects in device px relative to the client area, for the harness's pixel sampling.
function reportRects() {
  const r = {};
  for (const id of ['titlebar', 'nav', 'content', 'card-theme', 'card-status', 'opaque']) {
    const b = $(id).getBoundingClientRect();
    r[id] = [b.left, b.top, b.right, b.bottom].map((v) => Math.round(v * devicePixelRatio));
  }
  log('rects ' + JSON.stringify(r));
}

// POC_FAKE_PLATFORM_VERSION=10.0.0 makes detectMica() see a Windows 10 value (fallback path test).
const fake = await invoke('poc_env', { name: 'POC_FAKE_PLATFORM_VERSION' });
if (fake) {
  const proto = Object.getPrototypeOf(navigator.userAgentData);
  const real = proto.getHighEntropyValues;
  Object.defineProperty(proto, 'getHighEntropyValues', {
    configurable: true,
    value: async function (hints) { return { ...(await real.call(this, hints)), platformVersion: fake }; },
  });
  log('faking platformVersion ' + fake);
}
const t0 = performance.now();
detectMica().then((on) => {
  const paint = performance.getEntriesByType('paint').map((p) => `${p.name}=${p.startTime.toFixed(1)}`).join(' ');
  log(`mica ${on ? 'on' : 'off'} at ${(performance.now() - t0).toFixed(1)} ms after script start; ${paint || 'no paint yet'}`);
  refresh();
});

if ((await invoke('poc_env', { name: 'POC_TITLEBAR' })) === '1') {
  $('titlebar').hidden = false;
  document.documentElement.dataset.titlebar = 'custom';
  watchTitlebarInsets();
}

function segmented(id, handler) {
  for (const b of $(id).querySelectorAll('button')) {
    b.onclick = async () => {
      $(id).querySelectorAll('button').forEach((x) => x.setAttribute('aria-pressed', x === b));
      try {
        await handler(b.dataset.value);
        log(`${id} ${b.dataset.value} ok`);
      } catch (e) {
        log(`${id} ${b.dataset.value} failed: ${e}`);
      }
      setTimeout(refresh, 400);
    };
  }
}
segmented('theme', (v) => appWindow.setTheme(v === 'system' ? null : v));
segmented('backdrop', (v) =>
  v === 'none' ? appWindow.clearEffects() : appWindow.setEffects({ effects: [v === 'tabbed' ? Effect.Tabbed : Effect.Mica] }),
);
$('opaque').onchange = (e) => {
  document.documentElement.classList.toggle('opaque-page', e.target.checked);
  log('opaque page ' + e.target.checked);
};
for (const id of ['nav-appearance', 'nav-diagnostics', 'nav-about']) {
  $(id).onclick = () => document.querySelectorAll('.nav-item').forEach((n) => n.toggleAttribute('aria-current', n.id === id));
}
matchMedia('(prefers-color-scheme: dark)').onchange = () => { log('prefers-color-scheme changed: ' + scheme()); refresh(); };
addEventListener('focus', () => refresh());
addEventListener('blur', () => refresh());
addEventListener('resize', () => setTimeout(reportRects, 300));

// A second window created from JS with the same options as the config window.
function openSecond() {
  const w = new WebviewWindow('second', {
    title: 'mica-poc second', width: 640, height: 420, transparent: true, windowEffects: { effects: [Effect.Mica] },
  });
  return new Promise((resolve, reject) => {
    w.once('tauri://created', resolve);
    w.once('tauri://error', (e) => reject(e.payload));
  });
}
const WINDOW = {
  maximize: () => appWindow.maximize(), unmaximize: () => appWindow.unmaximize(),
  minimize: () => appWindow.minimize(), unminimize: () => appWindow.unminimize(), second: openSecond,
};
if (appWindow.label === 'main' && (await invoke('poc_env', { name: 'POC_SECOND' })) === '1') {
  openSecond().then(() => log('second window created'), (e) => log('second window failed: ' + e));
}

// POC_ACTIONS="theme=dark,backdrop=none,opaque=toggle,window=maximize": the harness drives the page without any
// mouse or keyboard input. Action i runs 5 s + 4 s * i after start and logs "action <i> ...".
const actions = appWindow.label !== 'main' ? [] : (await invoke('poc_env', { name: 'POC_ACTIONS' }))?.split(',').filter(Boolean) ?? [];
actions.forEach((a, i) =>
  setTimeout(() => {
    const [name, value] = a.split('=');
    log(`action ${i} ${a}`);
    if (name === 'opaque') $('opaque').click();
    else if (name === 'caption') invoke('set_caption_color', { color: value === 'null' ? null : value }).then(() => log(`window caption ${value} ok`), (e) => log(`window caption ${value} failed: ${e}`));
    else if (name === 'window') WINDOW[value]().then(() => log(`window ${value} ok`), (e) => log(`window ${value} failed: ${e}`));
    else $(name).querySelector(`button[data-value="${value}"]`).click();
  }, 5000 + 4000 * i),
);

// POC_VISIBLE=0: the window starts hidden; show it after the first frame (the usual anti-flash
// pattern). POC_SHOW=direct calls show() right away instead, without waiting for a frame.
if (!(await appWindow.isVisible())) {
  log('hidden at startup; visibilityState=' + document.visibilityState);
  const show = (how) => appWindow.show().then(() => log('shown ' + how), (e) => log('show failed: ' + e));
  const how = await invoke('poc_env', { name: 'POC_SHOW' }); // "direct" | "never" | unset (after first frame)
  if (how === 'direct') show('directly');
  else if (how !== 'never') requestAnimationFrame(() => show('after first frame'));
}
