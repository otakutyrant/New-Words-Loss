import logging
import traceback
from collections import OrderedDict
from pathlib import Path
from typing import NamedTuple

from calibre.ebooks.conversion.config import get_available_formats_for_book
from calibre.gui2 import warning_dialog
from calibre.gui2.actions import InterfaceAction
from calibre_plugins.new_words.jobs import do_count
from PyQt6.QtGui import QIcon


class Book(NamedTuple):
    book_id: int
    title: str
    pathname: Path


class NewWordsAction(InterfaceAction):
    name = "New Words"
    # Create our top-level menu/toolbar action
    # (text, icon_path, tooltip, keyboard shortcut)
    action_spec = ("New Words", None, "Analyze new words in a book.", ())
    action_type = "current"
    action_add_menu = True

    def genesis(self):
        self.is_library_selected = True

        icon = get_icons("images/new_words.png", "New Words")  # noqa: F821
        self.qaction.setIcon(icon)
        self.qaction.triggered.connect(self._toolbar_triggered)

        self.menu = self.qaction.menu()
        self.create_menu_action(
            self.menu,
            "Preferences",
            "Preferences",
            icon=QIcon.ic("config.png"),
            triggered=self.config,
        )
        self.create_menu_action(
            self.menu,
            "All for One",
            "All for One",
            icon=QIcon.ic("save.png"),
            description=(
                "Iterate all selected books, "
                "and generate one whole lemmas.txt that counts new words"
            ),
            triggered=self._all_for_one,
        )
        self.qaction.setMenu(self.menu)

    def location_selected(self, loc):
        self.is_library_selected = loc == "library"

    def config(self):
        self.interface_action_base_plugin.do_user_config(self.gui)

    def _are_selected_books_available(self):
        if self._check_the_custom_column() is False:
            logging.warning("the custom column new_words_loss is not defined")
            return False

        self.book_ids = self.gui.library_view.get_selected_ids()
        if not self._is_book_selected():
            logging.warning("no book selected")
            return False

        self._filter_book_ids_by_format()
        return len(self.book_ids) > 0

    def _toolbar_triggered(self):
        if self._are_selected_books_available():
            self._do_job()

    def _check_the_custom_column(self) -> bool:
        custom_columns = self.gui.library_view.model().custom_columns.keys()
        return "#new_words_loss" in custom_columns

    def _is_book_selected(self):
        # TODO: what is the relationship between self.is_library_selected and
        # self.gui.library_view.get_selected_ids()?
        return self.is_library_selected and len(self.book_ids) > 0

    def _filter_book_ids_by_format(self):
        logging.info("start filtering books with txt format")
        remained_book_ids = []
        unexpected_results = OrderedDict()
        for book_id in self.book_ids:
            book_formats = get_available_formats_for_book(
                self.gui.current_db.new_api, book_id
            )
            if "txt" in book_formats:
                remained_book_ids.append(book_id)
            else:
                unexpected_results[
                    book_id
                ] = "You should convert the book to txt at first."
        self.book_ids = remained_book_ids

        if len(unexpected_results) > 0:
            summary = f"Could not analyse new words in \
                {len(unexpected_results)} of {len(self.book_ids)} books, \
                for reasons shown in details below."
            messages = []
            for book_id, error in unexpected_results.items():
                title = self.gui.current_db.new_api.field_for("title", book_id)
                message = f"{title} ({error})"
                messages.append(message)
            messages = "\n".join(messages)
            warning_dialog(
                self.gui,
                "new_words warnings",
                summary,
                messages,
            ).exec_()
        logging.info("end filtering books with txt format")

    def _do_job(self):
        for book_id in self.book_ids:
            title = self.gui.current_db.new_api.field_for("title", book_id)
            pathname = Path(self.gui.current_db.new_api.format_abspath(book_id, "txt"))
            logging.info(f"handling {title=} {pathname=}")
            book = Book(book_id, title, pathname)
            try:
                loss = do_count(book)
            except Exception:
                traceback.print_exc()
            else:
                logging.info(f"calculated {loss=}")
                self.gui.current_db.new_api.set_field(
                    "#new_words_loss", {book_id: loss}
                )
        logging.info(f"About to refresh GUI - book_ids={self.book_ids}")
        self.gui.library_view.model().refresh_ids(self.book_ids)
        self.gui.library_view.model().refresh_ids(
            self.book_ids,
            current_row=self.gui.library_view.currentIndex().row(),
        )
        self.gui.status_bar.show_message(
            f"Counting new_words_loss in {len(self.book_ids)} books"
        )

    def _all_for_one(self):
        raise NotImplementedError
