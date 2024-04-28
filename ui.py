import json
from worker import Worker
from pytube import YouTube
import logging

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QComboBox, QPushButton, QScrollArea, QProgressBar, QLabel, QFileDialog
from PyQt5.QtCore import pyqtSignal, QThreadPool
from PyQt5.QtGui import QIcon

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
    def __init__(self, setting_path, icon_path, arrow_path):
        super().__init__()
    
        self.workers = []
        self.setting_path = setting_path
        self.icon_path = icon_path
        self.arrow_path = arrow_path
        
        self.load_settings()
        self.initUI()
    
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
        self.setWindowIcon(QIcon(self.icon_path))
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
            self.path_label.setText("Please enter a URL")
            return

        if not self.settings['save_path']:
            self.path_label.setText("Please select a save folder")
            return
        if url in Worker.downloading_urls:
            print("url is already being downloaded !")
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
        if url.strip() == "":
            # Handle error
            return
        worker = Worker(url, format, save_path)
        self.workers.append(worker)
        worker.signals.progress_updated.connect(download_widget.update_progress)
        worker.signals.download_complete.connect(lambda: download_widget.update_progress(100))
        worker.signals.download_error.connect(self.handle_download_error)
        self.threadpool.start(worker)

    def handle_download_error(self, error_message):
        logging.error(f"Error during download: {error_message}")
        # Update UI or notify user about the error

    def load_settings(self):
        try:
            with open(self.setting_path, 'r') as f:
                self.settings = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.settings = {'dark_mode': False, 'save_path': '', 'counts': {'mp3': 0, 'mp4': 0, 'total': 0}}

    def save_settings(self):
        with open(self.setting_path, 'w') as f:
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
                image: url({self.arrow_path});
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
