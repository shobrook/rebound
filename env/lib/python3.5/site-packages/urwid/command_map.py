#!/usr/bin/python
#
# Urwid CommandMap class
#    Copyright (C) 2004-2011  Ian Ward
#
#    This library is free software; you can redistribute it and/or
#    modify it under the terms of the GNU Lesser General Public
#    License as published by the Free Software Foundation; either
#    version 2.1 of the License, or (at your option) any later version.
#
#    This library is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#    Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public
#    License along with this library; if not, write to the Free Software
#    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
# Urwid web site: http://excess.org/urwid/

from __future__ import division, print_function

REDRAW_SCREEN = 'redraw screen'
CURSOR_UP = 'cursor up'
CURSOR_DOWN = 'cursor down'
CURSOR_LEFT = 'cursor left'
CURSOR_RIGHT = 'cursor right'
CURSOR_PAGE_UP = 'cursor page up'
CURSOR_PAGE_DOWN = 'cursor page down'
CURSOR_MAX_LEFT = 'cursor max left'
CURSOR_MAX_RIGHT = 'cursor max right'
ACTIVATE = 'activate'

class CommandMap(object):
    """
    dict-like object for looking up commands from keystrokes

    Default values (key: command)::

        'tab':       'next selectable',
        'ctrl n':    'next selectable',
        'shift tab': 'prev selectable',
        'ctrl p':    'prev selectable',
        'ctrl l':    'redraw screen',
        'esc':       'menu',
        'up':        'cursor up',
        'down':      'cursor down',
        'left':      'cursor left',
        'right':     'cursor right',
        'page up':   'cursor page up',
        'page down': 'cursor page down',
        'home':      'cursor max left',
        'end':       'cursor max right',
        ' ':         'activate',
        'enter':     'activate',
    """
    _command_defaults = {
        'tab': 'next selectable',
        'ctrl n': 'next selectable',
        'shift tab': 'prev selectable',
        'ctrl p': 'prev selectable',
        'ctrl l': REDRAW_SCREEN,
        'esc': 'menu',
        'up': CURSOR_UP,
        'down': CURSOR_DOWN,
        'left': CURSOR_LEFT,
        'right': CURSOR_RIGHT,
        'page up': CURSOR_PAGE_UP,
        'page down': CURSOR_PAGE_DOWN,
        'home': CURSOR_MAX_LEFT,
        'end': CURSOR_MAX_RIGHT,
        ' ': ACTIVATE,
        'enter': ACTIVATE,
    }

    def __init__(self):
        self.restore_defaults()

    def restore_defaults(self):
        self._command = dict(self._command_defaults)

    def __getitem__(self, key):
        return self._command.get(key, None)

    def __setitem__(self, key, command):
        self._command[key] = command

    def __delitem__(self, key):
        del self._command[key]

    def clear_command(self, command):
        dk = [k for k, v in self._command.items() if v == command]
        for k in dk:
            del self._command[k]

    def copy(self):
        """
        Return a new copy of this CommandMap, likely so we can modify
        it separate from a shared one.
        """
        c = CommandMap()
        c._command = dict(self._command)
        return c

command_map = CommandMap() # shared command mappings
