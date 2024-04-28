from pytube import YouTube
import youtube_dl
from win10toast import ToastNotifier
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot, QRunnable


toast = ToastNotifier()

class WorkerSignals(QObject):
    progress_updated = pyqtSignal(int)
    download_complete = pyqtSignal()
    download_error = pyqtSignal(str)

class Worker(QRunnable):
    downloading_urls = []

    def __init__(self, url, format, save_path):
        super().__init__()
        self.url = url
        Worker.downloading_urls.append(url)
        self.format = format
        self.save_path = save_path
        self.is_cancelled = False
        self.signals = WorkerSignals()

    @pyqtSlot()
    def run(self):
        try:
            yt = YouTube(self.url, on_progress_callback=self.progress_hook)
            if self.format == "mp3" or self.format == "flac" or self.format == "wav" or self.format == "m4a":
                stream = yt.streams.get_audio_only()
            else:
                stream = yt.streams.get_highest_resolution()
            filesize = stream.filesize  # get the video size
            title = f.normalize_title(yt.title) + "." + self.format
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
            while toast.notification_active(): time.sleep(0.1)
            if self.is_cancelled:
                # Supprimer le fichier si le téléchargement est annulé
                os.remove(self.save_path + "\\" + yt.title + "." + self.format)
                toast.show_toast("Download cancelled", "Video '" + yt.title + "' download was cancelled",
                                 icon_path="icon.ico",
                                 duration=10,
                                 threaded=True)
            else:
                toast.show_toast("Download complete",
                                 "Video '" + yt.title + "' was downloaded in " + self.format + " format",
                                 icon_path=icon_path,
                                 duration=10,
                                 threaded=True)
        except youtube_dl.utils.DownloadError as e:
            self.signals.download_error.emit("(pytube) " + str(e))
        except Exception as e:
            print(e)
            self.signals.download_error.emit(str(e))
        Worker.downloading_urls.remove(self.url)

    def cancel(self):
        self.is_cancelled = True