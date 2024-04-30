import cgitb
import json
import logging
import os
import sys
import time
import funcs as f

import youtube_dl
from PyQt5.QtCore import pyqtSignal, QObject, QThreadPool, QRunnable, pyqtSlot
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QPushButton, QLineEdit, QLabel, QFileDialog,
                             QHBoxLayout, QComboBox, QProgressBar, QScrollArea)
from pytube import YouTube
from pytube import request
from win10toast import ToastNotifier

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
        except youtube_dl.utils.DownloadError as e:
            self.signals.download_error.emit("(pytube) " + str(e))
        except Exception as e:
            print(e)
            self.signals.download_error.emit(str(e))
        Worker.downloading_urls.remove(self.url)

    def cancel(self):
        self.is_cancelled = True


class DownloadWidget(QWidget):
    cancel_signal = pyqtSignal(str)

    def __init__(self, url, format, layout):
        super().__init__()
        self.url = url
        self.format = format
        self.layout = layout
        self.setObjectName("dlwidget")
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
        self.cancel_button = QPushButton('X', self)
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


class App(QWidget):
    def __init__(self):
        super().__init__()

        self.load_settings()
        self.initUI()
        self.workers = []

    def initUI(self):
        self.layout = QVBoxLayout(self)

        top_layout = QHBoxLayout()
        self.url_input = QLineEdit(self)
        self.url_input.setPlaceholderText("Enter YouTube URL here")
        top_layout.addWidget(self.url_input)

        self.format_combo = QComboBox(self)
        self.format_combo.addItems(["MP4", "MOV", "AVI", "WMV", "FLV", "WEBM", "MP3", "WAV", "M4A", "FLAC"])
        top_layout.addWidget(self.format_combo)
        self.layout.addLayout(top_layout)

        self.save_path_button = QPushButton("Choose save folder", self)
        self.update_save_path_button()
        self.save_path_button.clicked.connect(self.choose_save_path)
        self.layout.addWidget(self.save_path_button)

        # Création d'une zone défilable pour les téléchargements
        self.scroll_area = QScrollArea(self)
        self.scroll_widget = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_widget)
        self.scroll_widget.setLayout(self.scroll_layout)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(self.scroll_widget)
        self.layout.addWidget(self.scroll_area)

        self.download_button = QPushButton("Download", self)
        self.download_button.clicked.connect(self.start_download)
        self.layout.addWidget(self.download_button)

        self.theme_button = QPushButton("Switch to Dark Mode", self)
        self.theme_button.clicked.connect(self.toggle_theme)
        self.layout.addWidget(self.theme_button)

        self.threadpool = QThreadPool()
        print("Multithreading with maximum %d threads" % self.threadpool.maxThreadCount())

        self.setWindowTitle('YouTube Downloader')
        self.setWindowIcon(QIcon(icon_path))
        self.setMinimumSize(1000, 500)
        self.apply_theme()

    def update_save_path_button(self):
        if self.settings['save_path']:
            self.save_path_button.setText(f"Folder: {self.settings['save_path']}")
        else:
            self.save_path_button.setText("Choose save folder")

    def choose_save_path(self):
        self.settings['save_path'] = QFileDialog.getExistingDirectory(self, "Select Directory")
        self.update_save_path_button()
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
            self.settings = {'dark_mode': False, 'save_path': '', 'counts': {'mp3': 0, 'mp4': 0, 'total': 0}}

    def save_settings(self):
        with open(setting_path, 'w') as f:
            json.dump(self.settings, f)

    def toggle_theme(self):
        self.settings['dark_mode'] = not self.settings['dark_mode']
        self.save_settings()
        self.apply_theme()

    def apply_theme(self):
        dark_mode = self.settings['dark_mode']
        text_color = "#D0D0D0" if dark_mode else "#333333"
        bg_color = "#1E1E1E" if dark_mode else "#FAFAFA"
        element_bg = "#252526" if dark_mode else "#FFFFFF"
        bbg_color = "#3A3A3C" if dark_mode else "#F0F0F0"
        bhover_color = "#575759" if dark_mode else "#E0E0E0"
        border_color = "rgba(255, 255, 255, 0.15)" if dark_mode else "rgba(0, 0, 0, 0.1)"
        button_shadow = "rgba(0, 0, 0, 0.4)" if dark_mode else "rgba(0, 0, 0, 0.1)"
        font_size = "16px"  # Taille de police générale
        button_font_size = "14px"  # Taille de police pour les boutons
        border_radius = "5px"  # Rayon de bordure pour les champs arrondis
        self.setStyleSheet(f"""
            QWidget {{
                font-family: 'Arial', sans-serif;
                font-size: {font_size};
                color: {text_color};
                background-color: {bg_color};
                padding: 10px;
            }}
            QLineEdit, QComboBox, QPushButton, QLabel {{
                border: 1px solid {border_color};
                border-radius: {border_radius};
                padding: 10px;
                margin: 10px;
                background: {element_bg};
            }}
            QPushButton {{
                font-size: {button_font_size};
                background-color: {bbg_color};
                box-shadow: 0 2px 5px {button_shadow};
            }}
            QPushButton:hover {{
                background-color: {bhover_color};
            }}
            QComboBox::down-arrow {{
                image: url({arrow_path});
                width: 10px;
                height: 10px;
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
            QWidget#dlwidget 
            {{
                margin: 0px 0px 0px 0px;
                padding: 0px 0px 0px 0px;
                border: pink;
                border-radius: 15px;
                background-color: pink;
            }}
        """)
        if self.settings['dark_mode']:
            self.theme_button.setText("Switch to Light Mode")
        else:
            self.theme_button.setText("Switch to Dark Mode")


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
