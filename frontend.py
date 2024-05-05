from YtDownloaderApp.data import data


def apply_theme(widget):
    url_arrow_path = data.arrow_path.replace('\\', "/")
    widget.setStyleSheet(f"""
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
            border: 2px solid #4e8df5;
            border-radius: 4px;
            background-color: #2a2d34;
        }}

        QProgressBar::chunk {{
            background-color: #05B8CC;
            border-radius: 4px; /* Match the border radius of the progress bar itself */
        }}

        QLabel {{
            text-align: left;
            margin: 10px 0;
            padding-left: 10px; /* Adds left padding for alignment */
        }}
    """)
