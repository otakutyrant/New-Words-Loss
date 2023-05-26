import logging
import re
import traceback
import typing
from collections import Counter
from pathlib import Path
from typing import List

import numpy as np
from calibre.ebooks import DRMError
from calibre.utils.ipc.job import ParallelJob
from calibre.utils.ipc.server import Server
from calibre_plugins.new_words.action import Book
from calibre_plugins.new_words.config import prefs


def do_count(books: List[Book], cpus, notification=None):
    """
    Master job, to launch child jobs to count new words in this list of books
    """
    server = Server(pool_size=cpus)

    # Queue all the jobs
    for book in books:
        args = [
            "calibre_plugins.new_words.jobs",
            "do_count_for_one_book",
            (book,),
        ]
        job = ParallelJob("arbitrary", str(book.book_id), done=None, args=args)
        job.book_id = book.book_id
        server.add_job(job)

    # dequeue the job results as they arrive, saving the results
    count = 0
    total = len(books)
    results = {}
    while count < total:
        job = server.changed_jobs_queue.get()
        job.update()
        if job.is_finished:
            results[job.book_id] = job.result
            count += 1
            logging.debug(job.details)

    server.close()
    return results


def do_count_for_one_book(book: Book):
    """
    Child job, to calculate new words loss in this specific book
    """
    results = {}
    try:
        lemma_pathname = generate_lemmas(book.pathname)
        new_words_pathname = generate_new_words(lemma_pathname)
        results["new words"] = new_word_loss(new_words_pathname)
        return results
    except DRMError:
        logging.error("Cannot read pages due to DRM Encryption")
        return results
    except Exception:
        traceback.print_exc()
        return results


def filter_to_valid_words(file_):
    words = [
        word
        for line in file_
        for word in line.split()
        if word.isalpha() and word.isascii()
    ]
    return words


def discard_duplicate_words(words):
    set_ = set(words)
    words = [word.lower() if word.lower() in set_ else word for word in words]
    return words


def discard_capital_words(words):
    words = [word for word in words if word.islower()]
    return words


def generate_lemmas(book_pathname: Path) -> Path:
    hashmap = {}
    lemma_pathname = get_resources("lemma.en.txt")  # type: ignore # noqa: F821
    with open(lemma_pathname) as lemma_file:
        for line in lemma_file:
            lemma, _, inflections = line.strip().split(" ")
            lemma = lemma.split("/")[0]
            hashmap[lemma] = lemma
            for inflection in inflections.split(","):
                hashmap[inflection] = lemma

    lemma_pathname = book_pathname.parent / "lemmas.txt"
    with open(book_pathname) as file_, open(lemma_pathname, "w") as lemma_file:
        words = filter_to_valid_words(file_)
        words = discard_duplicate_words(words)
        words = discard_capital_words(words)

        lemmas = [hashmap.get(word, word) for word in words]
        counter = Counter(lemmas)
        for word, count in counter.most_common():
            lemma_file.write(f"{word} {count}\n")
    return lemma_pathname


def generate_new_words(lemma_pathname: Path) -> Path:
    learnt_words_pathname = prefs["learnt_words_pathname"]
    learnt_words = set()
    with open(learnt_words_pathname) as file_:
        for line in file_:
            word = re.split(r"\W+", line, 1)[0]
            learnt_words.add(word)

    counter: typing.Counter[str] = Counter()
    with open(lemma_pathname) as file_:
        for line in file_:
            word, count_str = line.split()
            counter[word] = int(count_str)

    for word in learnt_words:
        del counter[word]

    new_words_pathname = lemma_pathname.parent / "new_words.txt"
    with open(new_words_pathname, "w") as new_words_file:
        for word, count in counter.most_common():
            new_words_file.write(f"{word} {count}\n")
    return new_words_pathname


def new_word_loss(new_words_pathname: Path):
    counts = []
    with open(new_words_pathname) as file_:
        for line in file_:
            _, count = line.split()
            counts.append(count)
    counts = np.array(counts)
    probabilities = counts / np.sum(counts)
    new_word_loss = np.sum(-probabilities * np.log(probabilities))
    return new_word_loss
