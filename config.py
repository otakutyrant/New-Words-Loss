#!/usr/bin/env python

from pathlib import Path

from calibre.utils.config import JSONConfig
from qt.core import QFileDialog, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget

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

        self.label = QLabel("Learned Words txt path:")

        self.learned_words_pathname_line_edit = QLineEdit()
        self.learned_words_pathname_line_edit.setPlaceholderText(
            "Choose the path of the learned words file"
        )
        self.learned_words_pathname_line_edit.setText(prefs["learned_words_pathname"])

        self.choose_path_button = QPushButton("Choose Path")
        self.choose_path_button.clicked.connect(self.set_learned_words_pathname)

        # Layout
        layout = QVBoxLayout()
        layout.addWidget(self.learned_words_pathname_line_edit)
        layout.addWidget(self.choose_path_button)

        self.setLayout(layout)

    def set_learned_words_pathname(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Choose File", ".", "Text Files (*.txt)"
        )
        self.learned_words_pathname_line_edit.setText(path)

    def save_settings(self):
        prefs["learned_words_pathname"] = self.learned_words_pathname_line_edit.text()
