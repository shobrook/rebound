# rebound

Rebound is a command-line tool that instantly fetches Stack Overflow results when you get a compiler error. Just use the `rebound` command to execute your file.

![Placeholder Demo](docs/demo.gif)

__Featured in:__ [50 Most Popular Python Projects in 2018](https://boostlog.io/@bily809/50-most-popular-python-projects-in-2018-5aea8e1c47018500491f4361), the top of [r/Python](https://www.reddit.com/r/Python/comments/8cwq72/i_made_a_commandline_tool_that_instantly_fetches/), [awesome-cli-apps](https://github.com/agarrharr/awesome-cli-apps), [awesome-shell](https://github.com/alebcay/awesome-shell), [terminals-are-sexy](https://github.com/k4m4/terminals-are-sexy), and [awesome-mac](https://github.com/jaywcjlove/awesome-mac).

## Installation

>Requires Python 3.0 or higher.

Rebound works on MacOS, Linux, and Windows (if you use Cygwin), with binary downloads available for [every release.](https://github.com/shobrook/rebound/releases) You can also install it with pip:

`$ pip install rebound-cli`
or
`$ pip3 install rebound-cli`

or apt-get if you're using Linux:

`$ sudo apt-get install rebound-cli`

## Usage

Running a file with `rebound` is just as easy as compiling it normally:

`$ rebound [file_path]`

This will execute the file, pull the error message, and let you browse related Stack Overflow questions and answers without leaving the terminal.

__Supported file types:__ Python, Node.js, Ruby, Golang, and Java.

## Contributing

To make a contribution, fork the repo, make your changes and then submit a pull request. Please try to adhere to the existing style. If you've discovered a bug or have a feature request, create an [issue](https://github.com/shobrook/rebound/issues/new) and I'll take care of it!

__Pending Features:__
* Improved text formatting (i.e. for duplicate questions, markdown, blockquotes, clickable links, etc.)
* Improved search result accuracy by extracting potential search terms from the stack trace
* Support for more languages

## Technologies

Rebound is written in Python and built on Urwid. Beautiful Soup is used to scrape Stack Overflow content and subprocess for catching compiler errors.

## Acknowledgements

Special thanks to [@rndusr](https://github.com/rndusr) for helping with the scrollbar.
