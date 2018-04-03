# Rebound
[![license](https://img.shields.io/github/license/mashape/apistatus.svg)](https://github.com/shobrook/BitVision/blob/master/LICENSE)
![build](https://img.shields.io/shippable/5444c5ecb904a4b21567b0ff.svg)
![status](https://img.shields.io/pypi/status/Django.svg)

Rebound automatically displays Stack Overflow search results in your terminal whenever you get a compiler error. Just use the `rebound` command before the file you want to execute.

![Placeholder Demo](demo.gif)

## Usage

Compiling a file with `rebound` is just as easy as running it normally: 

`$ rebound [file_name]`

This will execute the file, pull the error message, and allow you to browse related Stack Overflow questions/answers without leaving the terminal. <!--Here's an example:-->

__Supported file types:__ Python, Node.js, Ruby, and Java.

## Installation

You can install rebound with pip:

`$ pip install rebound-cli`

Requires Python 2.0 or higher. MacOS, Linux, and Windows are all supported.

## Dependencies

Rebound is written in Python and built on Urwid. Beautiful Soup is used to scrape Stack Overflow content and subprocess for catching compiler errors.

## Contributing

To make a contribution, fork the repo, make your changes and then submit a pull request. If you've discovered a bug or have a feature request, create an [issue](https://github.com/shobrook/rebound/issues/new) and tag it appropriately :)

## Acknowledgements

Special thanks to [@rndusr](https://github.com/rndusr) for helping with the scrollbar and [@alichtman](https://github.com/alichtman) for helping build the test suite.
