//! POC v2: native frame + DWM caption buttons, web content fills the caption strip.
//! - WRY_WEBVIEW container gets a window region with a hole over the caption buttons.
//! - A transparent overlay child provides the top resize edge without clipping web content.
use windows::core::w;
use windows::Win32::Foundation::*;
use windows::Win32::Graphics::Dwm::*;
use windows::Win32::Graphics::Gdi::*;
use windows::Win32::System::LibraryLoader::GetModuleHandleW;
use windows::Win32::UI::Controls::MARGINS;
use windows::Win32::UI::HiDpi::GetDpiForWindow;
use windows::Win32::UI::Shell::{DefSubclassProc, SetWindowSubclass};
use windows::Win32::UI::WindowsAndMessaging::*;

const SUBCLASS_ID: usize = 0x5449_544C;
const STRIP_CLASS: windows::core::PCWSTR = w!("TITLEBAR_TOP_RESIZE");

pub fn install(window: &tauri::WebviewWindow) -> Result<(), Box<dyn std::error::Error>> {
    let hwnd = HWND(window.hwnd()?.0);
    unsafe {
        let hinstance = GetModuleHandleW(None).map(|h| HINSTANCE(h.0)).ok();
        let class = WNDCLASSEXW {
            cbSize: std::mem::size_of::<WNDCLASSEXW>() as u32,
            lpfnWndProc: Some(strip_proc),
            hInstance: hinstance.unwrap_or_default(),
            lpszClassName: STRIP_CLASS,
            ..Default::default()
        };
        RegisterClassExW(&class);
        let strip = CreateWindowExW(
            WINDOW_EX_STYLE::default(),
            STRIP_CLASS,
            None,
            WS_CHILD | WS_VISIBLE | WS_CLIPSIBLINGS,
            0,
            0,
            0,
            0,
            Some(hwnd),
            None,
            hinstance,
            None,
        )?;
        let _ = SetWindowSubclass(hwnd, Some(subclass_proc), SUBCLASS_ID, strip.0 as usize);
        let _ = SetWindowPos(
            hwnd,
            None,
            0,
            0,
            0,
            0,
            SWP_FRAMECHANGED | SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE,
        );
        refresh(hwnd, strip);
    }
    Ok(())
}

#[derive(serde::Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Insets {
    top: f64,
    height: f64,
    right: f64,
}

#[tauri::command]
pub fn titlebar_insets(window: tauri::WebviewWindow) -> Insets {
    let hwnd = HWND(window.hwnd().unwrap().0);
    unsafe {
        let scale = GetDpiForWindow(hwnd) as f64 / 96.0;
        let b = caption_buttons_client(hwnd);
        let mut rc = RECT::default();
        let _ = GetClientRect(hwnd, &mut rc);
        let top = hidden_top(hwnd);
        Insets { top: top as f64 / scale, height: (b.bottom - top) as f64 / scale, right: (rc.right - b.left) as f64 / scale }
    }
}

/// `color` is "#rrggbb"; `None` restores the system caption color.
#[tauri::command]
pub fn set_caption_color(window: tauri::WebviewWindow, color: Option<String>) {
    let hwnd = HWND(window.hwnd().unwrap().0);
    let value: u32 = match color.as_deref().and_then(|c| u32::from_str_radix(c.trim_start_matches('#'), 16).ok()) {
        Some(rgb) => ((rgb & 0xFF) << 16) | (rgb & 0xFF00) | ((rgb >> 16) & 0xFF),
        None => 0xFFFF_FFFF, // DWMWA_COLOR_DEFAULT
    };
    unsafe {
        let _ = DwmSetWindowAttribute(hwnd, DWMWA_CAPTION_COLOR, &value as *const _ as *const _, 4);
    }
}

/// Native top resize band height: equals the invisible side border width (window rect vs visible frame).
unsafe fn resize_band(hwnd: HWND) -> i32 {
    let mut wr = RECT::default();
    let _ = GetWindowRect(hwnd, &mut wr);
    let mut vis = RECT::default();
    let _ = DwmGetWindowAttribute(
        hwnd,
        DWMWA_EXTENDED_FRAME_BOUNDS,
        &mut vis as *mut _ as *mut _,
        std::mem::size_of::<RECT>() as u32,
    );
    (vis.left - wr.left).max(1)
}

/// Rows of the client area pushed above the monitor work area while maximized.
unsafe fn hidden_top(hwnd: HWND) -> i32 {
    if !IsZoomed(hwnd).as_bool() {
        return 0;
    }
    let mut mi = MONITORINFO { cbSize: std::mem::size_of::<MONITORINFO>() as u32, ..Default::default() };
    let _ = GetMonitorInfoW(MonitorFromWindow(hwnd, MONITOR_DEFAULTTONEAREST), &mut mi);
    let mut origin = POINT::default();
    let _ = ClientToScreen(hwnd, &mut origin);
    (mi.rcWork.top - origin.y).max(0)
}

unsafe fn caption_buttons_client(hwnd: HWND) -> RECT {
    let mut b = RECT::default();
    let _ = DwmGetWindowAttribute(
        hwnd,
        DWMWA_CAPTION_BUTTON_BOUNDS,
        &mut b as *mut _ as *mut _,
        std::mem::size_of::<RECT>() as u32,
    );
    let mut wr = RECT::default();
    let _ = GetWindowRect(hwnd, &mut wr);
    let mut origin = POINT::default();
    let _ = ClientToScreen(hwnd, &mut origin);
    let (dx, dy) = (origin.x - wr.left, origin.y - wr.top);
    RECT { left: b.left - dx, top: b.top - dy, right: b.right - dx, bottom: b.bottom - dy }
}

unsafe fn refresh(hwnd: HWND, strip: HWND) {
    let b = caption_buttons_client(hwnd);
    let margins = MARGINS { cxLeftWidth: 0, cxRightWidth: 0, cyTopHeight: b.bottom.max(1), cyBottomHeight: 0 };
    let _ = DwmExtendFrameIntoClientArea(hwnd, &margins);

    let mut rc = RECT::default();
    let _ = GetClientRect(hwnd, &mut rc);
    if let Ok(container) = FindWindowExW(Some(hwnd), None, w!("WRY_WEBVIEW"), None) {
        let rgn = CreateRectRgn(0, 0, rc.right, rc.bottom);
        let hole = CreateRectRgn(b.left, b.top.min(0), b.right, b.bottom);
        CombineRgn(Some(rgn), Some(rgn), Some(hole), RGN_DIFF);
        let _ = DeleteObject(hole.into());
        SetWindowRgn(container, Some(rgn), true);
    } else {
        eprintln!("[titlebar] WRY_WEBVIEW not found");
    }
    let flags = if IsZoomed(hwnd).as_bool() { SWP_HIDEWINDOW } else { SWP_SHOWWINDOW };
    let _ = SetWindowPos(strip, Some(HWND_TOP), 0, 0, rc.right, resize_band(hwnd), flags | SWP_NOACTIVATE);
    eprintln!("[titlebar] buttons={:?} client={:?} band={} zoomed={} hidden_top={}", b, rc, resize_band(hwnd), IsZoomed(hwnd).as_bool(), hidden_top(hwnd));
}

unsafe extern "system" fn strip_proc(hwnd: HWND, msg: u32, wparam: WPARAM, lparam: LPARAM) -> LRESULT {
    match msg {
        WM_NCHITTEST => {
            // Band spans the full width, including above the caption buttons, like a native frame.
            let mut pt = POINT { x: (lparam.0 & 0xFFFF) as i16 as i32, y: ((lparam.0 >> 16) & 0xFFFF) as i16 as i32 };
            let _ = ScreenToClient(hwnd, &mut pt);
            let mut rc = RECT::default();
            let _ = GetClientRect(hwnd, &mut rc);
            let corner = rc.bottom;
            LRESULT(if pt.x < corner {
                HTTOPLEFT
            } else if pt.x >= rc.right - corner {
                HTTOPRIGHT
            } else {
                HTTOP
            } as isize)
        }
        WM_NCLBUTTONDOWN | WM_NCLBUTTONDBLCLK => {
            if let Ok(parent) = GetParent(hwnd) {
                let _ = PostMessageW(Some(parent), msg, wparam, lparam);
            }
            LRESULT(0)
        }
        WM_ERASEBKGND => LRESULT(1),
        _ => DefWindowProcW(hwnd, msg, wparam, lparam),
    }
}

unsafe extern "system" fn subclass_proc(
    hwnd: HWND,
    msg: u32,
    wparam: WPARAM,
    lparam: LPARAM,
    _id: usize,
    strip: usize,
) -> LRESULT {
    // DWM owns the caption buttons' hover/press state and only learns about mouse moves and leaves
    // through DwmDefWindowProc, so every message must go through it first.
    let mut r = LRESULT(0);
    if DwmDefWindowProc(hwnd, msg, wparam, lparam, &mut r).as_bool() {
        return r;
    }
    match msg {
        WM_NCCALCSIZE if wparam.0 != 0 => {
            let params = &mut *(lparam.0 as *mut NCCALCSIZE_PARAMS);
            let top = params.rgrc[0].top;
            let r = DefSubclassProc(hwnd, msg, wparam, lparam);
            params.rgrc[0].top = top;
            r
        }
        WM_NCHITTEST => {
            let r = DefSubclassProc(hwnd, msg, wparam, lparam);
            if r.0 != HTCLIENT as isize {
                return r;
            }
            LRESULT(HTCAPTION as isize)
        }
        WM_ERASEBKGND => {
            let mut rc = RECT::default();
            let _ = GetClientRect(hwnd, &mut rc);
            rc.bottom = caption_buttons_client(hwnd).bottom;
            FillRect(HDC(wparam.0 as *mut _), &rc, HBRUSH(GetStockObject(BLACK_BRUSH).0));
            LRESULT(1)
        }
        WM_SIZE | WM_DPICHANGED | WM_ACTIVATE => {
            let r = DefSubclassProc(hwnd, msg, wparam, lparam);
            refresh(hwnd, HWND(strip as *mut _));
            r
        }
        _ => DefSubclassProc(hwnd, msg, wparam, lparam),
    }
}
