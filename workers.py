import os
import re
import time
from urllib.error import URLError, HTTPError

from PyQt5.QtCore import QObject, pyqtSignal, QRunnable, pyqtSlot
from pytube import YouTube, request
from pytube.exceptions import RegexMatchError, VideoUnavailable

from YtDownloaderApp.file_formats import FileFormat, FileType
from YtDownloaderApp.funcs import sanitize_filename, notification_active, show_toast


workers = []
downloading_urls = []


def get_downloading_worker(url, format="any"):
    for worker in workers:  # Parcourir tous les travailleurs pour trouver celui qui correspond à l'URL
        if format.lower() == "any":
            has_format = True
        else:
            has_format = worker.format == format
        if worker.url == url and has_format:
            return worker


def is_downloading(url, format="any"):
    return get_downloading_worker(url, format) is not None


def cancel_download(url, format="any"):
    worker = get_downloading_worker(url, format)
    if not worker:
        return
    worker.cancel()


class WorkerSignals(QObject):
    progress_updated = pyqtSignal(int)
    download_complete = pyqtSignal()
    download_error = pyqtSignal(str, str)


class Worker(QRunnable):

    def __init__(self, url, format: FileFormat, save_path):
        super().__init__()
        self.url = url
        downloading_urls.append(url)
        self.format = format
        self.save_path = save_path
        self.is_cancelled = False
        self.signals = WorkerSignals()
        workers.append(self)

    @pyqtSlot()
    def run(self):
        error_title = None
        error_subtitle = None
        try:
            yt = YouTube(self.url)
            if self.format.file_type == FileType.Audio:
                stream = yt.streams.get_audio_only()
            else:
                stream = yt.streams.get_highest_resolution()
            filesize = stream.filesize  # get the video size
            title = sanitize_filename(yt.title, strict_cleaning=True) + "." + self.format.name
            with open(self.save_path + "\\" + title, 'wb') as out_file:
                stream = request.stream(stream.url)  # get an iterable stream
                downloaded = 0
                while True:
                    if self.is_cancelled:
                        break
                    chunk = next(stream, None)  # get next chunk of video
                    if chunk:
                        out_file.write(chunk)
                        downloaded += len(chunk)
                        percent = downloaded / filesize
                        self.signals.progress_updated.emit(int(percent * 100))
                    else:
                        break
            self.signals.download_complete.emit()
            while notification_active(): time.sleep(0.1)
            if self.is_cancelled:
                # Supprimer le fichier si le téléchargement est annulé
                os.remove(self.save_path + "\\" + yt.title + "." + self.format.name)
                show_toast("Download cancelled", "Video '" + yt.title + "' download was cancelled")
            else:
                show_toast("Download complete",
                           "Video '" + yt.title + "' was downloaded in " + self.format.name + " format")
        except RegexMatchError:
            error_title = "YouTube URL Parsing Error"
            error_subtitle = "Failed to parse the provided YouTube URL due to incorrect format."
        except VideoUnavailable:
            error_title = "YouTube Video Unavailable"
            error_subtitle = "The requested video cannot be accessed, possibly due to restrictions or deletion."
        except (URLError, HTTPError) as e:
            error_title = "Network Connection Error"
            error_subtitle = ("Failed to connect to YouTube due to a network issue or inaccessible server. "
                              "Error's reason : " + str(e.reason))
        except Exception as e:
            error_title = "Unexpected Application Error"
            error_subtitle = "An unspecified error occurred during operation, requiring further diagnosis."
            print(e)
        if error_title:
            self.signals.download_error.emit(error_title, error_subtitle)
            show_toast(error_title, error_subtitle)
        workers.remove(self)

    def download_youtube_video(self, url, path):
        """Download a video from YouTube while handling common exceptions."""

        # Check if the URL is a valid YouTube URL
        if not re.match(r'^(https?://)?(www\.)?(youtube\.com|youtu\.?be)/', url):
            return "Error: Invalid YouTube URL."

        try:
            # Create YouTube object
            yt = YouTube(url)

            # Select the first stream; if you need a specific stream, filter by mime_type, resolution, etc.
            stream = yt.streams.first()

            # Download the video
            stream.download(output_path=path)

            return "Download successful!"
        except RegexMatchError:
            return "Error: Failed to parse YouTube URL."
        except VideoUnavailable:
            return "Error: Video is unavailable."
        except (URLError, HTTPError) as e:
            return f"Network Error: {e.reason}"
        except Exception as e:
            # Catch-all for any other unforeseen errors
            return f"An unexpected error occurred: {str(e)}"

    def cancel(self):
        self.is_cancelled = True
