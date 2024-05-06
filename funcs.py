import re

import unicodedata
from pytube import YouTube, Playlist
from win10toast import ToastNotifier

from YtDownloaderApp.data import data

toast = ToastNotifier()


def sanitize_filename(input_string, strict_cleaning=False):
    forbidden_chars = r'[<>:"/\\|?*\x00-\x1f]'
    sanitized = re.sub(forbidden_chars, '_', input_string)

    if strict_cleaning:
        sanitized = unicodedata.normalize('NFKD', sanitized).encode('ASCII', 'ignore').decode()
        sanitized = re.sub(r'[^a-zA-Z0-9_]', '', sanitized)

    sanitized = sanitized[:255]
    sanitized = sanitized.strip(' .')
    windows_reserved = ['CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8',
                        'COM9',
                        'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9']
    if sanitized.upper() in windows_reserved:
        sanitized = '_' + sanitized

    return sanitized


def show_toast(title, subtitle):
    toast.show_toast(title, subtitle,
                     icon_path=data.icon_path,
                     duration=10,
                     threaded=True)


def notification_active():
    return toast.notification_active()


def get_youtube_content(url):
    if 'list=' in url:
        try:
            playlist = Playlist(url)
            if not playlist.video_urls:
                return [url]

            return [video for video in playlist.video_urls]
        except Exception:
            return [url]

    try:
        yt = YouTube(url)
        return [yt.watch_url]
    except Exception:
        return [url]
