from typing import NamedTuple, Callable
from pathlib import Path
import re


# Define Error Classes


class TitleNotFoundError(Exception):
    def __init__(self, path: Path):
        msg = f"File {path} does not contain a valid Title"
        super().__init__(msg)


# Define Module Classes


class ChordFile(NamedTuple):
    title: str
    artist: str
    path: Path
    tags: set[str]


# Function Definitions


def __read_meta(path: Path) -> ChordFile:
    """
    Liest die Metadateien (Frontmatter sowie erste Überschrift) aus einer
    Obsidian-md-Datei ein und gibt sie als ChordFile zurück.

    :param path: Pfad zu der zu ladenden Datei
    :returns: ChordFile-Objekt
    :raises TitleNotFoundError: Wenn die gewünschte Datei keinen passenden
                                Titel ("# Titel - Artist") enthält
    """

    with path.open() as fl:
        header: list[str] = []
        line = ""

        for line in fl.readlines():
            if line.startswith("# "):
                break
            header.append(line)
        # Raise exception if we reached end of file
        else:
            raise TitleNotFoundError(path)

    tags: set[str] = set(re.findall(r"\s#(\w+)", "\n".join(header)))

    # Raise exception if first caption does not satisfy title-header formatting
    if not (meta := re.match(r"#\s*(.+) ~ (.+)", line)):
        raise TitleNotFoundError(path)

    return ChordFile(meta[1].strip(), meta[2].strip(), path, tags)


def __include_file(
        chord_file: ChordFile,
        exclude_tags: set[str] | None) -> bool:
    """
    Gibt True zurück, wenn exclude_tags nicht gesetzt oder nicht in chord_file
    enthalten ist.
    
    :param chord_file:      ChordFile-Objekt, das durchsucht werden soll
    :param exclude_tags:    Optional, Liste von Tags, die nicht in chord_file
                            enthalten sein sollen
    :returns:               Boolean, True, wenn keiner der Tags in der Datei
                            enthalten sind.
    """
    return exclude_tags is None or set(exclude_tags).isdisjoint(chord_file.tags)


def __get_by_index_file(
        index_file_name: Path,
        vault_dir: Path,
        exclude_tags: set[str] | None) -> list[ChordFile]:

    """
    Selektiert alle Dateien, die als Obsidian-Wiki-Links in `index_file_name`
    enthalten sind

    :param index_file_name: Pfad zu einer Datei, die Links zu allen anderen
                            Dateien enthält, in denen die gewünschten Songs
                            stehen
    :param vault_dir:       Pfad zum Obsidian-Verzeichnis
    :param exclude_tags:    Optional, Liste von Tags in Dateien, die exkludiert
                            werden sollen

    :returns:               Liste von ChordFile-Objekten
    """

    result: list[ChordFile] = []

    # Select all links as titles to load
    file_names = re.findall(
        r"\[\[(.+?)[\|\]]",
        index_file_name.read_text())

    build_path: Callable[[Path], Path] = lambda f: \
            (vault_dir / f).with_suffix(".md")

    for path in map(build_path, file_names):
        if not path.exists():
            print(f"[!!] File '{path}' does not exists, skipping...")
            continue

        try:
            chord_file = __read_meta(path)
        except TitleNotFoundError as e:
            print(f"[!!] {e}, skipping...")
            continue

        if __include_file(chord_file, exclude_tags): 
            result.append(chord_file)

    return result


def __get_by_tags(
        search_tags: set[str],
        vault_dir: Path,
        exclude_tags: set[str] | None) -> list[ChordFile]:
    """
    Selektiert Dateien anhand von Tags in der Obsidian-Frontmatter

    :param search_tags:     Liste von Tags in Dateien, die inkludiert
                            werden sollen
    :param vault_dir:       Obsidian-Verzeichnis, das durchsucht werden soll
    :param exclude_tags:    optional, Liste von Tags in Dateien, die
                            ausgeschlossen werden sollen

    :returns:               Liste von ChordFile-Objekten
    """

    result: list[ChordFile] = []

    for path in vault_dir.glob("*.md"):
        try:
            chord_file = __read_meta(path)
        except TitleNotFoundError as e:
            print(f"[!!] {e}, skipping...")
            continue

        if search_tags & chord_file.tags \
                and __include_file(chord_file, exclude_tags):
            result.append(chord_file)

    return result


def collect(
        vault_dir: Path,
        index_file: Path | None = None,
        search_tags: set[str] | None = None,
        exclude_tags: set[str] | None = None) -> list[ChordFile]:

    """
    Get processing queue either by index file or by tag-names

    :param vault_dir:       Obsidian-Verzeichnis mit *.md-Dateien pro Song
    :param index_file:      optional, Datei mit Obsidian-Wiki-Links zu den 
                            gewünschten Songs
    :param search_tags:     optional, Liste von Tags in den md-Dateien, die
                            inkludiert werden sollen
    :param exclude_tags:    optional, Liste von Tags in den md-Dateien, die
                            ausgeschlossen werden sollen.

    :returns:               Liste mit ChordFile-Objekten
    """

    results: list[ChordFile] = []

    if index_file is not None:
        results = __get_by_index_file(index_file, vault_dir, exclude_tags)

    elif search_tags is not None:
        results = __get_by_tags(search_tags, vault_dir, exclude_tags)
        results.sort(key=lambda f: f.artist)
        results.sort(key=lambda f: f.title)

    else:
        print("[!!] Either an Index-File or tags must be provided")

    return results
