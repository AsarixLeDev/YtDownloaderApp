import re

from PyQt5.QtCore import pyqtSignal, QThreadPool, Qt
from PyQt5.QtGui import QIcon, QFont
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QLineEdit, QLabel, QFileDialog,
                             QHBoxLayout, QComboBox, QProgressBar, QScrollArea)
from pytube import YouTube

from YtDownloaderApp import frontend, file_formats
from YtDownloaderApp import workers
from YtDownloaderApp.data import data
from YtDownloaderApp.funcs import show_toast, get_youtube_content


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
        layout.setContentsMargins(0, 0, 0, 0)

        video_name = YouTube(self.url).title

        self.video_label = QLabel(video_name)  # Ici, on pourrait extraire le titre avec youtube_dl si nécessaire
        self.video_label.setFixedWidth(int(self.width() * 0.5))  # 50% de la largeur du parent
        self.video_label.setFixedHeight(60)
        self.video_label.setStyleSheet("""
                    QLabel {
                        font-size: 20px;
                    }
                """)

        self.resized.connect(lambda: self.video_label.setFixedWidth(int(self.width() * 0.5)))
        self.video_label.setWordWrap(False)
        layout.addWidget(self.video_label)

        self.progress = QProgressBar(self)
        self.progress.setFixedWidth(int(self.width() * 0.5) - 70)
        self.resized.connect(lambda: self.progress.setFixedWidth(int(self.width() * 0.5) - 70))
        self.progress.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.progress)

        self.cancel_button = QPushButton()
        self.cancel_button.setIcon(QIcon(data.close_path))
        self.cancel_button.setFixedHeight(50)
        self.cancel_button.setFixedWidth(30)
        self.cancel_button.clicked.connect(self.cancel_download)
        self.cancel_button.setStyleSheet("""
                    QPushButton {
                        border: 0px;
                    }
                    QPushButton:hover {
                        background-color: #ff6b6b;
                        border-color: #2a2d34;
                    }
                """)
        layout.addWidget(self.cancel_button)
        self.setLayout(layout)

    def cancel_download(self):
        try:
            self.cancel_signal.emit(self.url)
            self.layout.removeWidget(self.progress)
            self.layout.removeWidget(self.video_label)
            self.layout.removeWidget(self.cancel_button)
            self.layout.removeWidget(self)
            self.deleteLater()
        except Exception as e:
            print(e)

    def update_progress(self, percent):
        try:
            self.progress.setValue(percent)
        except Exception as e:
            print(e)

    def resizeEvent(self, event):
        super(DownloadWidget, self).resizeEvent(event)
        self.resized.emit()

    def handle_download_error(self, error_title, error_subtitle):
        pass

    resized = pyqtSignal()


class HoverLineEdit(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
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
        self.addItems(file_formats.get_formats_str())

    def enterEvent(self, event):
        self.lineEdit().apply_hover_style()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.lineEdit().apply_normal_style()
        super().leaveEvent(event)


class App(QWidget):
    def __init__(self):
        super().__init__()

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
        if data.save_folder_path:
            self.path_input.setText(data.save_folder_path)
        mid_layout.addWidget(self.path_input)

        self.path_input_button = QPushButton("Choose")
        self.path_input_button.setFixedWidth(int(center_widget.width() * 0.15))
        self.resized.connect(lambda: self.path_input_button.setFixedWidth(int(center_widget.width() * 0.15)))
        self.path_input_button.setObjectName("button-primary")
        self.path_input_button.clicked.connect(self.choose_save_path)
        mid_layout.addWidget(self.path_input_button, alignment=Qt.AlignRight)
        layout.addLayout(mid_layout)

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
        self.setWindowIcon(QIcon(data.icon_path))
        self.setMinimumSize(1000, 500)
        frontend.apply_theme(self)

    def resizeEvent(self, event):
        super(App, self).resizeEvent(event)
        self.resized.emit()

    def closeEvent(self, a0):
        data.save_settings()

    resized = pyqtSignal()

    def choose_save_path(self):
        new_path = QFileDialog.getExistingDirectory(self, "Select Directory")
        if not new_path or new_path == '':
            return
        data.save_folder_path = new_path
        self.path_input.setText(new_path)

    def start_download(self):
        url = self.url_input.text()
        if url.strip() == "":
            show_toast("No URL", "No URL was provided. Please fill the text area.")
            return
        if not re.match(r'^(https?://)?(www\.)?(youtube\.com|youtu\.?be)/', url):
            show_toast("Invalid YouTube URL", "The URL you provided is not a YouTube URL.")
            return
        if not data.save_folder_path:
            show_toast("No Save folder", "No save folder was provided. Please select one.")
            return

        format_str = self.format_combo.currentText().lower()
        format = file_formats.get_format(format_str)
        for yt_url in get_youtube_content(url):
            self.download_video(yt_url, format)

    def download_video(self, url, format):
        if workers.is_downloading(url):
            show_toast("URL already being downloaded",
                       "The url you specified is already being downloaded. Please wait !")
            return
        download_widget = DownloadWidget(url, format, self.scroll_layout)
        self.scroll_layout.addWidget(download_widget)
        url = download_widget.url
        save_path = data.save_folder_path
        worker = workers.Worker(url, format, save_path)
        worker.signals.progress_updated.connect(download_widget.update_progress)
        worker.signals.download_complete.connect(lambda: download_widget.update_progress(100))
        worker.signals.download_error.connect(download_widget.handle_download_error)
        download_widget.cancel_signal.connect(worker.cancel)
        self.threadpool.start(worker)
