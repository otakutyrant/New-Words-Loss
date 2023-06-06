import logging
import re
import typing
from collections import Counter
from pathlib import Path

import numpy as np

try:
    import stanza
except ImportError:
    has_stanza_installed = False
else:
    has_stanza_installed = True
from calibre_plugins.new_words.config import prefs


def do_count(book):
    lemma_pathname = generate_lemmas(book.pathname)
    new_words_pathname, counter = generate_new_words(lemma_pathname)
    loss = new_word_loss(new_words_pathname)
    return loss, counter


def is_valid_word(word: str):
    return all(char.isalpha() or char == "-" for char in word)


def filter_to_valid_words(file_):
    words = [word for line in file_ for word in line.split() if is_valid_word(word)]
    return words


def discard_duplicate_words(words):
    set_ = set(words)
    words = [word.lower() if word.lower() in set_ else word for word in words]
    return words


def discard_capital_words(words):
    words = [word for word in words if word.islower()]
    return words


def generate_lemmas_by_lookup(book_pathname: Path) -> Path:
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


def preprocess_before_ai(book_context: str) -> str:
    # stanza seems to regard "well..." as a word wrongly
    book_context = book_context.replace("…", " ")
    return book_context


def generate_lemmas_by_ai(
    book_pathname,
    nlp=stanza.Pipeline(  # noqa: E: B008
        lang="en", processors="tokenize,mwt,pos,lemma"
    ),
) -> Path:
    lemma_pathname = book_pathname.parent / "lemmas.txt"
    pronoun_pathname = book_pathname.parent / "pronouns.txt"
    with (
        open(book_pathname, "r") as book_file,
        open(lemma_pathname, "w") as lemma_file,
        open(pronoun_pathname, "w") as pronoun_file,
    ):
        book_context = book_file.read()
        book_context = preprocess_before_ai(book_context)
        doc = nlp(book_context)
        lemma_counter = Counter()
        pronoun_counter = Counter()
        for sentence in doc.sentences:
            for word in sentence.words:
                if word.pos == "PROPN":
                    pronoun_counter[word.lemma] += 1
                elif (
                    word.pos not in ("PUNCT", "NUM", "SYM", "X")
                    and word.lemma is not None
                    and is_valid_word(word.lemma)
                ):
                    # Stanza seems to generate some lemmas with a capital letter
                    # in the beginning. Altough lowering all lemmas means "I"
                    # is affected too.
                    logging.debug(f"{word.lemma=} {word.pos=}")
                    lemma_counter[word.lemma.lower()] += 1
        for word, count in lemma_counter.most_common():
            lemma_file.write(f"{word} {count}\n")
        for word, count in pronoun_counter.most_common():
            pronoun_file.write(f"{word} {count}\n")
    return lemma_pathname


def generate_lemmas(book_pathname: Path) -> Path:
    if has_stanza_installed:
        return generate_lemmas_by_ai(book_pathname)
    else:
        return generate_lemmas_by_lookup(book_pathname)


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
    logging.debug(f"{new_words_pathname=}")
    with open(new_words_pathname, "w") as new_words_file:
        for word, count in counter.most_common():
            new_words_file.write(f"{word} {count}\n")
    return new_words_pathname, counter


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
