#!/usr/bin/env python

from pathlib import Path

from calibre.utils.config import JSONConfig
from qt.core import QFileDialog, QGridLayout, QLabel, QLineEdit, QPushButton, QWidget

PLUGIN_ICONS = ["images/new_words.png"]


# This is where all preferences for this plugin will be stored
# Remember that this name (i.e. plugins/interface_demo) is also
# in a global namespace, so make it as unique as possible.
# You should always prefix your config file name with plugins/,
# so as to ensure you dont accidentally clobber a calibre config file
prefs = JSONConfig("plugins/new_words")

# Set defaults
prefs.defaults["learned_words_pathname"] = str(Path.home() / "learned_words.txt")


class ConfigWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setGeometry(20, 20, 20, 20)

        layout = QGridLayout()
        self.setLayout(layout)

        label = QLabel("Learned Words txt path:")
        layout.addWidget(label, 0, 0, 1, 1)

        self.learned_words_pathname_line_edit = QLineEdit(self)
        self.learned_words_pathname_line_edit.setPlaceholderText(
            "Choose the path of the learned words file"
        )
        self.learned_words_pathname_line_edit.setText(
            str(prefs["learned_words_pathname"])
        )
        layout.addWidget(self.learned_words_pathname_line_edit, 0, 1, 1, 2)

        choose_path_button = QPushButton("Choose Path")
        choose_path_button.clicked.connect(self.set_learned_words_pathname)
        layout.addWidget(choose_path_button, 0, 2, 1, 1)

    def set_learned_words_pathname(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Choose File", ".", "Text Files (*.txt)"
        )
        self.learned_words_pathname_line_edit.setText(path)

    def save_settings(self):
        prefs["learned_words_pathname"] = self.learned_words_pathname_line_edit.text()
