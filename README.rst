Rebound
=======

Rebound automatically displays Stack Overflow search results in your
terminal when you get a compiler error. Just use the ``rebound`` command
before the file you want to execute.

.. figure:: img/demo.gif
   :alt: Placeholder Demo

   Placeholder Demo

Installation
------------

You can install rebound with pip (homebrew coming soon):

``$ pip install rebound-cli``

Requires Python 2.0 or higher. OS X, Linux, and Windows are all
supported.

Usage
-----

Compiling a file with rebound is as simple as doing it normally. Just
run:

``$ rebound [file_name]``

This will execute the file, catch any compiler errors, and prompt you to
browse related Stack Overflow questions/answers. Rebound currently
supports Python and NodeJS files. Support for Ruby and Java is coming
soon!

Contributing
------------

Rebound is written in Python and built on Urwid. Beautiful Soup is used
to scrape Stack Overflow content and subprocess is used to catch
compiler errors.

To make a contribution, fork the repo, make
your changes and then submit a pull request. If you’ve discovered a bug
or have a feature request, create an `issue`_ and tag it appropriately.

Acknowledgements
----------------

Special thanks to [@alichtman](https://github.com/alichtman) for
providing helpful feedback.

.. _issue: https://github.com/shobrook/rebound/issues/new
