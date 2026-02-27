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


def read_meta(path: Path) -> ChordFile:

    """Read Metadata from a basic md-file containing an obsidian frontmatter
    with tags as well as a formatted title-header"""

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

    return ChordFile(meta[1], meta[2], path, tags)


def include_file(chord_file: ChordFile, exclude_tags: set[str] | None) -> bool:
    return exclude_tags is None or set(exclude_tags).isdisjoint(chord_file.tags)


def get_by_index_file(
        index_file_name: Path,
        vault_dir: Path,
        exclude_tags: set[str] | None) -> list[ChordFile]:

    """Read all titles from one index file and add found files to the
    processing queue"""

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
            chord_file = read_meta(path)
        except TitleNotFoundError as e:
            print(f"[!!] {e}, skipping...")
            continue

        if include_file(chord_file, exclude_tags): 
            result.append(chord_file)

    return result


def get_by_tags(
        search_tags: set[str],
        vault_dir: Path,
        exclude_tags: set[str] | None) -> list[ChordFile]:

    """Iterate over all files in vault_dir and determine, if they have
    any tags matching search_tags"""

    result: list[ChordFile] = []

    for path in vault_dir.glob("*.md"):
        try:
            chord_file = read_meta(path)
        except TitleNotFoundError as e:
            print(f"[!!] {e}, skipping...")
            continue

        if search_tags & chord_file.tags \
                and include_file(chord_file, exclude_tags):
            result.append(chord_file)

    return result


def collect(
        vault_dir: Path,
        index_file: Path | None = None,
        search_tags: set[str] | None = None,
        exclude_tags: set[str] | None = None) -> list[ChordFile]:

    """Get processing queue either by index file or by tag-names"""

    results: list[ChordFile] = []

    if index_file is not None:
        results = get_by_index_file(index_file, vault_dir, exclude_tags)

    elif search_tags is not None:
        results = get_by_tags(search_tags, vault_dir, exclude_tags)
        results.sort(key=lambda f: f.artist)
        results.sort(key=lambda f: f.title)

    else:
        print("[!!] Either an Index-File or tags must be provided")

    return results
