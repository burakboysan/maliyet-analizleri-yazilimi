import ctypes


def _get_windows_work_area():
    """Return the usable desktop area on Windows, excluding the taskbar when possible."""
    try:
        rect = ctypes.wintypes.RECT()
        spi_get_work_area = 0x0030
        if ctypes.windll.user32.SystemParametersInfoW(spi_get_work_area, 0, ctypes.byref(rect), 0):
            return rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top
    except Exception:
        pass
    return None


def open_window_zoomed(window, min_width=1280, min_height=860):
    """Open CTk/Tk top-level windows maximized with a reliable Windows fallback."""
    try:
        window.update_idletasks()
    except Exception:
        pass

    work_area = None
    try:
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()
    except Exception:
        screen_width = max(min_width, 1280)
        screen_height = max(min_height, 860)
    else:
        work_area = _get_windows_work_area()
        if work_area is not None:
            _, _, screen_width, screen_height = work_area

    try:
        window.minsize(min_width, min_height)
    except Exception:
        pass

    try:
        if work_area is not None:
            left, top, width, height = work_area
            window.geometry(f"{width}x{height}+{left}+{top}")
        else:
            window.geometry(f"{screen_width}x{screen_height}+0+0")
    except Exception:
        pass

    def _maximize():
        try:
            window.state("zoomed")
            return
        except Exception:
            pass

        try:
            if work_area is not None:
                left, top, width, height = work_area
                window.geometry(f"{width}x{height}+{left}+{top}")
            else:
                window.geometry(f"{screen_width}x{screen_height}+0+0")
        except Exception:
            pass

    _maximize()

    try:
        window.after(10, _maximize)
        window.after(120, _maximize)
    except Exception:
        pass
