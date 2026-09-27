#[cfg(windows)]
mod titlebar;

#[tauri::command]
fn log(msg: String) {
    eprintln!("[page] {msg}");
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
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![log, #[cfg(windows)] titlebar::titlebar_insets, #[cfg(windows)] titlebar::set_caption_color])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
