import sys
import os

def normalize_title(title):
    # C'est le pire code que j'ai jamais écrit
    return title.lower().strip().replace(" ", "_").replace("||", "_").replace(":", "").replace("?", "").replace("!", "").replace(".", "").replace(",", "").replace("(", "").replace(")", "").replace("[", "").replace("]", "").replace("{", "").replace("}", "").replace("/", "").replace("\\", "").replace("'", "").replace('"', "")

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