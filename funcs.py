import re

import unicodedata
from pytube import YouTube, Playlist
from win10toast import ToastNotifier

from YtDownloaderApp.data import data

toast = ToastNotifier()


def sanitize_filename(input_string, strict_cleaning=False):
    # Caractères à éviter sur les systèmes d'exploitation courants
    forbidden_chars = r'[<>:"/\\|?*\x00-\x1f]'
    # Remplacer les caractères interdits par un tiret bas
    sanitized = re.sub(forbidden_chars, '_', input_string)

    if strict_cleaning:
        # Décomposer les caractères unicode en caractères ASCII s'ils existent
        sanitized = unicodedata.normalize('NFKD', sanitized).encode('ASCII', 'ignore').decode()
        # Supprimer les espaces et autres caractères non alphanumériques
        sanitized = re.sub(r'[^a-zA-Z0-9_]', '', sanitized)

    # Tronquer le fichier pour s'assurer qu'il ne dépasse pas 255 caractères
    sanitized = sanitized[:255]
    # Supprimer les espaces ou les points en début et fin de chaîne
    sanitized = sanitized.strip(' .')
    # Gérer les cas de noms réservés sous Windows
    windows_reserved = ['CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8',
                        'COM9',
                        'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9']
    # Ajouter un tiret bas si le nom est réservé
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
    # Check if the URL contains a playlist ID
    if 'list=' in url:
        try:
            # Handle as a playlist
            playlist = Playlist(url)
            # Check if the playlist has any videos
            if not playlist.video_urls:
                return [url]

            # Return all video URLs from the playlist
            return [video for video in playlist.video_urls]
        except Exception:
            return [url]

    try:
        # Try to create a YouTube object
        yt = YouTube(url)
        # If creation is successful, return the video URL
        return [yt.watch_url]
    except Exception:
        # Handle generic exceptions
        return [url]
