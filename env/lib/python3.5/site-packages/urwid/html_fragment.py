#!/usr/bin/python
#
# Urwid html fragment output wrapper for "screen shots"
#    Copyright (C) 2004-2007  Ian Ward
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

"""
HTML PRE-based UI implementation
"""

from urwid import util
from urwid.main_loop import ExitMainLoop
from urwid.display_common import AttrSpec, BaseScreen


# replace control characters with ?'s
_trans_table = "?" * 32 + "".join([chr(x) for x in range(32, 256)])

_default_foreground = 'black'
_default_background = 'light gray'

class HtmlGeneratorSimulationError(Exception):
    pass

class HtmlGenerator(BaseScreen):
    # class variables
    fragments = []
    sizes = []
    keys = []
    started = True

    def __init__(self):
        super(HtmlGenerator, self).__init__()
        self.colors = 16
        self.bright_is_bold = False # ignored
        self.has_underline = True # ignored
        self.register_palette_entry(None,
            _default_foreground, _default_background)

    def set_terminal_properties(self, colors=None, bright_is_bold=None,
        has_underline=None):

        if colors is None:
            colors = self.colors
        if bright_is_bold is None:
            bright_is_bold = self.bright_is_bold
        if has_underline is None:
            has_underline = self.has_underline

        self.colors = colors
        self.bright_is_bold = bright_is_bold
        self.has_underline = has_underline

    def set_mouse_tracking(self, enable=True):
        """Not yet implemented"""
        pass

    def set_input_timeouts(self, *args):
        pass

    def reset_default_terminal_palette(self, *args):
        pass

    def draw_screen(self, size, r ):
        """Create an html fragment from the render object.
        Append it to HtmlGenerator.fragments list.
        """
        # collect output in l
        l = []

        cols, rows = size

        assert r.rows() == rows

        if r.cursor is not None:
            cx, cy = r.cursor
        else:
            cx = cy = None

        y = -1
        for row in r.content():
            y += 1
            col = 0

            for a, cs, run in row:
                if not str is bytes:
                    run = run.decode()
                run = run.translate(_trans_table)
                if isinstance(a, AttrSpec):
                    aspec = a
                else:
                    aspec = self._palette[a][
                        {1: 1, 16: 0, 88:2, 256:3}[self.colors]]

                if y == cy and col <= cx:
                    run_width = util.calc_width(run, 0,
                        len(run))
                    if col+run_width > cx:
                        l.append(html_span(run,
                            aspec, cx-col))
                    else:
                        l.append(html_span(run, aspec))
                    col += run_width
                else:
                    l.append(html_span(run, aspec))

            l.append("\n")

        # add the fragment to the list
        self.fragments.append( "<pre>%s</pre>" % "".join(l) )

    def clear(self):
        """
        Force the screen to be completely repainted on the next
        call to draw_screen().

        (does nothing for html_fragment)
        """
        pass

    def get_cols_rows(self):
        """Return the next screen size in HtmlGenerator.sizes."""
        if not self.sizes:
            raise HtmlGeneratorSimulationError("Ran out of screen sizes to return!")
        return self.sizes.pop(0)

    def get_input(self, raw_keys=False):
        """Return the next list of keypresses in HtmlGenerator.keys."""
        if not self.keys:
            raise ExitMainLoop()
        if raw_keys:
            return (self.keys.pop(0), [])
        return self.keys.pop(0)

_default_aspec = AttrSpec(_default_foreground, _default_background)
(_d_fg_r, _d_fg_g, _d_fg_b, _d_bg_r, _d_bg_g, _d_bg_b) = (
    _default_aspec.get_rgb_values())

def html_span(s, aspec, cursor = -1):
    fg_r, fg_g, fg_b, bg_r, bg_g, bg_b = aspec.get_rgb_values()
    # use real colours instead of default fg/bg
    if fg_r is None:
        fg_r, fg_g, fg_b = _d_fg_r, _d_fg_g, _d_fg_b
    if bg_r is None:
        bg_r, bg_g, bg_b = _d_bg_r, _d_bg_g, _d_bg_b
    html_fg = "#%02x%02x%02x" % (fg_r, fg_g, fg_b)
    html_bg = "#%02x%02x%02x" % (bg_r, bg_g, bg_b)
    if aspec.standout:
        html_fg, html_bg = html_bg, html_fg
    extra = (";text-decoration:underline" * aspec.underline +
        ";font-weight:bold" * aspec.bold)
    def html_span(fg, bg, s):
        if not s: return ""
        return ('<span style="color:%s;'
            'background:%s%s">%s</span>' %
            (fg, bg, extra, html_escape(s)))

    if cursor >= 0:
        c_off, _ign = util.calc_text_pos(s, 0, len(s), cursor)
        c2_off = util.move_next_char(s, c_off, len(s))
        return (html_span(html_fg, html_bg, s[:c_off]) +
            html_span(html_bg, html_fg, s[c_off:c2_off]) +
            html_span(html_fg, html_bg, s[c2_off:]))
    else:
        return html_span(html_fg, html_bg, s)


def html_escape(text):
    """Escape text so that it will be displayed safely within HTML"""
    text = text.replace('&','&amp;')
    text = text.replace('<','&lt;')
    text = text.replace('>','&gt;')
    return text

def screenshot_init( sizes, keys ):
    """
    Replace curses_display.Screen and raw_display.Screen class with
    HtmlGenerator.

    Call this function before executing an application that uses
    curses_display.Screen to have that code use HtmlGenerator instead.

    sizes -- list of ( columns, rows ) tuples to be returned by each call
             to HtmlGenerator.get_cols_rows()
    keys -- list of lists of keys to be returned by each call to
            HtmlGenerator.get_input()

    Lists of keys may include "window resize" to force the application to
    call get_cols_rows and read a new screen size.

    For example, the following call will prepare an application to:
     1. start in 80x25 with its first call to get_cols_rows()
     2. take a screenshot when it calls draw_screen(..)
     3. simulate 5 "down" keys from get_input()
     4. take a screenshot when it calls draw_screen(..)
     5. simulate keys "a", "b", "c" and a "window resize"
     6. resize to 20x10 on its second call to get_cols_rows()
     7. take a screenshot when it calls draw_screen(..)
     8. simulate a "Q" keypress to quit the application

    screenshot_init( [ (80,25), (20,10) ],
        [ ["down"]*5, ["a","b","c","window resize"], ["Q"] ] )
    """
    try:
        for (row,col) in sizes:
            assert type(row) == int
            assert row>0 and col>0
    except (AssertionError, ValueError):
        raise Exception("sizes must be in the form [ (col1,row1), (col2,row2), ...]")

    try:
        for l in keys:
            assert type(l) == list
            for k in l:
                assert type(k) == str
    except (AssertionError, ValueError):
        raise Exception("keys must be in the form [ [keyA1, keyA2, ..], [keyB1, ..], ...]")

    from . import curses_display
    curses_display.Screen = HtmlGenerator
    from . import raw_display
    raw_display.Screen = HtmlGenerator

    HtmlGenerator.sizes = sizes
    HtmlGenerator.keys = keys


def screenshot_collect():
    """Return screenshots as a list of HTML fragments."""
    l = HtmlGenerator.fragments
    HtmlGenerator.fragments = []
    return l


