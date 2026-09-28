// mica.js: Mica support detection for Tauri pages (tauri-windows-mica skill). No imports.
//
// Tauri drops the error when the Mica effect is unsupported, so on Windows 10 the
// "transparent": true window shows the desktop through every transparent pixel of the page.
// detectMica() sets data-mica="on" or "off" on <html>; mica.css paints an opaque fallback for "off".
//
// Windows 11 is recognised through User-Agent Client Hints: platformVersion >= 13 (the
// UniversalApiContract version). navigator.userAgent still says "Windows NT 10.0" on Windows 11.
// WebKit webviews (macOS, Linux) have no navigator.userAgentData, so they count as "off".
//
// Call it once at startup. Until it resolves the page stays transparent, so Windows 11 never
// flashes the fallback color.
export async function detectMica(root = document.documentElement) {
  const uad = navigator.userAgentData;
  let on = false;
  if (uad?.platform === 'Windows') {
    const { platformVersion } = await uad.getHighEntropyValues(['platformVersion']);
    on = parseInt(platformVersion, 10) >= 13;
  }
  root.dataset.mica = on ? 'on' : 'off';
  return on;
}
