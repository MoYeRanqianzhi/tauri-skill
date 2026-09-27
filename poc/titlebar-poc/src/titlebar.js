// Frontend half of the Windows custom title bar (pairs with windows_titlebar.rs).
// Framework-agnostic ES module; works as-is in TS projects (`allowJs`) or rename to .ts.
//
// CSS variables written on <html>:
//   --titlebar-top     rows hidden above the screen while maximized (0 when restored)
//   --titlebar-height  visible caption-button height = recommended title bar row height
//   --titlebar-right   width reserved for the native caption buttons
import { invoke } from '@tauri-apps/api/core';

export const isWindows = navigator.userAgent.includes('Windows');

/**
 * Keeps the CSS variables in sync. Geometry changes on maximize/restore, DPI change and resize, and
 * every one of those fires a window `resize` event in the page. Returns a disposer.
 */
export function watchTitlebarInsets(root = document.documentElement) {
  if (!isWindows) return () => {};
  let seq = 0;
  const apply = async () => {
    const mine = ++seq;
    const insets = await invoke('titlebar_insets');
    if (mine !== seq) return; // a newer resize already answered; drop stale geometry
    root.style.setProperty('--titlebar-top', `${insets.top}px`);
    root.style.setProperty('--titlebar-height', `${insets.height}px`);
    root.style.setProperty('--titlebar-right', `${insets.right}px`);
  };
  apply();
  addEventListener('resize', apply);
  return () => removeEventListener('resize', apply);
}

/**
 * Paints the native caption behind the buttons with the title bar color. DWM picks contrasting
 * glyph and hover colors automatically; do not call `setTheme()` for that (it also flips the page's
 * `prefers-color-scheme` on Windows).
 * @param {string | null} background "#rrggbb" of the title bar, or null for the system color
 */
export async function setTitlebarColor(background) {
  if (!isWindows) return;
  await invoke('set_caption_color', { color: background });
}
