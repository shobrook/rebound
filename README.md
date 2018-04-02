# Rebound
[![license](https://img.shields.io/github/license/mashape/apistatus.svg)](https://github.com/shobrook/BitVision/blob/master/LICENSE)
[![build](https://img.shields.io/wercker/ci/wercker/docs.svg)]()

Rebound automatically displays Stack Overflow search results in your terminal when you get a compiler error. Just use the `rebound` command before the file you want to execute.

![Placeholder Demo](demo.gif)

## Installation

You can install rebound with pip (homebrew coming soon):

`$ pip install rebound-cli`

Requires Python 2.0 or higher. OS X, Linux, and Windows are all supported.

## Usage

Compiling a file with rebound is as simple as doing it normally. Just run:

`$ rebound [file_name]`

This will execute the file, pull the error message, and allow you to browse related Stack Overflow questions/answers without leaving the terminal.

__Supported file types:__ Python, Node.js, Ruby, and Java.

## Contributing

To make a contribution, fork the repo, make your changes and then submit a pull request. If you've discovered a bug or have a feature request, create an [issue](https://github.com/shobrook/rebound/issues/new) and tag it appropriately :)

Rebound is written in Python and built on Urwid. Beautiful Soup is used to scrape Stack Overflow content and subprocess for catching compiler errors.

## Acknowledgements

Special thanks to [@rndusr](https://github.com/rndusr) for helping with the scrollbar.
