# Importation des autres fichiers 
from funcs import load_data
from ui import App

# Importation des modules
import cgitb
import sys

# Importation des modules PyQt5
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication

cgitb.enable(format='text')

if __name__ == '__main__':
    setting_path, icon_path, arrow_path = load_data()
    print("setting_path", setting_path)
    print("icon_path", icon_path)
    print("arrow_path", arrow_path)
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(icon_path))
    ex = App(setting_path, icon_path, arrow_path)
    ex.show()
    sys.exit(app.exec_())