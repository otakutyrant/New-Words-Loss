from pathlib import Path

from calibre.utils.config import JSONConfig
from qt.core import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

PLUGIN_ICONS = ["images/new_words_loss.png"]


# This is where all preferences for this plugin will be stored
# Remember that this name (i.e. plugins/interface_demo) is also
# in a global namespace, so make it as unique as possible.
# You should always prefix your config file name with plugins/,
# so as to ensure you dont accidentally clobber a calibre config file
prefs = JSONConfig("plugins/new_words_loss")

# Set defaults
prefs.defaults["learned_words_pathname"] = str(Path.home() / "learned_words.txt")
prefs.defaults["all_for_one_pathname"] = str(Path.home() / "all_for_one.txt")


class ConfigWidget(QWidget):
    def __init__(self):
        super().__init__()

        vboxlayout = QVBoxLayout()
        self.setLayout(vboxlayout)

        hboxlayout = QHBoxLayout()
        vboxlayout.addLayout(hboxlayout)

        label = QLabel("Learned Words txt path:")
        hboxlayout.addWidget(label)

        self.learned_words_pathname_line_edit = QLineEdit(self)
        self.learned_words_pathname_line_edit.setPlaceholderText(
            "Choose the path of the learned words file"
        )
        self.learned_words_pathname_line_edit.setText(
            str(prefs["learned_words_pathname"])
        )
        hboxlayout.addWidget(self.learned_words_pathname_line_edit)

        choose_path_button = QPushButton("Choose Path")
        choose_path_button.clicked.connect(self.set_learned_words_pathname)
        hboxlayout.addWidget(choose_path_button)

        hboxlayout = QHBoxLayout()
        vboxlayout.addLayout(hboxlayout)

        label = QLabel("All for One path:")
        hboxlayout.addWidget(label)

        self.all_for_one_pathname_line_edit = QLineEdit(self)
        self.all_for_one_pathname_line_edit.setPlaceholderText(
            "Choose the path of the All for One file"
        )
        self.all_for_one_pathname_line_edit.setText(str(prefs["all_for_one_pathname"]))
        hboxlayout.addWidget(self.all_for_one_pathname_line_edit)

        choose_path_button = QPushButton("Choose Path")
        choose_path_button.clicked.connect(self.set_learned_words_pathname)
        hboxlayout.addWidget(choose_path_button)

    def set_learned_words_pathname(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Choose File", ".", "Text Files (*.txt)"
        )
        self.learned_words_pathname_line_edit.setText(path)

    def set_all_for_one_pathname(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Choose File", ".", "Text Files (*.txt)"
        )
        self.all_for_one_pathname_line_edit.setText(path)

    def save_settings(self):
        prefs["learned_words_pathname"] = self.learned_words_pathname_line_edit.text()
        prefs["all_for_one_file_pathname"] = self.all_for_one_pathname_line_edit.text()
