# pyright: reportUnusedCallResult=false

import argparse
from pathlib import Path

import chord_files
import chord_processing


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog = "chord_creator",
        description = "A small program to convert Markdown-chord-sheets into a latex-file")

    # Exclusive Group

    file_tags_group = parser.add_mutually_exclusive_group()

    file_tags_group.add_argument(
        "-t", "--tags",
        action = "extend", nargs = "+",
        help = "list of tags to search for when selecting songs to print (needs to define --vault-dir)")

    file_tags_group.add_argument(
        "-f", "--index-file",
        action = "store", type = Path,
        help = "file with list(s) of song files to select")

    # Simple Parameters

    parser.add_argument(
        "-e", "--exclude-tags",
        action = "extend", nargs = "+", default = [],
        help = "tags to exclude from selection")

    parser.add_argument(
        "-o", "--output-file",
        nargs = 1, default = None, type = Path,
        help = "name of the output-file including extension")

    parser.add_argument(
        "-v", "--vault-dir",
        nargs = 1, default = None, type = Path,
        help = "vault to read all files from (needed in combination with --tags)")

    # Set complex defaults

    args = parser.parse_args()
    if args.output_file is None:
        if args.index_file is not None:
            args.output_file = Path(args.index_file).with_suffix(".latex")
        else:
            print("[!!] Either an --output or at least a --file argument must be present")
            exit(0)

    if args.vault_dir is None:
        if args.index_file is not None:
            args.vault_dir = Path(args.index_file.parent)
        else:
            print("[!!] Need to define a vault-dir if no index-file is given")
            exit(0)

    return args


if __name__ == "__main__":
    args = parse_arguments()

    songs = [chord_processing.build_song(file)
        for file in chord_files.collect(
            vault_dir       = args.vault_dir,
            index_file      = args.index_file,
            search_tags     = args.tags,
            exclude_tags    = set(args.exclude_tags))]

    if songs:
        chord_processing.print_songs(args.output_file, songs)


