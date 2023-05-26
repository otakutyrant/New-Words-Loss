import re
import typing
from collections import Counter
from pathlib import Path

import numpy as np
from calibre_plugins.new_words.config import prefs


def do_count(book):
    lemma_pathname = generate_lemmas(book.pathname)
    new_words_pathname = generate_new_words(lemma_pathname)
    loss = new_word_loss(new_words_pathname)
    return loss


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
    bytes_string = get_resources("lemma.en.txt")  # type: ignore # noqa: F821
    str_string = bytes_string.decode("utf-8")
    lines = str_string.strip().split("\n")  # there is a \n in the end
    for line in lines:
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
    learned_words_pathname = prefs["learned_words_pathname"]
    learned_words = set()
    with open(learned_words_pathname) as file_:
        for line in file_:
            word = re.split(r"\W+", line, 1)[0]
            learned_words.add(word)

    counter: typing.Counter[str] = Counter()
    with open(lemma_pathname) as file_:
        for line in file_:
            word, count_str = line.split()
            counter[word] = int(count_str)

    for word in learned_words:
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
            counts.append(int(count))
    counts = np.array(counts)
    probabilities = counts / np.sum(counts)
    new_word_loss = np.sum(-probabilities * np.log(probabilities))
    return new_word_loss
