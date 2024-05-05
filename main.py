import cgitb
import json
import logging
import os
import sys
import time

import funcs as f

import youtube_dl
from PyQt5.QtCore import pyqtSignal, QObject, QThreadPool, QRunnable, pyqtSlot, Qt
from PyQt5.QtGui import QIcon, QFont
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QPushButton, QLineEdit, QLabel, QFileDialog,
                             QHBoxLayout, QComboBox, QProgressBar, QScrollArea)
from pytube import YouTube
from pytube import request
from win10toast import ToastNotifier
from pytube.exceptions import RegexMatchError, VideoUnavailable
from urllib.error import URLError, HTTPError
import re

cgitb.enable(format='text')
toast = ToastNotifier()


def show_toast(title, subtitle):
    toast.show_toast(title, subtitle,
                     icon_path=icon_path,
                     duration=10,
                     threaded=True)


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
            yt = YouTube(self.url)
            if self.format == "mp3" or self.format == "flac" or self.format == "wav" or self.format == "m4a":
                stream = yt.streams.get_audio_only()
            else:
                stream = yt.streams.get_highest_resolution()
            filesize = stream.filesize  # get the video size
            title = f.sanitize_filename(yt.title, strict_cleaning=True) + "." + self.format
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
                show_toast("Download cancelled", "Video '" + yt.title + "' download was cancelled")
            else:
                show_toast("Download complete",
                           "Video '" + yt.title + "' was downloaded in " + self.format + " format")
        except RegexMatchError:
            show_toast("YouTube URL Parsing Error", "Failed to parse the provided YouTube URL due to incorrect format.")
        except VideoUnavailable:
            show_toast("YouTube Video Unavailable",
                       "The requested video cannot be accessed, possibly due to restrictions or deletion.")
        except (URLError, HTTPError) as e:
            show_toast("Network Connection Error",
                       "Failed to connect to YouTube due to a network issue or inaccessible server. "
                       "Error's reason : " + str(e.reason))
        except Exception as e:
            show_toast("Unexpected Application Error",
                       "An unspecified error occurred during operation, requiring further diagnosis.")
            print(e)
        except youtube_dl.utils.DownloadError as e:
            self.signals.download_error.emit("(pytube) " + str(e))
        except Exception as e:
            print(e)
            self.signals.download_error.emit(str(e))
        Worker.downloading_urls.remove(self.url)

    def download_youtube_video(url, path):
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


class DownloadWidget(QWidget):
    cancel_signal = pyqtSignal(str)

    def __init__(self, url, format, layout):
        super().__init__()
        self.url = url
        self.format = format
        self.layout = layout
        self.setStyleSheet("""
            QWidget {
                border: 2px solid #4e8df5;
                border-radius: 4px;
            }
        """)
        self.setContentsMargins(0, 0, 0, 0)
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout()

        video_name = YouTube(self.url).title

        # Nom de la vidéo
        self.video_label = QLabel(video_name)  # Ici, on pourrait extraire le titre avec youtube_dl si nécessaire
        self.video_label.setFixedWidth(int(self.width() * 0.5))  # 50% de la largeur du parent
        self.video_label.setFixedHeight(60)

        # Connecter le signal 'resized' du QWidget parent à une fonction pour ajuster la largeur du QLabel
        self.resized.connect(lambda: self.video_label.setFixedWidth(int(self.width() * 0.5)))
        self.video_label.setWordWrap(False)
        layout.addWidget(self.video_label)

        # Barre de progression
        self.progress = QProgressBar(self)
        self.progress.setValue(0)
        layout.addWidget(self.progress)

        # Bouton d'annulation
        self.cancel_button = QPushButton()
        self.cancel_button.setIcon(QIcon('close.png'))
        self.cancel_button.setFixedHeight(50)
        self.cancel_button.setFixedWidth(30)
        self.cancel_button.clicked.connect(self.cancel_download)
        layout.addWidget(self.cancel_button)
        self.setLayout(layout)

    def cancel_download(self):
        try:
            self.cancel_signal.emit(self.url)  # Envoie un signal pour annuler le téléchargement
            self.layout.removeWidget(self.progress)  # Supprime le widget de la mise en page
            self.layout.removeWidget(self.video_label)  # Supprime le widget de la mise en page
            self.layout.removeWidget(self.cancel_button)  # Supprime le widget de la mise en page
            self.layout.removeWidget(self)  # Supprime le widget de la mise en page
            self.deleteLater()  # Supprime le widget de la mémoire
        except Exception as e:
            print(e)

    def update_progress(self, percent):
        try:
            self.progress.setValue(percent)
        except Exception as e:
            print(e)

    # Personnalisation de la méthode 'resizeEvent' pour émettre un signal 'resized'
    def resizeEvent(self, event):
        super(DownloadWidget, self).resizeEvent(event)
        self.resized.emit()

    resized = pyqtSignal()


class HoverLineEdit(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        # Styles par défaut
        self.apply_normal_style()

    def apply_normal_style(self):
        self.setStyleSheet("""
            QLineEdit {
                background-color: #4e8df5;
                color: #ffffff;
                font-weight: bold;
                text-transform: uppercase;
                border: 0px;
            }
        """)

    def apply_hover_style(self):
        self.setStyleSheet("""
            QLineEdit {
                background-color: #ff6b6b;
                color: #ffffff;
                font-weight: bold;
                text-transform: uppercase;
                border: 0px;
            }
        """)


class HoverComboBox(QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setEditable(True)
        self.setLineEdit(HoverLineEdit())
        self.addItems(["MP4", "MOV", "AVI", "WMV", "FLV", "WEBM", "MP3", "WAV", "M4A", "FLAC"])

    def enterEvent(self, event):
        self.lineEdit().apply_hover_style()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.lineEdit().apply_normal_style()
        super().leaveEvent(event)


class App(QWidget):
    def __init__(self):
        super().__init__()

        self.load_settings()
        self.initUI()
        self.workers = []

    def initUI(self):
        self.setContentsMargins(40, 0, 40, 20)
        self.layout = QVBoxLayout(self)
        center_widget = QWidget()
        layout = QVBoxLayout()

        self.title_label = QLabel("YouTube Downloader")
        self.title_label.setObjectName("title")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setFont(QFont('Arial', 25))

        layout.addWidget(self.title_label)

        top_layout = QHBoxLayout()
        self.url_input = QLineEdit(self)
        self.url_input.setFixedWidth(int(center_widget.width() * 0.8))
        self.resized.connect(lambda: self.url_input.setFixedWidth(int(center_widget.width() * 0.8)))
        self.url_input.setPlaceholderText("Enter YouTube URL here")
        top_layout.addWidget(self.url_input)

        self.format_combo = HoverComboBox(self)
        self.format_combo.setFixedWidth(int(center_widget.width() * 0.15))
        self.resized.connect(lambda: self.format_combo.setFixedWidth(int(center_widget.width() * 0.15)))
        self.format_combo.setObjectName("button-primary")
        self.format_combo.setEditable(True)
        self.format_combo.setLineEdit(HoverLineEdit())
        self.format_combo.addItems(["MP4", "MOV", "AVI", "WMV", "FLV", "WEBM", "MP3", "WAV", "M4A", "FLAC"])
        line_edit = self.format_combo.lineEdit()
        line_edit.setAlignment(Qt.AlignCenter)
        line_edit.setReadOnly(True)
        top_layout.addWidget(self.format_combo, alignment=Qt.AlignRight)
        layout.addLayout(top_layout)

        mid_layout = QHBoxLayout()
        self.path_input = QLineEdit(self)
        self.path_input.setFixedWidth(int(center_widget.width() * 0.8))
        self.resized.connect(lambda: self.path_input.setFixedWidth(int(center_widget.width() * 0.8)))
        self.path_input.setPlaceholderText("Folder: C:/Users/.../DownloadsYT")
        if self.settings["save_path"]:
            self.path_input.setText(self.settings["save_path"])
        mid_layout.addWidget(self.path_input)

        self.path_input_button = QPushButton("Choose")
        self.path_input_button.setFixedWidth(int(center_widget.width() * 0.15))
        self.resized.connect(lambda: self.path_input_button.setFixedWidth(int(center_widget.width() * 0.15)))
        self.path_input_button.setObjectName("button-primary")
        self.path_input_button.clicked.connect(self.choose_save_path)
        mid_layout.addWidget(self.path_input_button, alignment=Qt.AlignRight)
        layout.addLayout(mid_layout)

        # Création d'une zone défilable pour les téléchargements
        self.scroll_area = QScrollArea(self)
        self.scroll_widget = QWidget()
        self.scroll_widget.setContentsMargins(0, 0, 0, 0)
        self.scroll_layout = QVBoxLayout(self.scroll_widget)
        self.scroll_layout.setSpacing(0)
        self.scroll_widget.setLayout(self.scroll_layout)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(self.scroll_widget)
        layout.addWidget(self.scroll_area)

        self.download_button = QPushButton("Download", self)
        self.download_button.setObjectName("button-primary")
        self.download_button.clicked.connect(self.start_download)
        layout.addWidget(self.download_button)

        self.threadpool = QThreadPool()
        print("Multithreading with maximum %d threads" % self.threadpool.maxThreadCount())

        center_widget.setLayout(layout)
        self.layout.addWidget(center_widget)
        self.setWindowTitle('YouTube Downloader')
        self.setWindowIcon(QIcon(icon_path))
        self.setMinimumSize(1000, 500)
        self.apply_theme()

    # Personnalisation de la méthode 'resizeEvent' pour émettre un signal 'resized'
    def resizeEvent(self, event):
        super(App, self).resizeEvent(event)
        self.resized.emit()

    resized = pyqtSignal()

    def choose_save_path(self):
        new_path = QFileDialog.getExistingDirectory(self, "Select Directory")
        if not new_path or new_path == '':
            return
        self.settings['save_path'] = new_path
        self.path_input.setText(new_path)
        self.save_settings()

    def cancel_download(self, url):
        for worker in self.workers:  # Parcourir tous les travailleurs pour trouver celui qui correspond à l'URL
            if worker.url == url:
                worker.cancel()

    def start_download(self):
        url = self.url_input.text()
        if url.strip() == "":
            show_toast("No URL", "No URL was provided. Please fill the text area.")
            return
        if not re.match(r'^(https?://)?(www\.)?(youtube\.com|youtu\.?be)/', url):
            show_toast("Invalid YouTube URL", "The URL you provided is not a YouTube URL.")
            return
        if not self.settings['save_path']:
            show_toast("No Save folder", "No save folder was provided. Please select one.")
            return
        if url in Worker.downloading_urls:
            show_toast("URL already being downloaded",
                       "The url you specified is already being downloaded. Please wait !")
            return

        format = self.format_combo.currentText().lower()
        download_widget = DownloadWidget(url, format, self.scroll_layout)
        self.scroll_layout.addWidget(download_widget)
        download_widget.cancel_signal.connect(self.cancel_download)
        self.download_video(download_widget)

    def download_video(self, download_widget):
        url = download_widget.url
        format = download_widget.format
        save_path = self.settings['save_path']
        worker = Worker(url, format, save_path)
        self.workers.append(worker)
        worker.signals.progress_updated.connect(download_widget.update_progress)
        worker.signals.download_complete.connect(lambda: download_widget.update_progress(100))
        worker.signals.download_error.connect(self.handle_download_error)
        self.threadpool.start(worker)

    def handle_download_error(self, error_message):
        show_toast("Error", f"Error during download: {error_message}")
        logging.error(f"Error during download: {error_message}")
        # Update UI or notify user about the error

    def load_settings(self):
        try:
            with open(setting_path, 'r') as f:
                self.settings = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.settings = {'save_path': ''}

    def save_settings(self):
        with open(setting_path, 'w') as f:
            json.dump(self.settings, f)

    def apply_theme(self):
        url_arrow_path = arrow_path.replace('\\', "/")
        self.setStyleSheet(f"""
            #title {{
                display: block;
                padding: 30px;
                font-weight: bold;
            }}
            
            QWidget {{
                font-family: 'Segoe UI', sans-serif;
                background-color: #2a2d34;
                color: #ffffff;
            }}
    
            QLineEdit:focus {{
                border-color: #2a2d34;
                box-shadow: 0 0 8px #ff6b6b;
            }}
            
            QComboBox, QLineEdit, QPushButton, QScrollArea {{
                border: 2px solid #4e8df5;
                border-radius: 4px;
                padding: 10px;
                margin: 10px 0;
                background-color: #2a2d34;
                color: #ffffff;
                transition: border-color 0.3s, box-shadow 0.3s;
            }}
    
            #button-primary {{
                background-color: #4e8df5;
                color: #ffffff;
                font-weight: bold;
                text-transform: uppercase;
            }}
    
            #button-primary:hover {{
                background-color: #ff6b6b;
                border-color: #2a2d34;
            }}
            
            QComboBox::down-arrow {{
                image: url({url_arrow_path});
                width: 20px;
                height: 20px;
                margin: auto;
            }}
            QComboBox::drop-down {{
                border:0px;
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 20px;
            }}
            QProgressBar {{
                border: solid grey;
                border-radius: 15px;
                color: black;
            }}
            QProgressBar::chunk {{
                background-color: #05B8CC;
                border-radius :15px;
            }}
        """)


def load_data():
    if getattr(sys, 'frozen', False):
        # Si l'application est exécutée en tant qu'exécutable OneFile.
        base_path = sys._MEIPASS
    else:
        # Si l'application est exécutée normalement (par exemple pendant le développement).
        base_path = os.path.dirname(__file__)
    setting_path = os.path.join(base_path, 'settings.json')
    icon_path = os.path.join(base_path, 'icon.ico')
    arrow_path = os.path.join(base_path, 'img.png')
    return setting_path, icon_path, arrow_path


if __name__ == '__main__':
    global setting_path, icon_path, arrow_path
    setting_path, icon_path, arrow_path = load_data()
    print("setting_path", setting_path)
    print("icon_path", icon_path)
    print("arrow_path", arrow_path)
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(icon_path))
    ex = App()
    ex.show()
    sys.exit(app.exec_())
