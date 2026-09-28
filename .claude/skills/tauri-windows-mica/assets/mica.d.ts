// Type declarations for mica.js. Copy both files side by side; TypeScript projects then import
// './mica.js' under `strict` without `allowJs`.

/**
 * Sets data-mica="on" or "off" on `root` (default: <html>) and resolves to true where the
 * Windows 11 Mica backdrop is available. mica.css paints an opaque fallback for "off".
 */
export declare function detectMica(root?: HTMLElement): Promise<boolean>;
