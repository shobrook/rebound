# Rebound
[![license](https://img.shields.io/github/license/mashape/apistatus.svg)](https://github.com/shobrook/BitVision/blob/master/LICENSE)
[![build](https://img.shields.io/wercker/ci/wercker/docs.svg)]()

`rebound` automatically displays Stack Overflow search results in your terminal when you get a compiler error. Just use the `rebound` command before the file you want to execute.

![Placeholder Demo](demo.gif)

## Usage

Compiling a file with `rebound` is as simple as running it normally. Just run:

`$ rebound [file_name]`

`rebound` will execute the file, pull the error message, and allow you to browse related Stack Overflow questions and answers without leaving the terminal.

**Supported file types**
+ Python
+ Node.js
+ Ruby
+ Java

## Installation

You can install `rebound` with `pip` (`homebrew` coming soon):

`$ pip install rebound-cli`

Requires `Python 2.0` or higher. `MacOS`, `Linux`, and `Windows` are all supported.

## Dependencies

Rebound is written in `Python`.

+ [Urwid](http://urwid.org/) is used to format the CLI.
+ [Beautiful Soup](https://www.crummy.com/software/BeautifulSoup/) is used to scrape Stack Overflow content
+ [Subprocess](https://docs.python.org/3/library/subprocess.html) is used to catch compiler errors.

## Contributing

To make a contribution:
1. Fork the repo.
2. Make your changes.
3. Submit a pull request.

If you've discovered a bug or have a feature request:
1. Create an [issue](https://github.com/shobrook/rebound/issues/new).
2. Tag it appropriately.

## Acknowledgements

Special thanks to:

1. [@rndusr](https://github.com/rndusr) for helping with the scrollbar.
2. [@alichtman](https://github.com/alichtman) for helping with interface design decisons.
