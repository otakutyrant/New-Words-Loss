from collections import namedtuple
from pathlib import Path

from calibre.ebooks.conversion.config import get_available_formats_for_book
from calibre.gui2 import warning_dialog
from calibre.gui2.actions import InterfaceAction
from calibre_plugins.new_words_loss.log import logger
from PyQt6.QtGui import QIcon

Book = namedtuple("Book", "id, title, pathname")


class NewWordsAction(InterfaceAction):
    name = "New Words Loss"
    # Create our top-level menu/toolbar action
    # (text, icon_path, tooltip, keyboard shortcut)
    action_spec = ("New Words Loss", None, "Analyze new words in a book.", ())
    action_type = "current"
    action_add_menu = True

    def genesis(self):
        self.is_library_selected = True

        icon = get_icons("images/new_words_loss.png", "New Words Loss")  # noqa: F821
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
            triggered=self._all_for_one_trigged,
        )
        self.qaction.setMenu(self.menu)

        # It seems that __init__ cannot work well so I put this code here.
        self.custom_columns = {
            "#new_words_loss": "New Words Loss",
            "#top_five_new_words": "Top Five New Words",
            "#new_words_count": "New Words Count",
        }

    def location_selected(self, loc):
        self.is_library_selected = loc == "library"

    def config(self):
        self.interface_action_base_plugin.do_user_config(self.gui)

    def _get_available_books(self) -> list[Book]:
        if not self._custom_columns_available():
            message = " or ".join(self.custom_columns.keys()) + " not available"
            logger.warning(message)
            warning_dialog(self.gui, "New Words Loss warnings", message)
            return []

        book_ids = self.gui.library_view.get_selected_ids()
        if not self._is_book_selected(book_ids):
            message = "No book selected."
            logger.warning()
            warning_dialog(self.gui, "New Words Loss warnings", message)
            return []

        book_ids = self._get_book_ids_with_txt_format(book_ids)
        books = []
        for book_id in book_ids:
            title = self.gui.current_db.new_api.field_for("title", book_id)
            pathname = Path(self.gui.current_db.new_api.format_abspath(book_id, "txt"))
            book = Book(book_id, title, pathname)
            books.append(book)
        books_for_debug = "\t".join(map(str, books))
        logger.debug(books_for_debug)

        logger.info(f"{len(books)} available books acquired.")
        return books

    def _toolbar_triggered(self):
        books = self._get_available_books()
        # Unfortuanately, only objects of basic types can pass to functions
        # which are called by job_manager. So namedtuple objects are converted
        # to tuple objects here.
        # See: https://www.mobileread.com/forums/showthread.php?t=354128
        books = [tuple(book) for book in books]
        cpus = self.gui.job_manager.server.pool_size
        args = [
            "calibre_plugins.new_words_loss.jobs",
            "do_jobs",
            (books, cpus),
        ]
        self.gui.job_manager.run_job(
            self.Dispatcher(self._fill_fields),
            "arbitrary_n",
            args=args,
            description="Infer New Word Loss",
        )

        message = f"Infering New Words Loss in {len(books)} books."
        logger.info(message)

    def _custom_columns_available(self) -> bool:
        custom_columns = self.gui.library_view.model().custom_columns.keys()
        intersection = set(self.custom_columns) & set(custom_columns)
        return len(intersection) > 0

    def _is_book_selected(self, book_ids):
        # TODO: what is the relationship between self.is_library_selected and
        # self.gui.library_view.get_selected_ids()?
        return self.is_library_selected and len(book_ids) > 0

    def _get_book_ids_with_txt_format(self, book_ids) -> list[int]:
        remained_book_ids = []
        other_book_ids = []
        for book_id in book_ids:
            book_formats = get_available_formats_for_book(
                self.gui.current_db.new_api, book_id
            )
            if "txt" in book_formats:
                remained_book_ids.append(book_id)
            else:
                other_book_ids.append(book_id)
        book_ids = remained_book_ids

        if len(other_book_ids) > 0:
            summary = (
                "Could not analyse new words in "
                f"{len(other_book_ids)} of {len(book_ids)} books, "
                "because they do not have txt format."
            )
            messages = "These books miss txt format:\n"
            messages = messages + "\n".join(
                self.gui.current_db.new_api.field_for("title", book_id)
                for book_id in other_book_ids
            )
            warning_dialog(
                self.gui,
                "New Words Loss warnings",
                summary,
                messages,
            ).exec_()

        logger.debug(f"{len(book_ids)} books with txt format acquired.")
        return book_ids

    def _all_for_one_trigged(self):
        books = self._get_available_books()
        # Unfortuanately, only objects of basic types can pass to functions
        # which are called by job_manager. So namedtuple objects are converted
        # to tuple objects here.
        # See: https://www.mobileread.com/forums/showthread.php?t=354128
        books = [tuple(book) for book in books]
        cpus = self.gui.job_manager.server.pool_size
        args = [
            "calibre_plugins.new_words_loss.jobs",
            "do_all_for_one",
            (books, cpus),
        ]
        self.gui.job_manager.run_job(
            None,
            "arbitrary_n",
            args=args,
            description="All for One!",
        )

        message = f"All for One done in {len(books)} books."
        logger.info(message)

    def _fill_fields(self, job):
        logger.debug("Start.")

        if job.failed:
            logger.error("The inferting job totally failed.")
            return self.gui.job_exception(job, dialog_title="Failed to fill fields.")

        def callback(payload):
            self, book_stats_map = payload
            logger.info("Proceed to fill columns.")
            for book_id, stats in book_stats_map.items():
                for custom_field, stat in zip(
                    self.custom_columns.keys(), stats, strict=True
                ):
                    self.gui.current_db.new_api.set_field(custom_field, {book_id: stat})

                title = self.gui.current_db.new_api.field_for("title", book_id)
                logger.info(f"{title=} columns filled.")
                logger.info(f"{book_id=} {stats=}")

            book_ids = list(book_stats_map.keys())
            self.gui.library_view.model().refresh_ids(book_ids)
            self.gui.library_view.model().refresh_ids(
                book_ids,
                current_row=self.gui.library_view.currentIndex().row(),
            )
            message = (
                f"New Words Loss done in {len(book_ids)} books. " "All columns updated."
            )
            logger.info(message)

        book_stats_map = job.result
        payload = (self, book_stats_map)
        message = (
            f"<p>New Word Loss plugin found <b>{len(book_stats_map)} "
            "statistics</b>. "
            "Proceed with updating columns in your library?"
        )
        self.gui.proceed_question(
            callback=callback,
            payload=payload,  # Passed to the callback function.
            html_log=job.details,
            log_viewer_title="Count New Word Loss",
            title="Count complete",
            msg=message,
            cancel_callback=lambda: logger.info("Canceled to fill columns."),
        )
