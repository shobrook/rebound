#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Urwid unicode character processing tables
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

import re

from urwid.compat import bytes, B, ord2, text_type

SAFE_ASCII_RE = re.compile(u"^[ -~]*$")
SAFE_ASCII_BYTES_RE = re.compile(B("^[ -~]*$"))

_byte_encoding = None

# GENERATED DATA
# generated from
# http://www.unicode.org/Public/4.0-Update/EastAsianWidth-4.0.0.txt

widths = [
    (126, 1),
    (159, 0),
    (687, 1),
    (710, 0),
    (711, 1),
    (727, 0),
    (733, 1),
    (879, 0),
    (1154, 1),
    (1161, 0),
    (4347, 1),
    (4447, 2),
    (7467, 1),
    (7521, 0),
    (8369, 1),
    (8426, 0),
    (9000, 1),
    (9002, 2),
    (11021, 1),
    (12350, 2),
    (12351, 1),
    (12438, 2),
    (12442, 0),
    (19893, 2),
    (19967, 1),
    (55203, 2),
    (63743, 1),
    (64106, 2),
    (65039, 1),
    (65059, 0),
    (65131, 2),
    (65279, 1),
    (65376, 2),
    (65500, 1),
    (65510, 2),
    (120831, 1),
    (262141, 2),
    (1114109, 1),
]

# ACCESSOR FUNCTIONS

def get_width( o ):
    """Return the screen column width for unicode ordinal o."""
    global widths
    if o == 0xe or o == 0xf:
        return 0
    for num, wid in widths:
        if o <= num:
            return wid
    return 1

def decode_one( text, pos ):
    """
    Return (ordinal at pos, next position) for UTF-8 encoded text.
    """
    assert isinstance(text, bytes), text
    b1 = ord2(text[pos])
    if not b1 & 0x80:
        return b1, pos+1
    error = ord("?"), pos+1
    lt = len(text)
    lt = lt-pos
    if lt < 2:
        return error
    if b1 & 0xe0 == 0xc0:
        b2 = ord2(text[pos+1])
        if b2 & 0xc0 != 0x80:
            return error
        o = ((b1&0x1f)<<6)|(b2&0x3f)
        if o < 0x80:
            return error
        return o, pos+2
    if lt < 3:
        return error
    if b1 & 0xf0 == 0xe0:
        b2 = ord2(text[pos+1])
        if b2 & 0xc0 != 0x80:
            return error
        b3 = ord2(text[pos+2])
        if b3 & 0xc0 != 0x80:
            return error
        o = ((b1&0x0f)<<12)|((b2&0x3f)<<6)|(b3&0x3f)
        if o < 0x800:
            return error
        return o, pos+3
    if lt < 4:
        return error
    if b1 & 0xf8 == 0xf0:
        b2 = ord2(text[pos+1])
        if b2 & 0xc0 != 0x80:
            return error
        b3 = ord2(text[pos+2])
        if b3 & 0xc0 != 0x80:
            return error
        b4 = ord2(text[pos+2])
        if b4 & 0xc0 != 0x80:
            return error
        o = ((b1&0x07)<<18)|((b2&0x3f)<<12)|((b3&0x3f)<<6)|(b4&0x3f)
        if o < 0x10000:
            return error
        return o, pos+4
    return error

def decode_one_uni(text, i):
    """
    decode_one implementation for unicode strings
    """
    return ord(text[i]), i+1

def decode_one_right(text, pos):
    """
    Return (ordinal at pos, next position) for UTF-8 encoded text.
    pos is assumed to be on the trailing byte of a utf-8 sequence.
    """
    assert isinstance(text, bytes), text
    error = ord("?"), pos-1
    p = pos
    while p >= 0:
        if ord2(text[p])&0xc0 != 0x80:
            o, next = decode_one( text, p )
            return o, p-1
        p -=1
        if p == p-4:
            return error

def set_byte_encoding(enc):
    assert enc in ('utf8', 'narrow', 'wide')
    global _byte_encoding
    _byte_encoding = enc

def get_byte_encoding():
    return _byte_encoding

def calc_text_pos(text, start_offs, end_offs, pref_col):
    """
    Calculate the closest position to the screen column pref_col in text
    where start_offs is the offset into text assumed to be screen column 0
    and end_offs is the end of the range to search.

    text may be unicode or a byte string in the target _byte_encoding

    Returns (position, actual_col).
    """
    assert start_offs <= end_offs, repr((start_offs, end_offs))
    utfs = isinstance(text, bytes) and _byte_encoding == "utf8"
    unis = not isinstance(text, bytes)
    if unis or utfs:
        decode = [decode_one, decode_one_uni][unis]
        i = start_offs
        sc = 0
        n = 1 # number to advance by
        while i < end_offs:
            o, n = decode(text, i)
            w = get_width(o)
            if w+sc > pref_col:
                return i, sc
            i = n
            sc += w
        return i, sc
    assert type(text) == bytes, repr(text)
    # "wide" and "narrow"
    i = start_offs+pref_col
    if i >= end_offs:
        return end_offs, end_offs-start_offs
    if _byte_encoding == "wide":
        if within_double_byte(text, start_offs, i) == 2:
            i -= 1
    return i, i-start_offs

def calc_width(text, start_offs, end_offs):
    """
    Return the screen column width of text between start_offs and end_offs.

    text may be unicode or a byte string in the target _byte_encoding

    Some characters are wide (take two columns) and others affect the
    previous character (take zero columns).  Use the widths table above
    to calculate the screen column width of text[start_offs:end_offs]
    """

    assert start_offs <= end_offs, repr((start_offs, end_offs))

    utfs = isinstance(text, bytes) and _byte_encoding == "utf8"
    unis = not isinstance(text, bytes)
    if (unis and not SAFE_ASCII_RE.match(text)
            ) or (utfs and not SAFE_ASCII_BYTES_RE.match(text)):
        decode = [decode_one, decode_one_uni][unis]
        i = start_offs
        sc = 0
        n = 1 # number to advance by
        while i < end_offs:
            o, n = decode(text, i)
            w = get_width(o)
            i = n
            sc += w
        return sc
    # "wide", "narrow" or all printable ASCII, just return the character count
    return end_offs - start_offs

def is_wide_char(text, offs):
    """
    Test if the character at offs within text is wide.

    text may be unicode or a byte string in the target _byte_encoding
    """
    if isinstance(text, text_type):
        o = ord(text[offs])
        return get_width(o) == 2
    assert isinstance(text, bytes)
    if _byte_encoding == "utf8":
        o, n = decode_one(text, offs)
        return get_width(o) == 2
    if _byte_encoding == "wide":
        return within_double_byte(text, offs, offs) == 1
    return False

def move_prev_char(text, start_offs, end_offs):
    """
    Return the position of the character before end_offs.
    """
    assert start_offs < end_offs
    if isinstance(text, text_type):
        return end_offs-1
    assert isinstance(text, bytes)
    if _byte_encoding == "utf8":
        o = end_offs-1
        while ord2(text[o])&0xc0 == 0x80:
            o -= 1
        return o
    if _byte_encoding == "wide" and within_double_byte(text,
        start_offs, end_offs-1) == 2:
        return end_offs-2
    return end_offs-1

def move_next_char(text, start_offs, end_offs):
    """
    Return the position of the character after start_offs.
    """
    assert start_offs < end_offs
    if isinstance(text, text_type):
        return start_offs+1
    assert isinstance(text, bytes)
    if _byte_encoding == "utf8":
        o = start_offs+1
        while o<end_offs and ord2(text[o])&0xc0 == 0x80:
            o += 1
        return o
    if _byte_encoding == "wide" and within_double_byte(text,
        start_offs, start_offs) == 1:
        return start_offs +2
    return start_offs+1

def within_double_byte(text, line_start, pos):
    """Return whether pos is within a double-byte encoded character.

    text -- byte string in question
    line_start -- offset of beginning of line (< pos)
    pos -- offset in question

    Return values:
    0 -- not within dbe char, or double_byte_encoding == False
    1 -- pos is on the 1st half of a dbe char
    2 -- pos is on the 2nd half of a dbe char
    """
    assert isinstance(text, bytes)
    v = ord2(text[pos])

    if v >= 0x40 and v < 0x7f:
        # might be second half of big5, uhc or gbk encoding
        if pos == line_start: return 0

        if ord2(text[pos-1]) >= 0x81:
            if within_double_byte(text, line_start, pos-1) == 1:
                return 2
        return 0

    if v < 0x80: return 0

    i = pos -1
    while i >= line_start:
        if ord2(text[i]) < 0x80:
            break
        i -= 1

    if (pos - i) & 1:
        return 1
    return 2

# TABLE GENERATION CODE

def process_east_asian_width():
    import sys
    out = []
    last = None
    for line in sys.stdin.readlines():
        if line[:1] == "#": continue
        line = line.strip()
        hex,rest = line.split(";",1)
        wid,rest = rest.split(" # ",1)
        word1 = rest.split(" ",1)[0]

        if "." in hex:
            hex = hex.split("..")[1]
        num = int(hex, 16)

        if word1 in ("COMBINING","MODIFIER","<control>"):
            l = 0
        elif wid in ("W", "F"):
            l = 2
        else:
            l = 1

        if last is None:
            out.append((0, l))
            last = l

        if last == l:
            out[-1] = (num, l)
        else:
            out.append( (num, l) )
            last = l

    print("widths = [")
    for o in out[1:]:  # treat control characters same as ascii
        print("\t%r," % (o,))
    print("]")

if __name__ == "__main__":
    process_east_asian_width()

