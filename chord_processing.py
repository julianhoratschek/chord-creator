# pyright: reportUnusedCallResult=false

import re
from dataclasses import dataclass
from typing import NamedTuple, override
from pathlib import Path

import chord_files


# Define Constants


NOTES_PATTERN = "[CDEFGAHB][#b]?"
CHORD_PATTERN= re.compile(
    f"{NOTES_PATTERN}m?"                      +   # Major/Minor Chords
    r"(?:maj|Maj|M|^|aug|dim|°)?[( ,\-+b#\d)]*" +   # Major 7
    r"(?:sus\d+|add\d+)*"       +   # Sus
    f"(?:/{NOTES_PATTERN})?")       # Bass

LEADSHEET_OPTIONS = ["align-chords=l"]

TEX_HEADER = r"""\documentclass{article}
\usepackage{fontspec}
\usepackage{leadsheets}

\setmainfont{0xProtoNerdFontMono-Regular.ttf}[
    Path=fonts/,
    BoldFont=0xProtoNerdFontMono-Bold.ttf,
    ItalicFont=0xProtoNerdFontMono-Italic.ttf
]

\defineversetypetemplate{custom}
{%
    \setleadsheets{verse/named, chords/format={\bfseries}}
    \ifversestarred{}{%
        \noindent\textbf\verselabel\newline\newline
    }
}
{\newline}
"""


# Module Helper Functions


def indent_string(s: str, indent: int) -> str:
    tab = "    " * indent
    return ("\n" + tab).join(s.splitlines())


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
    # TODO: process single chord lines
    chords: list[ChordPosition]


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
        return indent_string(
f"""
\\begin{{song}}[remember-chords]{{%
    title={{{self.title}}},
    music={{{self.artist}}}
}}
{'\n'.join(map(lambda section: section.latex(indent), self.sections))}
\\end{{song}}

\\pagebreak
""", indent)


# Module Function Definitions


def get_chords(line: str) -> list[ChordPosition]:
    """Extract chords and positions from a line, if present"""

    result = [
        ChordPosition(chord.start(), chord[0].rstrip())
        for chord in CHORD_PATTERN.finditer(line)
    ]

    if not result:
        return []

    # TODO: Better checker
    check = line.split()
    if len(check) != len(result):
        print(f"[ii] Inconsistent:\n{result}\n{check}")
        return []

    return result


def merge_lines(line: str, chord_line: ChordLine) -> TextLine:
    """Insert chords into a line at the correct positions"""

    chord_pos = iter(chord_line.chords)
    line_end = len(line)
    pos, chord = next(chord_pos, (line_end, None))
    result = line[:pos]

    while chord:
        last_pos, ins_str = pos, f"^{{{chord}}}"
        pos, chord = next(chord_pos, (line_end, None))
        result += ins_str + line[last_pos:pos]

        if chord is not None and pos >= line_end:
            result += f" ^{{{chord}}} "
            result += " ".join(map(lambda x: f"^{{{x[1]}}}", chord_pos))
            break

    return TextLine(result)


def get_sections(chord_file: chord_files.ChordFile) -> list[Section]:
    """Separate sections (verse, chorus, interlude etc.) in a file
    Sections are marked as 2nd tier headings"""

    result: list[Section] = []

    # Pointer to current section lines list
    section_lines = None

    for line in chord_file.path.read_text().splitlines():
        if line.strip() == "":
            continue

        if section_title := re.match(r"^##\s+(.+)", line):
            result.append(Section(section_title[1].rstrip().lower(), []))
            section_lines = result[-1].lines
            continue
        
        if section_lines is None:
            continue

        if (chords := get_chords(line)):
            append_line = ChordLine(line, chords)
        elif section_lines and isinstance(section_lines[-1], ChordLine):
            append_line = merge_lines(line, section_lines.pop())
        else:
            append_line = TextLine(line)

        section_lines.append(append_line)

    return result


def build_song(chord_file: chord_files.ChordFile) -> Song:
    """Convenienve-method to put together song class"""

    sections = get_sections(chord_file)
    return Song(chord_file.title, chord_file.artist, sections)


def print_songs(file_name: Path, songs: list[Song]):
    section_names = {name for song in songs for name in song.section_names()}
    section_params = [f"{name}/template=custom, {name}/named" for name in section_names]

    file_name.parent.mkdir(parents=True, exist_ok=True)

    file_name.write_text(f"""
{TEX_HEADER}

\\setleadsheets{{%
    {', '.join(LEADSHEET_OPTIONS)},
    {',\n    '.join(section_params)}
}}

\\begin{{document}}
{'\n'.join(map(lambda song: song.latex(1), songs))}
\\end{{document}}""")
