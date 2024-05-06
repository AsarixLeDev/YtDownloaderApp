import json
import os
import sys


class Data:
    def __init__(self):
        self.setting_path = None
        self.icon_path = None
        self.close_path = None
        self.arrow_path = None
        self.save_folder_path = None
        self.settings = {}

    def load_data(self):
        if getattr(sys, 'frozen', False):
            # Si l'application est exécutée en tant qu'exécutable OneFile.
            base_path = sys._MEIPASS
        else:
            # Si l'application est exécutée normalement (par exemple pendant le développement).
            base_path = os.path.dirname(__file__)
        self.setting_path = os.path.join(base_path, 'resources/json/settings.json')
        self.icon_path = os.path.join(base_path, 'resources/icons/icon.ico')
        self.close_path = os.path.join(base_path, 'resources/images/close.png')
        self.arrow_path = os.path.join(base_path, 'resources/images/img.png')
        try:
            with open(self.setting_path, 'r') as f:
                json_data = json.load(f)
                if "save_path" in json_data:
                    self.save_folder_path = json_data["save_path"]
        except (FileNotFoundError, json.JSONDecodeError):
            self.settings = {'save_path': ''}

    def save_settings(self):
        settings = {}
        if self.save_folder_path:
            settings["save_path"] = self.save_folder_path
        with open(self.setting_path, 'w') as f:
            json.dump(settings, f)


data = Data()
