# Chord-Creator :loud_sound:


## Description :monocle_face:

Simple python script to create full latex songbooks out of a markdown-file
collection of songs (e.g. ab obsidian vault)


## Requirements :package:

- Python 3.12 >=
- Latex-viewer with leadsheets-package
- No other dependencies


## Usage :hammer:

From the commandline invoke

```bash
python main.py [[-f <filename>] | [-t <tag>+]] [-e <tag>+] [-o <outputfile>] [-v <vault-dir>]
```


## Parameters :memo:


| Argument | Name           | Expected value(s)      | Description                                    |
| -------- | -------------- | ---------------------- | ---------------------------------------------- |
| -f       | --index-file   | Input filename         | Path to file to read songlist from             |
| -t       | --tags         | List of Tags           | Tags describing files included in the songlist |
| -e       | --exclude-tags | List of Tags           | Tags describing files excluded from songlist   |
| -o       | --output-file  | Path to Output file    | Write Latex into this file                     |
| -v       | --vault-dir    | Path to Obsidian vault | Look for songfiles in this directory           |


### Index file

- Describes a markdown file with Obsidian Wiki Links: `[[Path-to-File.md|Name]]`
- Each Link will be read and a corresponding file at `--vault-dir` will be opened
- All songs will be read from those files
- Mutually exclusive with `--tags`

### Tags

- Enables the user to define a list of tags
- Each file in `--vault-dir` will be opened and its Obsidian frontmatter will
  be searched for tags
- When any of the defined tags are present, this file will be added to the
  songlist processing
- Mutually exclusive with `--index-file`

### Exclude Tags

- Works as `--tags` but excludes all files that have at least one of the
  defined tags
- Works together with `--index-file`


### Output File

- File to print processed latex code of all songs in the songlist to


### Vault Dir

- Directory to search the markdown (song-) files in
- If not defined, the parent directory of `--index-file` will be used
- Required for use with `--tags`
