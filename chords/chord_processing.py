# pyright: reportUnusedCallResult=false

import re
from dataclasses import dataclass
from typing import NamedTuple, override, Callable
from pathlib import Path

from .chord_files import ChordFile


# Define Constants


NOTES_PATTERN = "[CDEFGAHB][#b]?"
CHORD_PATTERN= re.compile(
    f"{NOTES_PATTERN}m?"                +
    r"(?:maj|Maj|M|^|aug|dim|°|o|\\o)?" +
    r"[( ,\-+b#\d)]*"                   +
    r"(?:sus\d+|add\d+)*"               +
    f"(?:/{NOTES_PATTERN})?"            +
    r"\*?")

LEADSHEET_OPTIONS = [
    "align-chords=l",
    "verses-format=\\footnotesize",
    "chords/format={\\bfseries}"]

TEX_HEADER = r"""\documentclass{article}
\usepackage{fontspec}
\usepackage{leadsheets}

% My personal preferences regarding fonts
\setmainfont{0xProtoNerdFontMono-Regular.ttf}[
    Path=fonts/,
    BoldFont=0xProtoNerdFontMono-Bold.ttf,
    ItalicFont=0xProtoNerdFontMono-Italic.ttf
]

\defineversetypetemplate{custom}
{%
    \ifversestarred{}{%
        \noindent\footnotesize\textbf\versename\newline
    }
}
{\newline}
"""

# Module Helper Functions


def indent_string(s: str, indent: int, indent_char: str = "    ") -> str:
    tab = indent_char * indent
    return (f"\n{tab}").join(s.splitlines())


# Error Definitions


class UnknownChordError(Exception):
    def __init__(self, chord_list: set[str]):
        super().__init__(f"Encountered unknown chords: {', '.join(chord_list)}")


# Module Class Definitions


class ChordPosition(NamedTuple):
    pos: int
    chord: str


@dataclass
class TextLine:
    text: str

    @override
    def __str__(self) -> str:
        return self.text


@dataclass
class ChordLine(TextLine):
    chords: list[ChordPosition]

    @override
    def __str__(self) -> str:
        return " ".join(map(lambda chord: f"^{{{chord.chord}}}", self.chords))


@dataclass
class Section:
    name: str
    lines: list[TextLine | ChordLine]

    def latex(self, indent: int = 0) -> str:
        name = self.name.lower()
        lines = indent_string(
            " \\\\\n".join(map(str, self.lines)),
            indent)

        return indent_string(
f"""
\\begin{{{name}}}
    {lines}
\\end{{{name}}}
""", indent)


@dataclass
class Song:
    title: str
    artist: str
    sections: list[Section]

    def section_names(self) -> set[str]:
        return {section.name for section in self.sections}

    def latex(self, indent: int = 0) -> str:
        sect_list = '\n'.join(
            [s.latex(indent) for s in self.sections])

        return indent_string(
f"""
\\begin{{song}}{{%
    title={{{self.title}}},
    music={{{self.artist}}}
}}
{sect_list}
\\end{{song}}

\\pagebreak
""", indent)


# Module Function Definitions


def __get_chords(line: str) -> list[ChordPosition]:
    """
    Liest die Akkorde einer Zeile ein
    :param line: Aus z.B. einer Datei gelesene Zeile
    :returns: Liste von ChordPosition oder eine leere Liste, falls es sich nicht
              um eine reine Akkord-Zeile handelt
    :raises: UnknownChordError, if an unknown chord was encountered
    """

    result = [
        ChordPosition(chord.start(), chord[0].rstrip())
        for chord in CHORD_PATTERN.finditer(line)
    ]

    if not result:
        return []

    check = line.split()
    if len(check) > len(result):
        # Make sure, unknown chords really don't match with out pattern and
        # this isn't just mistaking a text-file for a chord-file by matching
        # parts of words
        # TODO: any good checker?
        # unknown_chords = { chord
        #     for chord in set(check) if CHORD_PATTERN.match(chord)
        # } - { chord_pos.chord for chord_pos in set(result) }
        #
        # if unknown_chords:
        #     raise UnknownChordError(unknown_chords)
        return []

    return result


def __merge_lines(line: str, chord_line: ChordLine) -> TextLine:
    """
    Fügt alle Akkorde in `chord_line` als Latex (leadsheets-package) in
    `line` an entsprechender Position ein.

    :param line:        Text-Line
    :param chord_line:  Geladene Akkorde

    :returns: TextLine-Objekt mit allen eingefügten Akkorden
    """

    chord_pos = iter(chord_line.chords)
    line_end = len(line)
    pos, chord = next(chord_pos, (line_end, None))
    result = line[:pos]

    while chord:
        last_pos, ins_str = pos, f"^{{{chord}}}"
        pos, chord = next(chord_pos, (line_end, None))
        result += ins_str + line[last_pos:pos]

        # Fill in "overhanging" Chords
        if chord is not None and pos >= line_end:
            result += f" ^{{{chord}}} "
            result += " ".join(map(lambda x: f"^{{{x[1]}}}", chord_pos))
            break

    return TextLine(result)


def __get_sections(chord_file: ChordFile) -> list[Section]:
    """
    Lese alle Sections aus `chord_file` (Verse, Chorus, Intermezzo etc.) und
    prozessiere Chord-Lines in chord_file.

    :param chord_file: ChordFile Objekt

    :returns: Liste der gefundenen und prozessierten Sections
    """

    result: list[Section] = []

    # Pointer to current section lines list
    section_lines = None

    for iline, line in enumerate(chord_file.path.read_text().splitlines()):
        if line.strip() == "":
            continue

        # Find "second header" as Section-start
        if section_title := re.match(r"^##\s+([\w\-]+)", line):
            new_section = Section(
                section_title[1].rstrip().lower().replace("-", ""), [])
            result.append(new_section)
            section_lines = new_section.lines
            continue
        
        # Skip everything up to the first section
        if section_lines is None:
            continue

        try:
            chords = __get_chords(line)

        except UnknownChordError as e:
            print(f"[!!] {e}\n\tIn File {chord_file.path}, line {iline}")
            chords: list[ChordPosition] = []

        if chords:
            append_line = ChordLine(line, chords)

        elif (section_lines
              and isinstance(section_lines[-1], ChordLine)):
            append_line = __merge_lines(line, section_lines.pop())

        else:
            append_line = TextLine(line)

        section_lines.append(append_line)

    return result


def build_song(chord_file: ChordFile) -> Song:
    """
    Fasst alle Sections in `chord_file` zusammen und gibt einen Song zurück

    :param chord_file: Geladene chord_file

    :returns: Song-Objekt aus der chord_file
    """

    return Song(
        chord_file.title,
        chord_file.artist,
        __get_sections(chord_file))


def write_songs(file_name: Path, songs: list[Song]):
    """
    Schreibt alle Songs in `songs` in die Datei `file_name`

    :param file_name: Pfad zu der zu schreibenden Datei
    :param songs:       Liste von Songs, die geschrieben werden sollen

    :returns: Integer, Anzahl der geschriebenen Bytes
    """

    section_names = {name for song in songs for name in song.section_names()}
    section_params = [f"{name}/template=custom, {name}/named" for name in section_names]

    file_name.parent.mkdir(parents=True, exist_ok=True)

    return file_name.write_text(f"""
{TEX_HEADER}

\\setleadsheets{{%
    {', '.join(LEADSHEET_OPTIONS)},
    {',\n    '.join(section_params)}
}}

\\begin{{document}}
{'\n'.join(map(lambda song: song.latex(1), songs))}
\\end{{document}}""")
