# Rebound
Rebound automatically displays Stack Overflow search results in your terminal when you get a compiler error. Just use the `rebound` command before the file you want to execute.

![Placeholder Demo](img/demo.gif)

## Installation

You can install rebound with pip (homebrew coming soon):

`$ pip install rebound-cli`

Requires Python 2.0 or higher. OS X, Linux, and Windows are all supported.

## Usage

Compiling a file with rebound is as simple as doing it normally. Just run:

`$ rebound [file_name]`

This will execute the file, catch any compiler errors, and prompt you to browse related Stack Overflow questions/answers. 

__Supported file types:__ Python, Node.js, Ruby, and Java.

## Contributing

Rebound is written in Python and built on Urwid. Beautiful Soup is used to scrape Stack Overflow content and subprocess is used to catch compiler errors.

To make a contribution, fork the repo, make your changes and then submit a pull request. If you've discovered a bug or have a feature request, create an [issue](https://github.com/shobrook/rebound/issues/new) and tag it appropriately.

## Acknowledgements

Special thanks to [@alichtman](https://github.com/alichtman) for providing helpful feedback.
