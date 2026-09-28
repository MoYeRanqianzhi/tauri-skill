// mica-poc: proves the tauri-windows-mica skill on Windows 11.
//
// The "main" window is declared in tauri.conf.json with "create": false and built here from that
// same config, which is exactly what Tauri does for config windows (tauri/src/app.rs `setup`).
// POC_* env vars override single config fields per run, so one build covers the whole test matrix.
// The skill's recipe is this config plus POC_VISIBLE=0 POC_SHOW=direct ("visible": false, and the
// page calls show()); without any POC_* var the window starts visible, which shows the white flash.
#[cfg(windows)]
mod titlebar;

use serde_json::{json, Value};

/// Forwards page logs to stderr, which the harness redirects into poc/app.log.
#[tauri::command]
fn log(msg: String) {
    eprintln!("[page] {msg}");
}

/// Lets the page read POC_* switches (for example POC_TITLEBAR) without a rebuild.
#[tauri::command]
fn poc_env(name: String) -> Option<String> {
    std::env::var(name).ok()
}

/// Reads the DWM attributes that decide what the backdrop looks like, from inside the process
/// (ground truth for the harness): DWMWA_SYSTEMBACKDROP_TYPE (38) and
/// DWMWA_USE_IMMERSIVE_DARK_MODE (20).
#[cfg(windows)]
#[tauri::command]
fn dwm_attrs(window: tauri::WebviewWindow) -> Result<(i32, i32), String> {
    use windows::Win32::Foundation::HWND;
    use windows::Win32::Graphics::Dwm::{DwmGetWindowAttribute, DWMWINDOWATTRIBUTE};
    let hwnd = HWND(window.hwnd().map_err(|e| e.to_string())?.0);
    let read = |attr: i32| -> i32 {
        let mut v: i32 = -1;
        let _ = unsafe {
            DwmGetWindowAttribute(hwnd, DWMWINDOWATTRIBUTE(attr), &mut v as *mut i32 as *mut _, 4)
        };
        v
    };
    Ok((read(38), read(20)))
}

fn var(name: &str) -> Option<String> {
    std::env::var(name).ok()
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .setup(|app| {
            let mut cfg = app
                .config()
                .app
                .windows
                .iter()
                .find(|w| w.label == "main")
                .expect("main window in tauri.conf.json")
                .clone();
            // Each override goes through serde so it parses exactly like tauri.conf.json would.
            if let Some(v) = var("POC_TRANSPARENT") {
                cfg.transparent = v == "1";
            }
            if let Some(v) = var("POC_EFFECT") {
                cfg.window_effects = match v.as_str() {
                    "none" => None,
                    name => Some(serde_json::from_value(json!({ "effects": [name] }))?),
                };
            }
            if let Some(v) = var("POC_THEME") {
                cfg.theme = Some(serde_json::from_value(Value::String(v))?);
            }
            if let Some(v) = var("POC_DECORATIONS") {
                cfg.decorations = v == "1";
            }
            if let Some(v) = var("POC_BG") {
                cfg.background_color = Some(serde_json::from_value(Value::String(v))?);
            }
            if let Some(v) = var("POC_VISIBLE") {
                cfg.visible = v == "1";
            }
            if let Some(v) = var("POC_TITLE") {
                cfg.title = v;
            }
            eprintln!(
                "[rust] window transparent={} effects={:?} theme={:?} decorations={} background={:?} visible={}",
                cfg.transparent,
                cfg.window_effects.as_ref().map(|e| &e.effects),
                cfg.theme,
                cfg.decorations,
                cfg.background_color,
                cfg.visible
            );
            let window = tauri::WebviewWindowBuilder::from_config(app.handle(), &cfg)?.build()?;
            #[cfg(windows)]
            if var("POC_TITLEBAR").as_deref() == Some("1") {
                titlebar::install(&window)?;
            }
            let _ = window;
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            log,
            poc_env,
            #[cfg(windows)]
            dwm_attrs,
            #[cfg(windows)]
            titlebar::titlebar_insets,
            #[cfg(windows)]
            titlebar::set_caption_color
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
