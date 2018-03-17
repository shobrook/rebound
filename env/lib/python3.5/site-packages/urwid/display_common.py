#!/usr/bin/python
# Urwid common display code
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

import os
import sys

try:
    import termios
except ImportError:
    pass # windows

from urwid.util import StoppingContext, int_scale
from urwid import signals
from urwid.compat import B, bytes3, xrange, with_metaclass

# for replacing unprintable bytes with '?'
UNPRINTABLE_TRANS_TABLE = B("?") * 32 + bytes3(list(xrange(32,256)))


# signals sent by BaseScreen
UPDATE_PALETTE_ENTRY = "update palette entry"
INPUT_DESCRIPTORS_CHANGED = "input descriptors changed"


# AttrSpec internal values
_BASIC_START = 0 # first index of basic color aliases
_CUBE_START = 16 # first index of color cube
_CUBE_SIZE_256 = 6 # one side of the color cube
_GRAY_SIZE_256 = 24
_GRAY_START_256 = _CUBE_SIZE_256 ** 3 + _CUBE_START
_CUBE_WHITE_256 = _GRAY_START_256 -1
_CUBE_SIZE_88 = 4
_GRAY_SIZE_88 = 8
_GRAY_START_88 = _CUBE_SIZE_88 ** 3 + _CUBE_START
_CUBE_WHITE_88 = _GRAY_START_88 -1
_CUBE_BLACK = _CUBE_START

# values copied from xterm 256colres.h:
_CUBE_STEPS_256 = [0x00, 0x5f, 0x87, 0xaf, 0xd7, 0xff]
_GRAY_STEPS_256 = [0x08, 0x12, 0x1c, 0x26, 0x30, 0x3a, 0x44, 0x4e, 0x58, 0x62,
    0x6c, 0x76, 0x80, 0x84, 0x94, 0x9e, 0xa8, 0xb2, 0xbc, 0xc6, 0xd0,
    0xda, 0xe4, 0xee]
# values copied from xterm 88colres.h:
_CUBE_STEPS_88 = [0x00, 0x8b, 0xcd, 0xff]
_GRAY_STEPS_88 = [0x2e, 0x5c, 0x73, 0x8b, 0xa2, 0xb9, 0xd0, 0xe7]
# values copied from X11/rgb.txt and XTerm-col.ad:
_BASIC_COLOR_VALUES = [(0,0,0), (205, 0, 0), (0, 205, 0), (205, 205, 0),
    (0, 0, 238), (205, 0, 205), (0, 205, 205), (229, 229, 229),
    (127, 127, 127), (255, 0, 0), (0, 255, 0), (255, 255, 0),
    (0x5c, 0x5c, 0xff), (255, 0, 255), (0, 255, 255), (255, 255, 255)]

_COLOR_VALUES_256 = (_BASIC_COLOR_VALUES +
    [(r, g, b) for r in _CUBE_STEPS_256 for g in _CUBE_STEPS_256
    for b in _CUBE_STEPS_256] +
    [(gr, gr, gr) for gr in _GRAY_STEPS_256])
_COLOR_VALUES_88 = (_BASIC_COLOR_VALUES +
    [(r, g, b) for r in _CUBE_STEPS_88 for g in _CUBE_STEPS_88
    for b in _CUBE_STEPS_88] +
    [(gr, gr, gr) for gr in _GRAY_STEPS_88])

assert len(_COLOR_VALUES_256) == 256
assert len(_COLOR_VALUES_88) == 88

_FG_COLOR_MASK = 0x000000ff
_BG_COLOR_MASK = 0x0000ff00
_FG_BASIC_COLOR = 0x00010000
_FG_HIGH_COLOR = 0x00020000
_BG_BASIC_COLOR = 0x00040000
_BG_HIGH_COLOR = 0x00080000
_BG_SHIFT = 8
_HIGH_88_COLOR = 0x00100000
_STANDOUT = 0x02000000
_UNDERLINE = 0x04000000
_BOLD = 0x08000000
_BLINK = 0x10000000
_ITALICS = 0x20000000
_STRIKETHROUGH = 0x40000000
_FG_MASK = (_FG_COLOR_MASK | _FG_BASIC_COLOR | _FG_HIGH_COLOR |
    _STANDOUT | _UNDERLINE | _BLINK | _BOLD | _ITALICS | _STRIKETHROUGH)
_BG_MASK = _BG_COLOR_MASK | _BG_BASIC_COLOR | _BG_HIGH_COLOR

DEFAULT = 'default'
BLACK = 'black'
DARK_RED = 'dark red'
DARK_GREEN = 'dark green'
BROWN = 'brown'
DARK_BLUE = 'dark blue'
DARK_MAGENTA = 'dark magenta'
DARK_CYAN = 'dark cyan'
LIGHT_GRAY = 'light gray'
DARK_GRAY = 'dark gray'
LIGHT_RED = 'light red'
LIGHT_GREEN = 'light green'
YELLOW = 'yellow'
LIGHT_BLUE = 'light blue'
LIGHT_MAGENTA = 'light magenta'
LIGHT_CYAN = 'light cyan'
WHITE = 'white'

_BASIC_COLORS = [
    BLACK,
    DARK_RED,
    DARK_GREEN,
    BROWN,
    DARK_BLUE,
    DARK_MAGENTA,
    DARK_CYAN,
    LIGHT_GRAY,
    DARK_GRAY,
    LIGHT_RED,
    LIGHT_GREEN,
    YELLOW,
    LIGHT_BLUE,
    LIGHT_MAGENTA,
    LIGHT_CYAN,
    WHITE,
]

_ATTRIBUTES = {
    'bold': _BOLD,
    'italics': _ITALICS,
    'underline': _UNDERLINE,
    'blink': _BLINK,
    'standout': _STANDOUT,
    'strikethrough': _STRIKETHROUGH,
}

def _value_lookup_table(values, size):
    """
    Generate a lookup table for finding the closest item in values.
    Lookup returns (index into values)+1

    values -- list of values in ascending order, all < size
    size -- size of lookup table and maximum value

    >>> _value_lookup_table([0, 7, 9], 10)
    [0, 0, 0, 0, 1, 1, 1, 1, 2, 2]
    """

    middle_values = [0] + [(values[i] + values[i + 1] + 1) // 2
        for i in range(len(values) - 1)] + [size]
    lookup_table = []
    for i in range(len(middle_values)-1):
        count = middle_values[i + 1] - middle_values[i]
        lookup_table.extend([i] * count)
    return lookup_table

_CUBE_256_LOOKUP = _value_lookup_table(_CUBE_STEPS_256, 256)
_GRAY_256_LOOKUP = _value_lookup_table([0] + _GRAY_STEPS_256 + [0xff], 256)
_CUBE_88_LOOKUP = _value_lookup_table(_CUBE_STEPS_88, 256)
_GRAY_88_LOOKUP = _value_lookup_table([0] + _GRAY_STEPS_88 + [0xff], 256)

# convert steps to values that will be used by string versions of the colors
# 1 hex digit for rgb and 0..100 for grayscale
_CUBE_STEPS_256_16 = [int_scale(n, 0x100, 0x10) for n in _CUBE_STEPS_256]
_GRAY_STEPS_256_101 = [int_scale(n, 0x100, 101) for n in _GRAY_STEPS_256]
_CUBE_STEPS_88_16 = [int_scale(n, 0x100, 0x10) for n in _CUBE_STEPS_88]
_GRAY_STEPS_88_101 = [int_scale(n, 0x100, 101) for n in _GRAY_STEPS_88]

# create lookup tables for 1 hex digit rgb and 0..100 for grayscale values
_CUBE_256_LOOKUP_16 = [_CUBE_256_LOOKUP[int_scale(n, 16, 0x100)]
    for n in range(16)]
_GRAY_256_LOOKUP_101 = [_GRAY_256_LOOKUP[int_scale(n, 101, 0x100)]
    for n in range(101)]
_CUBE_88_LOOKUP_16 = [_CUBE_88_LOOKUP[int_scale(n, 16, 0x100)]
    for n in range(16)]
_GRAY_88_LOOKUP_101 = [_GRAY_88_LOOKUP[int_scale(n, 101, 0x100)]
    for n in range(101)]


# The functions _gray_num_256() and _gray_num_88() do not include the gray
# values from the color cube so that the gray steps are an even width.
# The color cube grays are available by using the rgb functions.  Pure
# white and black are taken from the color cube, since the gray range does
# not include them, and the basic colors are more likely to have been
# customized by an end-user.


def _gray_num_256(gnum):
    """Return ths color number for gray number gnum.

    Color cube black and white are returned for 0 and 25 respectively
    since those values aren't included in the gray scale.

    """
    # grays start from index 1
    gnum -= 1

    if gnum < 0:
        return _CUBE_BLACK
    if gnum >= _GRAY_SIZE_256:
        return _CUBE_WHITE_256
    return _GRAY_START_256 + gnum


def _gray_num_88(gnum):
    """Return ths color number for gray number gnum.

    Color cube black and white are returned for 0 and 9 respectively
    since those values aren't included in the gray scale.

    """
    # gnums start from index 1
    gnum -= 1

    if gnum < 0:
        return _CUBE_BLACK
    if gnum >= _GRAY_SIZE_88:
        return _CUBE_WHITE_88
    return _GRAY_START_88 + gnum


def _color_desc_256(num):
    """
    Return a string description of color number num.
    0..15 -> 'h0'..'h15' basic colors (as high-colors)
    16..231 -> '#000'..'#fff' color cube colors
    232..255 -> 'g3'..'g93' grays

    >>> _color_desc_256(15)
    'h15'
    >>> _color_desc_256(16)
    '#000'
    >>> _color_desc_256(17)
    '#006'
    >>> _color_desc_256(230)
    '#ffd'
    >>> _color_desc_256(233)
    'g7'
    >>> _color_desc_256(234)
    'g11'

    """
    assert num >= 0 and num < 256, num
    if num < _CUBE_START:
        return 'h%d' % num
    if num < _GRAY_START_256:
        num -= _CUBE_START
        b, num = num % _CUBE_SIZE_256, num // _CUBE_SIZE_256
        g, num = num % _CUBE_SIZE_256, num // _CUBE_SIZE_256
        r = num % _CUBE_SIZE_256
        return '#%x%x%x' % (_CUBE_STEPS_256_16[r], _CUBE_STEPS_256_16[g],
            _CUBE_STEPS_256_16[b])
    return 'g%d' % _GRAY_STEPS_256_101[num - _GRAY_START_256]

def _color_desc_88(num):
    """
    Return a string description of color number num.
    0..15 -> 'h0'..'h15' basic colors (as high-colors)
    16..79 -> '#000'..'#fff' color cube colors
    80..87 -> 'g18'..'g90' grays

    >>> _color_desc_88(15)
    'h15'
    >>> _color_desc_88(16)
    '#000'
    >>> _color_desc_88(17)
    '#008'
    >>> _color_desc_88(78)
    '#ffc'
    >>> _color_desc_88(81)
    'g36'
    >>> _color_desc_88(82)
    'g45'

    """
    assert num > 0 and num < 88
    if num < _CUBE_START:
        return 'h%d' % num
    if num < _GRAY_START_88:
        num -= _CUBE_START
        b, num = num % _CUBE_SIZE_88, num // _CUBE_SIZE_88
        g, r= num % _CUBE_SIZE_88, num // _CUBE_SIZE_88
        return '#%x%x%x' % (_CUBE_STEPS_88_16[r], _CUBE_STEPS_88_16[g],
            _CUBE_STEPS_88_16[b])
    return 'g%d' % _GRAY_STEPS_88_101[num - _GRAY_START_88]

def _parse_color_256(desc):
    """
    Return a color number for the description desc.
    'h0'..'h255' -> 0..255 actual color number
    '#000'..'#fff' -> 16..231 color cube colors
    'g0'..'g100' -> 16, 232..255, 231 grays and color cube black/white
    'g#00'..'g#ff' -> 16, 232...255, 231 gray and color cube black/white

    Returns None if desc is invalid.

    >>> _parse_color_256('h142')
    142
    >>> _parse_color_256('#f00')
    196
    >>> _parse_color_256('g100')
    231
    >>> _parse_color_256('g#80')
    244
    """
    if len(desc) > 4:
        # keep the length within reason before parsing
        return None
    try:
        if desc.startswith('h'):
            # high-color number
            num = int(desc[1:], 10)
            if num < 0 or num > 255:
                return None
            return num

        if desc.startswith('#') and len(desc) == 4:
            # color-cube coordinates
            rgb = int(desc[1:], 16)
            if rgb < 0:
                return None
            b, rgb = rgb % 16, rgb // 16
            g, r = rgb % 16, rgb // 16
            # find the closest rgb values
            r = _CUBE_256_LOOKUP_16[r]
            g = _CUBE_256_LOOKUP_16[g]
            b = _CUBE_256_LOOKUP_16[b]
            return _CUBE_START + (r * _CUBE_SIZE_256 + g) * _CUBE_SIZE_256 + b

        # Only remaining possibility is gray value
        if desc.startswith('g#'):
            # hex value 00..ff
            gray = int(desc[2:], 16)
            if gray < 0 or gray > 255:
                return None
            gray = _GRAY_256_LOOKUP[gray]
        elif desc.startswith('g'):
            # decimal value 0..100
            gray = int(desc[1:], 10)
            if gray < 0 or gray > 100:
                return None
            gray = _GRAY_256_LOOKUP_101[gray]
        else:
            return None
        if gray == 0:
            return _CUBE_BLACK
        gray -= 1
        if gray == _GRAY_SIZE_256:
            return _CUBE_WHITE_256
        return _GRAY_START_256 + gray

    except ValueError:
        return None

def _parse_color_88(desc):
    """
    Return a color number for the description desc.
    'h0'..'h87' -> 0..87 actual color number
    '#000'..'#fff' -> 16..79 color cube colors
    'g0'..'g100' -> 16, 80..87, 79 grays and color cube black/white
    'g#00'..'g#ff' -> 16, 80...87, 79 gray and color cube black/white

    Returns None if desc is invalid.

    >>> _parse_color_88('h142')
    >>> _parse_color_88('h42')
    42
    >>> _parse_color_88('#f00')
    64
    >>> _parse_color_88('g100')
    79
    >>> _parse_color_88('g#80')
    83
    """
    if len(desc) > 4:
        # keep the length within reason before parsing
        return None
    try:
        if desc.startswith('h'):
            # high-color number
            num = int(desc[1:], 10)
            if num < 0 or num > 87:
                return None
            return num

        if desc.startswith('#') and len(desc) == 4:
            # color-cube coordinates
            rgb = int(desc[1:], 16)
            if rgb < 0:
                return None
            b, rgb = rgb % 16, rgb // 16
            g, r = rgb % 16, rgb // 16
            # find the closest rgb values
            r = _CUBE_88_LOOKUP_16[r]
            g = _CUBE_88_LOOKUP_16[g]
            b = _CUBE_88_LOOKUP_16[b]
            return _CUBE_START + (r * _CUBE_SIZE_88 + g) * _CUBE_SIZE_88 + b

        # Only remaining possibility is gray value
        if desc.startswith('g#'):
            # hex value 00..ff
            gray = int(desc[2:], 16)
            if gray < 0 or gray > 255:
                return None
            gray = _GRAY_88_LOOKUP[gray]
        elif desc.startswith('g'):
            # decimal value 0..100
            gray = int(desc[1:], 10)
            if gray < 0 or gray > 100:
                return None
            gray = _GRAY_88_LOOKUP_101[gray]
        else:
            return None
        if gray == 0:
            return _CUBE_BLACK
        gray -= 1
        if gray == _GRAY_SIZE_88:
            return _CUBE_WHITE_88
        return _GRAY_START_88 + gray

    except ValueError:
        return None

class AttrSpecError(Exception):
    pass

class AttrSpec(object):
    def __init__(self, fg, bg, colors=256):
        """
        fg -- a string containing a comma-separated foreground color
              and settings

              Color values:
              'default' (use the terminal's default foreground),
              'black', 'dark red', 'dark green', 'brown', 'dark blue',
              'dark magenta', 'dark cyan', 'light gray', 'dark gray',
              'light red', 'light green', 'yellow', 'light blue',
              'light magenta', 'light cyan', 'white'

              High-color example values:
              '#009' (0% red, 0% green, 60% red, like HTML colors)
              '#fcc' (100% red, 80% green, 80% blue)
              'g40' (40% gray, decimal), 'g#cc' (80% gray, hex),
              '#000', 'g0', 'g#00' (black),
              '#fff', 'g100', 'g#ff' (white)
              'h8' (color number 8), 'h255' (color number 255)

              Setting:
              'bold', 'italics', 'underline', 'blink', 'standout',
              'strikethrough'

              Some terminals use 'bold' for bright colors.  Most terminals
              ignore the 'blink' setting.  If the color is not given then
              'default' will be assumed.

        bg -- a string containing the background color

              Color values:
              'default' (use the terminal's default background),
              'black', 'dark red', 'dark green', 'brown', 'dark blue',
              'dark magenta', 'dark cyan', 'light gray'

              High-color exaples:
              see fg examples above

              An empty string will be treated the same as 'default'.

        colors -- the maximum colors available for the specification

                   Valid values include: 1, 16, 88 and 256.  High-color
                   values are only usable with 88 or 256 colors.  With
                   1 color only the foreground settings may be used.

        >>> AttrSpec('dark red', 'light gray', 16)
        AttrSpec('dark red', 'light gray')
        >>> AttrSpec('yellow, underline, bold', 'dark blue')
        AttrSpec('yellow,bold,underline', 'dark blue')
        >>> AttrSpec('#ddb', '#004', 256) # closest colors will be found
        AttrSpec('#dda', '#006')
        >>> AttrSpec('#ddb', '#004', 88)
        AttrSpec('#ccc', '#000', colors=88)
        """
        if colors not in (1, 16, 88, 256):
            raise AttrSpecError('invalid number of colors (%d).' % colors)
        self._value = 0 | _HIGH_88_COLOR * (colors == 88)
        self.foreground = fg
        self.background = bg
        if self.colors > colors:
            raise AttrSpecError(('foreground/background (%s/%s) require ' +
                'more colors than have been specified (%d).') %
                (repr(fg), repr(bg), colors))

    foreground_basic = property(lambda s: s._value & _FG_BASIC_COLOR != 0)
    foreground_high = property(lambda s: s._value & _FG_HIGH_COLOR != 0)
    foreground_number = property(lambda s: s._value & _FG_COLOR_MASK)
    background_basic = property(lambda s: s._value & _BG_BASIC_COLOR != 0)
    background_high = property(lambda s: s._value & _BG_HIGH_COLOR != 0)
    background_number = property(lambda s: (s._value & _BG_COLOR_MASK)
        >> _BG_SHIFT)
    italics = property(lambda s: s._value & _ITALICS != 0)
    bold = property(lambda s: s._value & _BOLD != 0)
    underline = property(lambda s: s._value & _UNDERLINE != 0)
    blink = property(lambda s: s._value & _BLINK != 0)
    standout = property(lambda s: s._value & _STANDOUT != 0)
    strikethrough = property(lambda s: s._value & _STRIKETHROUGH != 0)

    def _colors(self):
        """
        Return the maximum colors required for this object.

        Returns 256, 88, 16 or 1.
        """
        if self._value & _HIGH_88_COLOR:
            return 88
        if self._value & (_BG_HIGH_COLOR | _FG_HIGH_COLOR):
            return 256
        if self._value & (_BG_BASIC_COLOR | _BG_BASIC_COLOR):
            return 16
        return 1
    colors = property(_colors)

    def __repr__(self):
        """
        Return an executable python representation of the AttrSpec
        object.
        """
        args = "%r, %r" % (self.foreground, self.background)
        if self.colors == 88:
            # 88-color mode is the only one that is handled differently
            args = args + ", colors=88"
        return "%s(%s)" % (self.__class__.__name__, args)

    def _foreground_color(self):
        """Return only the color component of the foreground."""
        if not (self.foreground_basic or self.foreground_high):
            return 'default'
        if self.foreground_basic:
            return _BASIC_COLORS[self.foreground_number]
        if self.colors == 88:
            return _color_desc_88(self.foreground_number)
        return _color_desc_256(self.foreground_number)

    def _foreground(self):
        return (self._foreground_color() +
            ',bold' * self.bold + ',italics' * self.italics +
            ',standout' * self.standout + ',blink' * self.blink +
            ',underline' * self.underline + ',strikethrough' * self.strikethrough)

    def _set_foreground(self, foreground):
        color = None
        flags = 0
        # handle comma-separated foreground
        for part in foreground.split(','):
            part = part.strip()
            if part in _ATTRIBUTES:
                # parse and store "settings"/attributes in flags
                if flags & _ATTRIBUTES[part]:
                    raise AttrSpecError(("Setting %s specified more than" +
                        "once in foreground (%s)") % (repr(part),
                        repr(foreground)))
                flags |= _ATTRIBUTES[part]
                continue
            # past this point we must be specifying a color
            if part in ('', 'default'):
                scolor = 0
            elif part in _BASIC_COLORS:
                scolor = _BASIC_COLORS.index(part)
                flags |= _FG_BASIC_COLOR
            elif self._value & _HIGH_88_COLOR:
                scolor = _parse_color_88(part)
                flags |= _FG_HIGH_COLOR
            else:
                scolor = _parse_color_256(part)
                flags |= _FG_HIGH_COLOR
            # _parse_color_*() return None for unrecognised colors
            if scolor is None:
                raise AttrSpecError(("Unrecognised color specification %s " +
                    "in foreground (%s)") % (repr(part), repr(foreground)))
            if color is not None:
                raise AttrSpecError(("More than one color given for " +
                    "foreground (%s)") % (repr(foreground),))
            color = scolor
        if color is None:
            color = 0
        self._value = (self._value & ~_FG_MASK) | color | flags

    foreground = property(_foreground, _set_foreground)

    def _background(self):
        """Return the background color."""
        if not (self.background_basic or self.background_high):
            return 'default'
        if self.background_basic:
            return _BASIC_COLORS[self.background_number]
        if self._value & _HIGH_88_COLOR:
            return _color_desc_88(self.background_number)
        return _color_desc_256(self.background_number)

    def _set_background(self, background):
        flags = 0
        if background in ('', 'default'):
            color = 0
        elif background in _BASIC_COLORS:
            color = _BASIC_COLORS.index(background)
            flags |= _BG_BASIC_COLOR
        elif self._value & _HIGH_88_COLOR:
            color = _parse_color_88(background)
            flags |= _BG_HIGH_COLOR
        else:
            color = _parse_color_256(background)
            flags |= _BG_HIGH_COLOR
        if color is None:
            raise AttrSpecError(("Unrecognised color specification " +
                "in background (%s)") % (repr(background),))
        self._value = (self._value & ~_BG_MASK) | (color << _BG_SHIFT) | flags

    background = property(_background, _set_background)

    def get_rgb_values(self):
        """
        Return (fg_red, fg_green, fg_blue, bg_red, bg_green, bg_blue) color
        components.  Each component is in the range 0-255.  Values are taken
        from the XTerm defaults and may not exactly match the user's terminal.

        If the foreground or background is 'default' then all their compenents
        will be returned as None.

        >>> AttrSpec('yellow', '#ccf', colors=88).get_rgb_values()
        (255, 255, 0, 205, 205, 255)
        >>> AttrSpec('default', 'g92').get_rgb_values()
        (None, None, None, 238, 238, 238)
        """
        if not (self.foreground_basic or self.foreground_high):
            vals = (None, None, None)
        elif self.colors == 88:
            assert self.foreground_number < 88, "Invalid AttrSpec _value"
            vals = _COLOR_VALUES_88[self.foreground_number]
        else:
            vals = _COLOR_VALUES_256[self.foreground_number]

        if not (self.background_basic or self.background_high):
            return vals + (None, None, None)
        elif self.colors == 88:
            assert self.background_number < 88, "Invalid AttrSpec _value"
            return vals + _COLOR_VALUES_88[self.background_number]
        else:
            return vals + _COLOR_VALUES_256[self.background_number]

    def __eq__(self, other):
        return isinstance(other, AttrSpec) and self._value == other._value

    def __ne__(self, other):
        return not self == other

    __hash__ = object.__hash__


class RealTerminal(object):
    def __init__(self):
        super(RealTerminal,self).__init__()
        self._signal_keys_set = False
        self._old_signal_keys = None

    def tty_signal_keys(self, intr=None, quit=None, start=None,
        stop=None, susp=None, fileno=None):
        """
        Read and/or set the tty's signal character settings.
        This function returns the current settings as a tuple.

        Use the string 'undefined' to unmap keys from their signals.
        The value None is used when no change is being made.
        Setting signal keys is done using the integer ascii
        code for the key, eg.  3 for CTRL+C.

        If this function is called after start() has been called
        then the original settings will be restored when stop()
        is called.
        """
        if fileno is None:
            fileno = sys.stdin.fileno()
        if not os.isatty(fileno):
            return

        tattr = termios.tcgetattr(fileno)
        sattr = tattr[6]
        skeys = (sattr[termios.VINTR], sattr[termios.VQUIT],
            sattr[termios.VSTART], sattr[termios.VSTOP],
            sattr[termios.VSUSP])

        if intr == 'undefined': intr = 0
        if quit == 'undefined': quit = 0
        if start == 'undefined': start = 0
        if stop == 'undefined': stop = 0
        if susp == 'undefined': susp = 0

        if intr is not None: tattr[6][termios.VINTR] = intr
        if quit is not None: tattr[6][termios.VQUIT] = quit
        if start is not None: tattr[6][termios.VSTART] = start
        if stop is not None: tattr[6][termios.VSTOP] = stop
        if susp is not None: tattr[6][termios.VSUSP] = susp

        if intr is not None or quit is not None or \
            start is not None or stop is not None or \
            susp is not None:
            termios.tcsetattr(fileno, termios.TCSADRAIN, tattr)
            self._signal_keys_set = True

        return skeys


class ScreenError(Exception):
    pass

class BaseScreen(with_metaclass(signals.MetaSignals, object)):
    """
    Base class for Screen classes (raw_display.Screen, .. etc)
    """
    signals = [UPDATE_PALETTE_ENTRY, INPUT_DESCRIPTORS_CHANGED]

    def __init__(self):
        super(BaseScreen,self).__init__()
        self._palette = {}
        self._started = False

    started = property(lambda self: self._started)

    def start(self, *args, **kwargs):
        """Set up the screen.  If the screen has already been started, does
        nothing.

        May be used as a context manager, in which case :meth:`stop` will
        automatically be called at the end of the block:

            with screen.start():
                ...

        You shouldn't override this method in a subclass; instead, override
        :meth:`_start`.
        """
        if not self._started:
            self._start(*args, **kwargs)
        self._started = True
        return StoppingContext(self)

    def _start(self):
        pass

    def stop(self):
        if self._started:
            self._stop()
        self._started = False

    def _stop(self):
        pass

    def run_wrapper(self, fn, *args, **kwargs):
        """Start the screen, call a function, then stop the screen.  Extra
        arguments are passed to `start`.

        Deprecated in favor of calling `start` as a context manager.
        """
        with self.start(*args, **kwargs):
            return fn()


    def register_palette(self, palette):
        """Register a set of palette entries.

        palette -- a list of (name, like_other_name) or
        (name, foreground, background, mono, foreground_high,
        background_high) tuples

            The (name, like_other_name) format will copy the settings
            from the palette entry like_other_name, which must appear
            before this tuple in the list.

            The mono and foreground/background_high values are
            optional ie. the second tuple format may have 3, 4 or 6
            values.  See register_palette_entry() for a description
            of the tuple values.
        """

        for item in palette:
            if len(item) in (3,4,6):
                self.register_palette_entry(*item)
                continue
            if len(item) != 2:
                raise ScreenError("Invalid register_palette entry: %s" %
                    repr(item))
            name, like_name = item
            if like_name not in self._palette:
                raise ScreenError("palette entry '%s' doesn't exist"%like_name)
            self._palette[name] = self._palette[like_name]

    def register_palette_entry(self, name, foreground, background,
        mono=None, foreground_high=None, background_high=None):
        """Register a single palette entry.

        name -- new entry/attribute name

        foreground -- a string containing a comma-separated foreground
        color and settings

            Color values:
            'default' (use the terminal's default foreground),
            'black', 'dark red', 'dark green', 'brown', 'dark blue',
            'dark magenta', 'dark cyan', 'light gray', 'dark gray',
            'light red', 'light green', 'yellow', 'light blue',
            'light magenta', 'light cyan', 'white'

            Settings:
            'bold', 'underline', 'blink', 'standout', 'strikethrough'

            Some terminals use 'bold' for bright colors.  Most terminals
            ignore the 'blink' setting.  If the color is not given then
            'default' will be assumed.

        background -- a string containing the background color

            Background color values:
            'default' (use the terminal's default background),
            'black', 'dark red', 'dark green', 'brown', 'dark blue',
            'dark magenta', 'dark cyan', 'light gray'

        mono -- a comma-separated string containing monochrome terminal
        settings (see "Settings" above.)

            None = no terminal settings (same as 'default')

        foreground_high -- a string containing a comma-separated
        foreground color and settings, standard foreground
        colors (see "Color values" above) or high-colors may
        be used

            High-color example values:
            '#009' (0% red, 0% green, 60% red, like HTML colors)
            '#fcc' (100% red, 80% green, 80% blue)
            'g40' (40% gray, decimal), 'g#cc' (80% gray, hex),
            '#000', 'g0', 'g#00' (black),
            '#fff', 'g100', 'g#ff' (white)
            'h8' (color number 8), 'h255' (color number 255)

            None = use foreground parameter value

        background_high -- a string containing the background color,
        standard background colors (see "Background colors" above)
        or high-colors (see "High-color example values" above)
        may be used

            None = use background parameter value
        """
        basic = AttrSpec(foreground, background, 16)

        if type(mono) == tuple:
            # old style of specifying mono attributes was to put them
            # in a tuple.  convert to comma-separated string
            mono = ",".join(mono)
        if mono is None:
            mono = DEFAULT
        mono = AttrSpec(mono, DEFAULT, 1)

        if foreground_high is None:
            foreground_high = foreground
        if background_high is None:
            background_high = background
        high_256 = AttrSpec(foreground_high, background_high, 256)

        # 'hX' where X > 15 are different in 88/256 color, use
        # basic colors for 88-color mode if high colors are specified
        # in this way (also avoids crash when X > 87)
        def large_h(desc):
            if not desc.startswith('h'):
                return False
            if ',' in desc:
            	desc = desc.split(',',1)[0]
            num = int(desc[1:], 10)
            return num > 15
        if large_h(foreground_high) or large_h(background_high):
            high_88 = basic
        else:
            high_88 = AttrSpec(foreground_high, background_high, 88)

        signals.emit_signal(self, UPDATE_PALETTE_ENTRY,
            name, basic, mono, high_88, high_256)
        self._palette[name] = (basic, mono, high_88, high_256)


def _test():
    import doctest
    doctest.testmod()

if __name__=='__main__':
    _test()
