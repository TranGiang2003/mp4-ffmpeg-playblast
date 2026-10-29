"""Copy a local video as a file attachment using Maya's existing Qt runtime."""
from pathlib import Path
import os
import struct
import time


def qt_types():
    try:
        from PySide6.QtCore import QMimeData, QUrl, QThread
        from PySide6.QtGui import QGuiApplication
    except ImportError:
        from PySide2.QtCore import QMimeData, QUrl, QThread
        from PySide2.QtGui import QGuiApplication
    return QMimeData, QUrl, QThread, QGuiApplication


def file_payload(path):
    """Qt publishes local file URLs as native Windows file-drop clipboard data."""
    path = Path(path).resolve(strict=True)
    if not path.is_file():
        raise ValueError('Clipboard attachment must be an existing video file.')
    QMimeData, QUrl, _, _ = qt_types()
    payload = QMimeData()
    payload.setUrls([QUrl.fromLocalFile(str(path))])
    return payload


def copy_video(path):
    if os.name == 'nt':
        return copy_windows_file(path)
    return copy_qt_file(path)


def copy_qt_file(path):
    """Must run on Maya's main thread; transfers payload ownership to Qt."""
    _, _, QThread, QGuiApplication = qt_types()
    app = QGuiApplication.instance()
    if app is None or QThread.currentThread() != app.thread():
        raise RuntimeError('Video clipboard copying requires Maya\'s main UI thread.')
    payload = file_payload(path)
    expected = payload.urls()[0]
    clipboard = app.clipboard()
    clipboard.setMimeData(payload)
    # File contents are never read: clipboard data is only the local file URL.
    actual = clipboard.mimeData()
    if actual is None or expected not in actual.urls():
        raise RuntimeError('Windows did not accept the video attachment on the clipboard.')


def drop_payload(path):
    path = Path(path).resolve(strict=True)
    if not path.is_file():
        raise ValueError('Clipboard attachment must be an existing video file.')
    # DROPFILES: byte offset, POINT(x,y), fNC, fWide. Unicode double-null list.
    return struct.pack('<IiiII', 20, 0, 0, 0, 1) + (str(path) + '\0\0').encode('utf-16-le')


def copy_windows_file(path):
    """Publish fully rendered CF_HDROP; no Qt delayed clipboard ownership."""
    import ctypes as c
    from ctypes import wintypes as w
    data = drop_payload(path)
    user = c.WinDLL('user32', use_last_error=True)
    kernel = c.WinDLL('kernel32', use_last_error=True)
    user.CreateWindowExW.argtypes = [w.DWORD, w.LPCWSTR, w.LPCWSTR, w.DWORD,
                                   c.c_int, c.c_int, c.c_int, c.c_int,
                                   w.HWND, w.HMENU, w.HINSTANCE, c.c_void_p]
    user.CreateWindowExW.restype = w.HWND
    user.DestroyWindow.argtypes = [w.HWND]
    user.OpenClipboard.argtypes = [w.HWND]
    user.SetClipboardData.argtypes = [w.UINT, w.HANDLE]
    user.SetClipboardData.restype = w.HANDLE
    user.RegisterClipboardFormatW.argtypes = [w.LPCWSTR]
    user.RegisterClipboardFormatW.restype = w.UINT
    kernel.GlobalAlloc.argtypes = [w.UINT, c.c_size_t]
    kernel.GlobalAlloc.restype = w.HGLOBAL
    kernel.GlobalLock.argtypes = [w.HGLOBAL]
    kernel.GlobalLock.restype = c.c_void_p
    kernel.GlobalUnlock.argtypes = [w.HGLOBAL]
    kernel.GlobalFree.argtypes = [w.HGLOBAL]

    def publish(fmt, content):
        handle = kernel.GlobalAlloc(0x0002, len(content))  # GMEM_MOVEABLE
        if not handle:
            raise c.WinError(c.get_last_error())
        try:
            pointer = kernel.GlobalLock(handle)
            if not pointer:
                raise c.WinError(c.get_last_error())
            try:
                c.memmove(pointer, content, len(content))
            finally:
                kernel.GlobalUnlock(handle)
            if not user.SetClipboardData(fmt, handle):
                raise c.WinError(c.get_last_error())
            handle = None  # Windows owns the allocation now.
        finally:
            if handle:
                kernel.GlobalFree(handle)

    # A real hidden owner window avoids OpenClipboard(NULL)/EmptyClipboard issues.
    owner = user.CreateWindowExW(0, 'STATIC', 'Maya FFmpeg Clipboard', 0,
                                 0, 0, 0, 0, None, None, None, None)
    if not owner:
        raise c.WinError(c.get_last_error())
    opened = False
    try:
        for attempt in range(5):
            if user.OpenClipboard(owner):
                opened = True
                break
            if attempt < 4:
                time.sleep(0.01)
        if not opened:
            raise RuntimeError('Clipboard is busy. The saved MP4 is still available.')
        if not user.EmptyClipboard():
            raise c.WinError(c.get_last_error())
        publish(15, data)  # CF_HDROP, same file-list format used by Explorer.
        effect = user.RegisterClipboardFormatW('Preferred DropEffect')
        if effect:
            publish(effect, struct.pack('<I', 1))  # DROPEFFECT_COPY
    finally:
        if opened:
            user.CloseClipboard()
        user.DestroyWindow(owner)
