#[cfg(windows)]
mod titlebar;

#[tauri::command]
fn log(msg: String) {
    eprintln!("[page] {msg}");
}

#[tauri::command]
fn poc_env(name: String) -> Option<String> {
    std::env::var(name).ok()
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .setup(|app| {
            #[cfg(windows)]
            {
                use tauri::Manager;
                let w = app.get_webview_window("main").unwrap();
                if std::env::var("POC_NO_TITLEBAR").is_err() {
                    titlebar::install(&w)?;
                }
            }
            let _ = app; // only used on Windows
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![log, poc_env, #[cfg(windows)] titlebar::titlebar_insets, #[cfg(windows)] titlebar::set_caption_color])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
