import cgitb
import sys

from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (QApplication)

from YtDownloaderApp.data import data
from YtDownloaderApp.ui import App

cgitb.enable(format='text')

if __name__ == '__main__':
    data.load_data()
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(data.icon_path))
    ex = App()
    ex.show()
    sys.exit(app.exec_())
