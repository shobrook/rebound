#!/usr/bin/python
#
# Urwid Text Layout classes
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

from urwid.util import calc_width, calc_text_pos, calc_trim_text, is_wide_char, \
    move_prev_char, move_next_char
from urwid.compat import bytes, PYTHON3, B, xrange

class TextLayout:
    def supports_align_mode(self, align):
        """Return True if align is a supported align mode."""
        return True
    def supports_wrap_mode(self, wrap):
        """Return True if wrap is a supported wrap mode."""
        return True
    def layout(self, text, width, align, wrap ):
        """
        Return a layout structure for text.

        :param text: string in current encoding or unicode string
        :param width: number of screen columns available
        :param align: align mode for text
        :param wrap: wrap mode for text

        Layout structure is a list of line layouts, one per output line.
        Line layouts are lists than may contain the following tuples:

        * (column width of text segment, start offset, end offset)
        * (number of space characters to insert, offset or None)
        * (column width of insert text, offset, "insert text")

        The offset in the last two tuples is used to determine the
        attribute used for the inserted spaces or text respectively.
        The attribute used will be the same as the attribute at that
        text offset.  If the offset is None when inserting spaces
        then no attribute will be used.
        """
        raise NotImplementedError("This function must be overridden by a real"
            " text layout class. (see StandardTextLayout)")

class CanNotDisplayText(Exception):
    pass

class StandardTextLayout(TextLayout):
    def __init__(self):#, tab_stops=(), tab_stop_every=8):
        pass
        #"""
        #tab_stops -- list of screen column indexes for tab stops
        #tab_stop_every -- repeated interval for following tab stops
        #"""
        #assert tab_stop_every is None or type(tab_stop_every)==int
        #if not tab_stops and tab_stop_every:
        #    self.tab_stops = (tab_stop_every,)
        #self.tab_stops = tab_stops
        #self.tab_stop_every = tab_stop_every
    def supports_align_mode(self, align):
        """Return True if align is 'left', 'center' or 'right'."""
        return align in ('left', 'center', 'right')
    def supports_wrap_mode(self, wrap):
        """Return True if wrap is 'any', 'space' or 'clip'."""
        return wrap in ('any', 'space', 'clip')
    def layout(self, text, width, align, wrap ):
        """Return a layout structure for text."""
        try:
            segs = self.calculate_text_segments( text, width, wrap )
            return self.align_layout( text, width, segs, wrap, align )
        except CanNotDisplayText:
            return [[]]

    def pack(self, maxcol, layout):
        """
        Return a minimal maxcol value that would result in the same
        number of lines for layout.  layout must be a layout structure
        returned by self.layout().
        """
        maxwidth = 0
        assert layout, "huh? empty layout?: "+repr(layout)
        for l in layout:
            lw = line_width(l)
            if lw >= maxcol:
                return maxcol
            maxwidth = max(maxwidth, lw)
        return maxwidth

    def align_layout( self, text, width, segs, wrap, align ):
        """Convert the layout segs to an aligned layout."""
        out = []
        for l in segs:
            sc = line_width(l)
            if sc == width or align=='left':
                out.append(l)
                continue

            if align == 'right':
                out.append([(width-sc, None)] + l)
                continue
            assert align == 'center'
            out.append([((width-sc+1) // 2, None)] + l)
        return out


    def calculate_text_segments(self, text, width, wrap):
        """
        Calculate the segments of text to display given width screen
        columns to display them.

        text - unicode text or byte string to display
        width - number of available screen columns
        wrap - wrapping mode used

        Returns a layout structure without alignment applied.
        """
        nl, nl_o, sp_o = "\n", "\n", " "
        if PYTHON3 and isinstance(text, bytes):
            nl = B(nl) # can only find bytes in python3 bytestrings
            nl_o = ord(nl_o) # + an item of a bytestring is the ordinal value
            sp_o = ord(sp_o)
        b = []
        p = 0
        if wrap == 'clip':
            # no wrapping to calculate, so it's easy.
            while p<=len(text):
                n_cr = text.find(nl, p)
                if n_cr == -1:
                    n_cr = len(text)
                sc = calc_width(text, p, n_cr)
                l = [(0,n_cr)]
                if p!=n_cr:
                    l = [(sc, p, n_cr)] + l
                b.append(l)
                p = n_cr+1
            return b


        while p<=len(text):
            # look for next eligible line break
            n_cr = text.find(nl, p)
            if n_cr == -1:
                n_cr = len(text)
            sc = calc_width(text, p, n_cr)
            if sc == 0:
                # removed character hint
                b.append([(0,n_cr)])
                p = n_cr+1
                continue
            if sc <= width:
                # this segment fits
                b.append([(sc,p,n_cr),
                    # removed character hint
                    (0,n_cr)])

                p = n_cr+1
                continue
            pos, sc = calc_text_pos( text, p, n_cr, width )
            if pos == p: # pathological width=1 double-byte case
                raise CanNotDisplayText(
                    "Wide character will not fit in 1-column width")
            if wrap == 'any':
                b.append([(sc,p,pos)])
                p = pos
                continue
            assert wrap == 'space'
            if text[pos] == sp_o:
                # perfect space wrap
                b.append([(sc,p,pos),
                    # removed character hint
                    (0,pos)])
                p = pos+1
                continue
            if is_wide_char(text, pos):
                # perfect next wide
                b.append([(sc,p,pos)])
                p = pos
                continue
            prev = pos
            while prev > p:
                prev = move_prev_char(text, p, prev)
                if text[prev] == sp_o:
                    sc = calc_width(text,p,prev)
                    l = [(0,prev)]
                    if p!=prev:
                        l = [(sc,p,prev)] + l
                    b.append(l)
                    p = prev+1
                    break
                if is_wide_char(text,prev):
                    # wrap after wide char
                    next = move_next_char(text, prev, pos)
                    sc = calc_width(text,p,next)
                    b.append([(sc,p,next)])
                    p = next
                    break
            else:
                # unwrap previous line space if possible to
                # fit more text (we're breaking a word anyway)
                if b and (len(b[-1]) == 2 or ( len(b[-1])==1
                        and len(b[-1][0])==2 )):
                    # look for removed space above
                    if len(b[-1]) == 1:
                        [(h_sc, h_off)] = b[-1]
                        p_sc = 0
                        p_off = p_end = h_off
                    else:
                        [(p_sc, p_off, p_end),
                               (h_sc, h_off)] = b[-1]
                    if (p_sc < width and h_sc==0 and
                        text[h_off] == sp_o):
                        # combine with previous line
                        del b[-1]
                        p = p_off
                        pos, sc = calc_text_pos(
                            text, p, n_cr, width )
                        b.append([(sc,p,pos)])
                        # check for trailing " " or "\n"
                        p = pos
                        if p < len(text) and (
                            text[p] in (sp_o, nl_o)):
                            # removed character hint
                            b[-1].append((0,p))
                            p += 1
                        continue


                # force any char wrap
                b.append([(sc,p,pos)])
                p = pos
        return b



######################################
# default layout object to use
default_layout = StandardTextLayout()
######################################


class LayoutSegment:
    def __init__(self, seg):
        """Create object from line layout segment structure"""

        assert type(seg) == tuple, repr(seg)
        assert len(seg) in (2,3), repr(seg)

        self.sc, self.offs = seg[:2]

        assert type(self.sc) == int, repr(self.sc)

        if len(seg)==3:
            assert type(self.offs) == int, repr(self.offs)
            assert self.sc > 0, repr(seg)
            t = seg[2]
            if type(t) == bytes:
                self.text = t
                self.end = None
            else:
                assert type(t) == int, repr(t)
                self.text = None
                self.end = t
        else:
            assert len(seg) == 2, repr(seg)
            if self.offs is not None:
                assert self.sc >= 0, repr(seg)
                assert type(self.offs)==int
            self.text = self.end = None

    def subseg(self, text, start, end):
        """
        Return a "sub-segment" list containing segment structures
        that make up a portion of this segment.

        A list is returned to handle cases where wide characters
        need to be replaced with a space character at either edge
        so two or three segments will be returned.
        """
        if start < 0: start = 0
        if end > self.sc: end = self.sc
        if start >= end:
            return [] # completely gone
        if self.text:
            # use text stored in segment (self.text)
            spos, epos, pad_left, pad_right = calc_trim_text(
                self.text, 0, len(self.text), start, end )
            return [ (end-start, self.offs, bytes().ljust(pad_left) +
                self.text[spos:epos] + bytes().ljust(pad_right)) ]
        elif self.end:
            # use text passed as parameter (text)
            spos, epos, pad_left, pad_right = calc_trim_text(
                text, self.offs, self.end, start, end )
            l = []
            if pad_left:
                l.append((1,spos-1))
            l.append((end-start-pad_left-pad_right, spos, epos))
            if pad_right:
                l.append((1,epos))
            return l
        else:
            # simple padding adjustment
            return [(end-start,self.offs)]


def line_width( segs ):
    """
    Return the screen column width of one line of a text layout structure.

    This function ignores any existing shift applied to the line,
    represented by an (amount, None) tuple at the start of the line.
    """
    sc = 0
    seglist = segs
    if segs and len(segs[0])==2 and segs[0][1]==None:
        seglist = segs[1:]
    for s in seglist:
        sc += s[0]
    return sc

def shift_line( segs, amount ):
    """
    Return a shifted line from a layout structure to the left or right.
    segs -- line of a layout structure
    amount -- screen columns to shift right (+ve) or left (-ve)
    """
    assert type(amount)==int, repr(amount)

    if segs and len(segs[0])==2 and segs[0][1]==None:
        # existing shift
        amount += segs[0][0]
        if amount:
            return [(amount,None)]+segs[1:]
        return segs[1:]

    if amount:
        return [(amount,None)]+segs
    return segs


def trim_line( segs, text, start, end ):
    """
    Return a trimmed line of a text layout structure.
    text -- text to which this layout structure applies
    start -- starting screen column
    end -- ending screen column
    """
    l = []
    x = 0
    for seg in segs:
        sc = seg[0]
        if start or sc < 0:
            if start >= sc:
                start -= sc
                x += sc
                continue
            s = LayoutSegment(seg)
            if x+sc >= end:
                # can all be done at once
                return s.subseg( text, start, end-x )
            l += s.subseg( text, start, sc )
            start = 0
            x += sc
            continue
        if x >= end:
            break
        if x+sc > end:
            s = LayoutSegment(seg)
            l += s.subseg( text, 0, end-x )
            break
        l.append( seg )
    return l



def calc_line_pos( text, line_layout, pref_col ):
    """
    Calculate the closest linear position to pref_col given a
    line layout structure.  Returns None if no position found.
    """
    closest_sc = None
    closest_pos = None
    current_sc = 0

    if pref_col == 'left':
        for seg in line_layout:
            s = LayoutSegment(seg)
            if s.offs is not None:
                return s.offs
        return
    elif pref_col == 'right':
        for seg in line_layout:
            s = LayoutSegment(seg)
            if s.offs is not None:
                closest_pos = s
        s = closest_pos
        if s is None:
            return
        if s.end is None:
            return s.offs
        return calc_text_pos( text, s.offs, s.end, s.sc-1)[0]

    for seg in line_layout:
        s = LayoutSegment(seg)
        if s.offs is not None:
            if s.end is not None:
                if (current_sc <= pref_col and
                    pref_col < current_sc + s.sc):
                    # exact match within this segment
                    return calc_text_pos( text,
                        s.offs, s.end,
                        pref_col - current_sc )[0]
                elif current_sc <= pref_col:
                    closest_sc = current_sc + s.sc - 1
                    closest_pos = s

            if closest_sc is None or ( abs(pref_col-current_sc)
                    < abs(pref_col-closest_sc) ):
                # this screen column is closer
                closest_sc = current_sc
                closest_pos = s.offs
            if current_sc > closest_sc:
                # we're moving past
                break
        current_sc += s.sc

    if closest_pos is None or type(closest_pos) == int:
        return closest_pos

    # return the last positions in the segment "closest_pos"
    s = closest_pos
    return calc_text_pos( text, s.offs, s.end, s.sc-1)[0]

def calc_pos( text, layout, pref_col, row ):
    """
    Calculate the closest linear position to pref_col and row given a
    layout structure.
    """

    if row < 0 or row >= len(layout):
        raise Exception("calculate_pos: out of layout row range")

    pos = calc_line_pos( text, layout[row], pref_col )
    if pos is not None:
        return pos

    rows_above = list(xrange(row-1,-1,-1))
    rows_below = list(xrange(row+1,len(layout)))
    while rows_above and rows_below:
        if rows_above:
            r = rows_above.pop(0)
            pos = calc_line_pos(text, layout[r], pref_col)
            if pos is not None: return pos
        if rows_below:
            r = rows_below.pop(0)
            pos = calc_line_pos(text, layout[r], pref_col)
            if pos is not None: return pos
    return 0


def calc_coords( text, layout, pos, clamp=1 ):
    """
    Calculate the coordinates closest to position pos in text with layout.

    text -- raw string or unicode string
    layout -- layout structure applied to text
    pos -- integer position into text
    clamp -- ignored right now
    """
    closest = None
    y = 0
    for line_layout in layout:
        x = 0
        for seg in line_layout:
            s = LayoutSegment(seg)
            if s.offs is None:
                x += s.sc
                continue
            if s.offs == pos:
                return x,y
            if s.end is not None and s.offs<=pos and s.end>pos:
                x += calc_width( text, s.offs, pos )
                return x,y
            distance = abs(s.offs - pos)
            if s.end is not None and s.end<pos:
                distance = pos - (s.end-1)
            if closest is None or distance < closest[0]:
                closest = distance, (x,y)
            x += s.sc
        y += 1

    if closest:
        return closest[1]
    return 0,0
