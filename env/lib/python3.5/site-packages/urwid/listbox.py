#!/usr/bin/python
#
# Urwid listbox class
#    Copyright (C) 2004-2012  Ian Ward
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

from urwid.compat import xrange, with_metaclass
from urwid.util import is_mouse_press
from urwid.canvas import SolidCanvas, CanvasCombine
from urwid.widget import Widget, nocache_widget_render_instance, BOX, GIVEN
from urwid.decoration import calculate_top_bottom_filler, normalize_valign
from urwid import signals
from urwid.signals import connect_signal
from urwid.monitored_list import MonitoredList, MonitoredFocusList
from urwid.container import WidgetContainerMixin
from urwid.command_map import (CURSOR_UP, CURSOR_DOWN,
    CURSOR_PAGE_UP, CURSOR_PAGE_DOWN, CURSOR_MAX_LEFT, CURSOR_MAX_RIGHT)

class ListWalkerError(Exception):
    pass

class ListWalker(with_metaclass(signals.MetaSignals, object)):
    signals = ["modified"]

    def _modified(self):
        signals.emit_signal(self, "modified")

    def get_focus(self):
        """
        This default implementation relies on a focus attribute and a
        __getitem__() method defined in a subclass.

        Override and don't call this method if these are not defined.
        """
        try:
            focus = self.focus
            return self[focus], focus
        except (IndexError, KeyError, TypeError):
            return None, None

    def get_next(self, position):
        """
        This default implementation relies on a next_position() method and a
        __getitem__() method defined in a subclass.

        Override and don't call this method if these are not defined.
        """
        try:
            position = self.next_position(position)
            return self[position], position
        except (IndexError, KeyError):
            return None, None

    def get_prev(self, position):
        """
        This default implementation relies on a prev_position() method and a
        __getitem__() method defined in a subclass.

        Override and don't call this method if these are not defined.
        """
        try:
            position = self.prev_position(position)
            return self[position], position
        except (IndexError, KeyError):
            return None, None


class PollingListWalker(object):  # NOT ListWalker subclass
    def __init__(self, contents):
        """
        contents -- list to poll for changes

        This class is deprecated.  Use SimpleFocusListWalker instead.
        """
        import warnings
        warnings.warn("PollingListWalker is deprecated, "
            "use SimpleFocusListWalker instead.", DeprecationWarning)

        self.contents = contents
        if not getattr(contents, '__getitem__', None):
            raise ListWalkerError("PollingListWalker expecting list like "
                "object, got: %r" % (contents,))
        self.focus = 0

    def _clamp_focus(self):
        if self.focus >= len(self.contents):
            self.focus = len(self.contents)-1

    def get_focus(self):
        """Return (focus widget, focus position)."""
        if len(self.contents) == 0: return None, None
        self._clamp_focus()
        return self.contents[self.focus], self.focus

    def set_focus(self, position):
        """Set focus position."""
        # this class is deprecated, otherwise I might have fixed this:
        assert type(position) == int
        self.focus = position

    def get_next(self, start_from):
        """
        Return (widget after start_from, position after start_from).
        """
        pos = start_from + 1
        if len(self.contents) <= pos: return None, None
        return self.contents[pos],pos

    def get_prev(self, start_from):
        """
        Return (widget before start_from, position before start_from).
        """
        pos = start_from - 1
        if pos < 0: return None, None
        return self.contents[pos],pos


class SimpleListWalker(MonitoredList, ListWalker):
    def __init__(self, contents):
        """
        contents -- list to copy into this object

        Changes made to this object (when it is treated as a list) are
        detected automatically and will cause ListBox objects using
        this list walker to be updated.
        """
        if not getattr(contents, '__getitem__', None):
            raise ListWalkerError("SimpleListWalker expecting list like object, got: %r"%(contents,))
        MonitoredList.__init__(self, contents)
        self.focus = 0

    def _get_contents(self):
        """
        Return self.

        Provides compatibility with old SimpleListWalker class.
        """
        return self
    contents = property(_get_contents)

    def _modified(self):
        if self.focus >= len(self):
            self.focus = max(0, len(self)-1)
        ListWalker._modified(self)

    def set_modified_callback(self, callback):
        """
        This function inherited from MonitoredList is not
        implemented in SimpleListWalker.

        Use connect_signal(list_walker, "modified", ...) instead.
        """
        raise NotImplementedError('Use connect_signal('
            'list_walker, "modified", ...) instead.')

    def set_focus(self, position):
        """Set focus position."""
        try:
            if position < 0 or position >= len(self):
                raise ValueError
        except (TypeError, ValueError):
            raise IndexError("No widget at position %s" % (position,))
        self.focus = position
        self._modified()

    def next_position(self, position):
        """
        Return position after start_from.
        """
        if len(self) - 1 <= position:
            raise IndexError
        return position + 1

    def prev_position(self, position):
        """
        Return position before start_from.
        """
        if position <= 0:
            raise IndexError
        return position - 1

    def positions(self, reverse=False):
        """
        Optional method for returning an iterable of positions.
        """
        if reverse:
            return xrange(len(self) - 1, -1, -1)
        return xrange(len(self))


class SimpleFocusListWalker(ListWalker, MonitoredFocusList):
    def __init__(self, contents):
        """
        contents -- list to copy into this object

        Changes made to this object (when it is treated as a list) are
        detected automatically and will cause ListBox objects using
        this list walker to be updated.

        Also, items added or removed before the widget in focus with
        normal list methods will cause the focus to be updated
        intelligently.
        """
        if not getattr(contents, '__getitem__', None):
            raise ListWalkerError("SimpleFocusListWalker expecting list like "
                "object, got: %r"%(contents,))
        MonitoredFocusList.__init__(self, contents)

    def set_modified_callback(self, callback):
        """
        This function inherited from MonitoredList is not
        implemented in SimpleFocusListWalker.

        Use connect_signal(list_walker, "modified", ...) instead.
        """
        raise NotImplementedError('Use connect_signal('
            'list_walker, "modified", ...) instead.')

    def set_focus(self, position):
        """Set focus position."""
        self.focus = position
        self._modified()

    def next_position(self, position):
        """
        Return position after start_from.
        """
        if len(self) - 1 <= position:
            raise IndexError
        return position + 1

    def prev_position(self, position):
        """
        Return position before start_from.
        """
        if position <= 0:
            raise IndexError
        return position - 1

    def positions(self, reverse=False):
        """
        Optional method for returning an iterable of positions.
        """
        if reverse:
            return xrange(len(self) - 1, -1, -1)
        return xrange(len(self))


class ListBoxError(Exception):
    pass

class ListBox(Widget, WidgetContainerMixin):
    """
    a horizontally stacked list of widgets
    """
    _selectable = True
    _sizing = frozenset([BOX])

    def __init__(self, body):
        """
        :param body: a ListWalker subclass such as
            :class:`SimpleFocusListWalker` that contains
            widgets to be displayed inside the list box
        :type body: ListWalker
        """
        self.body = body
        try:
            connect_signal(self._body, "modified", self._invalidate)
        except NameError:
            # our list walker has no modified signal so we must not
            # cache our canvases because we don't know when our
            # content has changed
            self.render = nocache_widget_render_instance(self)

        # offset_rows is the number of rows between the top of the view
        # and the top of the focused item
        self.offset_rows = 0
        # inset_fraction is used when the focused widget is off the
        # top of the view.  it is the fraction of the widget cut off
        # at the top.  (numerator, denominator)
        self.inset_fraction = (0,1)

        # pref_col is the preferred column for the cursor when moving
        # between widgets that use the cursor (edit boxes etc.)
        self.pref_col = 'left'

        # variable for delayed focus change used by set_focus
        self.set_focus_pending = 'first selectable'

        # variable for delayed valign change used by set_focus_valign
        self.set_focus_valign_pending = None


    def _get_body(self):
        return self._body

    def _set_body(self, body):
        if getattr(body, 'get_focus', None):
            self._body = body
        else:
            self._body = SimpleListWalker(body)
        self._invalidate()

    body = property(_get_body, _set_body, doc="""
    a ListWalker subclass such as :class:`SimpleFocusListWalker` that contains
    widgets to be displayed inside the list box
    """)


    def calculate_visible(self, size, focus=False ):
        """
        Returns the widgets that would be displayed in
        the ListBox given the current *size* and *focus*.

        see :meth:`Widget.render` for parameter details

        :returns: (*middle*, *top*, *bottom*) or (``None``, ``None``, ``None``)

        *middle*
            (*row offset*(when +ve) or *inset*(when -ve),
            *focus widget*, *focus position*, *focus rows*,
            *cursor coords* or ``None``)
        *top*
            (*# lines to trim off top*,
            list of (*widget*, *position*, *rows*) tuples above focus
            in order from bottom to top)
        *bottom*
            (*# lines to trim off bottom*,
            list of (*widget*, *position*, *rows*) tuples below focus
            in order from top to bottom)
        """
        (maxcol, maxrow) = size

        # 0. set the focus if a change is pending
        if self.set_focus_pending or self.set_focus_valign_pending:
            self._set_focus_complete( (maxcol, maxrow), focus )

        # 1. start with the focus widget
        focus_widget, focus_pos = self._body.get_focus()
        if focus_widget is None: #list box is empty?
            return None,None,None
        top_pos = focus_pos

        offset_rows, inset_rows = self.get_focus_offset_inset(
            (maxcol,maxrow))
        #    force at least one line of focus to be visible
        if maxrow and offset_rows >= maxrow:
            offset_rows = maxrow -1

        #    adjust position so cursor remains visible
        cursor = None
        if maxrow and focus_widget.selectable() and focus:
            if hasattr(focus_widget,'get_cursor_coords'):
                cursor=focus_widget.get_cursor_coords((maxcol,))

        if cursor is not None:
            cx, cy = cursor
            effective_cy = cy + offset_rows - inset_rows

            if effective_cy < 0: # cursor above top?
                inset_rows = cy
            elif effective_cy >= maxrow: # cursor below bottom?
                offset_rows = maxrow - cy -1
                if offset_rows < 0: # need to trim the top
                    inset_rows, offset_rows = -offset_rows, 0

        #    set trim_top by focus trimmimg
        trim_top = inset_rows
        focus_rows = focus_widget.rows((maxcol,),True)

        # 2. collect the widgets above the focus
        pos = focus_pos
        fill_lines = offset_rows
        fill_above = []
        top_pos = pos
        while fill_lines > 0:
            prev, pos = self._body.get_prev( pos )
            if prev is None: # run out of widgets above?
                offset_rows -= fill_lines
                break
            top_pos = pos

            p_rows = prev.rows( (maxcol,) )
            if p_rows: # filter out 0-height widgets
                fill_above.append( (prev, pos, p_rows) )
            if p_rows > fill_lines: # crosses top edge?
                trim_top = p_rows-fill_lines
                break
            fill_lines -= p_rows

        trim_bottom = focus_rows + offset_rows - inset_rows - maxrow
        if trim_bottom < 0: trim_bottom = 0

        # 3. collect the widgets below the focus
        pos = focus_pos
        fill_lines = maxrow - focus_rows - offset_rows + inset_rows
        fill_below = []
        while fill_lines > 0:
            next, pos = self._body.get_next( pos )
            if next is None: # run out of widgets below?
                break

            n_rows = next.rows( (maxcol,) )
            if n_rows: # filter out 0-height widgets
                fill_below.append( (next, pos, n_rows) )
            if n_rows > fill_lines: # crosses bottom edge?
                trim_bottom = n_rows-fill_lines
                fill_lines -= n_rows
                break
            fill_lines -= n_rows

        # 4. fill from top again if necessary & possible
        fill_lines = max(0, fill_lines)

        if fill_lines >0 and trim_top >0:
            if fill_lines <= trim_top:
                trim_top -= fill_lines
                offset_rows += fill_lines
                fill_lines = 0
            else:
                fill_lines -= trim_top
                offset_rows += trim_top
                trim_top = 0
        pos = top_pos
        while fill_lines > 0:
            prev, pos = self._body.get_prev( pos )
            if prev is None:
                break

            p_rows = prev.rows( (maxcol,) )
            fill_above.append( (prev, pos, p_rows) )
            if p_rows > fill_lines: # more than required
                trim_top = p_rows-fill_lines
                offset_rows += fill_lines
                break
            fill_lines -= p_rows
            offset_rows += p_rows

        # 5. return the interesting bits
        return ((offset_rows - inset_rows, focus_widget,
                focus_pos, focus_rows, cursor ),
            (trim_top, fill_above), (trim_bottom, fill_below))


    def render(self, size, focus=False ):
        """
        Render ListBox and return canvas.

        see :meth:`Widget.render` for details
        """
        (maxcol, maxrow) = size

        middle, top, bottom = self.calculate_visible(
            (maxcol, maxrow), focus=focus)
        if middle is None:
            return SolidCanvas(" ", maxcol, maxrow)

        _ignore, focus_widget, focus_pos, focus_rows, cursor = middle
        trim_top, fill_above = top
        trim_bottom, fill_below = bottom

        combinelist = []
        rows = 0
        fill_above.reverse() # fill_above is in bottom-up order
        for widget,w_pos,w_rows in fill_above:
            canvas = widget.render((maxcol,))
            if w_rows != canvas.rows():
                raise ListBoxError("Widget %r at position %r within listbox calculated %d rows but rendered %d!"% (widget,w_pos,w_rows, canvas.rows()))
            rows += w_rows
            combinelist.append((canvas, w_pos, False))

        focus_canvas = focus_widget.render((maxcol,), focus=focus)

        if focus_canvas.rows() != focus_rows:
            raise ListBoxError("Focus Widget %r at position %r within listbox calculated %d rows but rendered %d!"% (focus_widget,focus_pos,focus_rows, focus_canvas.rows()))
        c_cursor = focus_canvas.cursor
        if cursor != c_cursor:
            raise ListBoxError("Focus Widget %r at position %r within listbox calculated cursor coords %r but rendered cursor coords %r!" %(focus_widget,focus_pos,cursor,c_cursor))

        rows += focus_rows
        combinelist.append((focus_canvas, focus_pos, True))

        for widget,w_pos,w_rows in fill_below:
            canvas = widget.render((maxcol,))
            if w_rows != canvas.rows():
                raise ListBoxError("Widget %r at position %r within listbox calculated %d rows but rendered %d!"% (widget,w_pos,w_rows, canvas.rows()))
            rows += w_rows
            combinelist.append((canvas, w_pos, False))

        final_canvas = CanvasCombine(combinelist)

        if trim_top:
            final_canvas.trim(trim_top)
            rows -= trim_top
        if trim_bottom:
            final_canvas.trim_end(trim_bottom)
            rows -= trim_bottom

        if rows > maxrow:
            raise ListBoxError("Listbox contents too long!  Probably urwid's fault (please report): %r" % ((top,middle,bottom),))

        if rows < maxrow:
            bottom_pos = focus_pos
            if fill_below: bottom_pos = fill_below[-1][1]
            if trim_bottom != 0 or self._body.get_next(bottom_pos) != (None,None):
                raise ListBoxError("Listbox contents too short!  Probably urwid's fault (please report): %r" % ((top,middle,bottom),))
            final_canvas.pad_trim_top_bottom(0, maxrow - rows)

        return final_canvas


    def get_cursor_coords(self, size):
        """
        See :meth:`Widget.get_cursor_coords` for details
        """
        (maxcol, maxrow) = size

        middle, top, bottom = self.calculate_visible(
            (maxcol, maxrow), True)
        if middle is None:
            return None

        offset_inset, _ignore1, _ignore2, _ignore3, cursor = middle
        if not cursor:
            return None

        x, y = cursor
        y += offset_inset
        if y < 0 or y >= maxrow:
            return None
        return (x, y)


    def set_focus_valign(self, valign):
        """Set the focus widget's display offset and inset.

        :param valign: one of:
            'top', 'middle', 'bottom'
            ('fixed top', rows)
            ('fixed bottom', rows)
            ('relative', percentage 0=top 100=bottom)
        """
        vt, va = normalize_valign(valign,ListBoxError)
        self.set_focus_valign_pending = vt, va


    def set_focus(self, position, coming_from=None):
        """
        Set the focus position and try to keep the old focus in view.

        :param position: a position compatible with :meth:`self._body.set_focus`
        :param coming_from: set to 'above' or 'below' if you know that
                            old position is above or below the new position.
        :type coming_from: str
        """
        if coming_from not in ('above', 'below', None):
            raise ListBoxError("coming_from value invalid: %r" %
                (coming_from,))
        focus_widget, focus_pos = self._body.get_focus()
        if focus_widget is None:
            raise IndexError("Can't set focus, ListBox is empty")

        self.set_focus_pending = coming_from, focus_widget, focus_pos
        self._body.set_focus(position)

    def get_focus(self):
        """
        Return a `(focus widget, focus position)` tuple, for backwards
        compatibility. You may also use the new standard container
        properties :attr:`focus` and :attr:`focus_position` to read these values.
        """
        return self._body.get_focus()

    def _get_focus(self):
        """
        Return the widget in focus according to our :obj:`list walker <ListWalker>`.
        """
        return self._body.get_focus()[0]
    focus = property(_get_focus,
                     doc="the child widget in focus or None when ListBox is empty")

    def _get_focus_position(self):
        """
        Return the list walker position of the widget in focus. The type
        of value returned depends on the :obj:`list walker <ListWalker>`.

        """
        w, pos = self._body.get_focus()
        if w is None:
            raise IndexError("No focus_position, ListBox is empty")
        return pos
    focus_position = property(_get_focus_position, set_focus, doc="""
        the position of child widget in focus. The valid values for this
        position depend on the list walker in use.
        :exc:`IndexError` will be raised by reading this property when the
        ListBox is empty or setting this property to an invalid position.
        """)

    def _contents(self):
        class ListBoxContents(object):
            __getitem__ = self._contents__getitem__
        return ListBoxContents()
    def _contents__getitem__(self, key):
        # try list walker protocol v2 first
        getitem = getattr(self._body, '__getitem__', None)
        if getitem:
            try:
                return (getitem(key), None)
            except (IndexError, KeyError):
                raise KeyError("ListBox.contents key not found: %r" % (key,))
        # fall back to v1
        w, old_focus = self._body.get_focus()
        try:
            try:
                self._body.set_focus(key)
                return self._body.get_focus()[0]
            except (IndexError, KeyError):
                raise KeyError("ListBox.contents key not found: %r" % (key,))
        finally:
            self._body.set_focus(old_focus)
    contents = property(lambda self: self._contents, doc="""
        An object that allows reading widgets from the ListBox's list
        walker as a `(widget, options)` tuple. `None` is currently the only
        value for options.

        .. warning::

            This object may not be used to set or iterate over contents.

            You must use the list walker stored as
            :attr:`.body` to perform manipulation and iteration, if supported.
        """)

    def options(self):
        """
        There are currently no options for ListBox contents.

        Return None as a placeholder for future options.
        """
        return None

    def _set_focus_valign_complete(self, size, focus):
        """
        Finish setting the offset and inset now that we have have a
        maxcol & maxrow.
        """
        (maxcol, maxrow) = size
        vt,va = self.set_focus_valign_pending
        self.set_focus_valign_pending = None
        self.set_focus_pending = None

        focus_widget, focus_pos = self._body.get_focus()
        if focus_widget is None:
            return

        rows = focus_widget.rows((maxcol,), focus)
        rtop, rbot = calculate_top_bottom_filler(maxrow,
            vt, va, GIVEN, rows, None, 0, 0)

        self.shift_focus((maxcol, maxrow), rtop)

    def _set_focus_first_selectable(self, size, focus):
        """
        Choose the first visible, selectable widget below the
        current focus as the focus widget.
        """
        (maxcol, maxrow) = size
        self.set_focus_valign_pending = None
        self.set_focus_pending = None
        middle, top, bottom = self.calculate_visible(
            (maxcol, maxrow), focus=focus)
        if middle is None:
            return

        row_offset, focus_widget, focus_pos, focus_rows, cursor = middle
        trim_top, fill_above = top
        trim_bottom, fill_below = bottom

        if focus_widget.selectable():
            return

        if trim_bottom:
            fill_below = fill_below[:-1]
        new_row_offset = row_offset + focus_rows
        for widget, pos, rows in fill_below:
            if widget.selectable():
                self._body.set_focus(pos)
                self.shift_focus((maxcol, maxrow),
                    new_row_offset)
                return
            new_row_offset += rows

    def _set_focus_complete(self, size, focus):
        """
        Finish setting the position now that we have maxcol & maxrow.
        """
        (maxcol, maxrow) = size
        self._invalidate()
        if self.set_focus_pending == "first selectable":
            return self._set_focus_first_selectable(
                (maxcol,maxrow), focus)
        if self.set_focus_valign_pending is not None:
            return self._set_focus_valign_complete(
                (maxcol,maxrow), focus)
        coming_from, focus_widget, focus_pos = self.set_focus_pending
        self.set_focus_pending = None

        # new position
        new_focus_widget, position = self._body.get_focus()
        if focus_pos == position:
            # do nothing
            return

        # restore old focus temporarily
        self._body.set_focus(focus_pos)

        middle,top,bottom=self.calculate_visible((maxcol,maxrow),focus)
        focus_offset, focus_widget, focus_pos, focus_rows, cursor=middle
        trim_top, fill_above = top
        trim_bottom, fill_below = bottom

        offset = focus_offset
        for widget, pos, rows in fill_above:
            offset -= rows
            if pos == position:
                self.change_focus((maxcol, maxrow), pos,
                    offset, 'below' )
                return

        offset = focus_offset + focus_rows
        for widget, pos, rows in fill_below:
            if pos == position:
                self.change_focus((maxcol, maxrow), pos,
                    offset, 'above' )
                return
            offset += rows

        # failed to find widget among visible widgets
        self._body.set_focus( position )
        widget, position = self._body.get_focus()
        rows = widget.rows((maxcol,), focus)

        if coming_from=='below':
            offset = 0
        elif coming_from=='above':
            offset = maxrow-rows
        else:
            offset = (maxrow-rows) // 2
        self.shift_focus((maxcol, maxrow), offset)


    def shift_focus(self, size, offset_inset):
        """
        Move the location of the current focus relative to the top.
        This is used internally by methods that know the widget's *size*.

        See also :meth:`.set_focus_valign`.

        :param size: see :meth:`Widget.render` for details
        :param offset_inset: either the number of rows between the
            top of the listbox and the start of the focus widget (+ve
            value) or the number of lines of the focus widget hidden off
            the top edge of the listbox (-ve value) or ``0`` if the top edge
            of the focus widget is aligned with the top edge of the
            listbox.
        :type offset_inset: int
        """
        (maxcol, maxrow) = size

        if offset_inset >= 0:
            if offset_inset >= maxrow:
                raise ListBoxError("Invalid offset_inset: %r, only %r rows in list box"% (offset_inset, maxrow))
            self.offset_rows = offset_inset
            self.inset_fraction = (0,1)
        else:
            target, _ignore = self._body.get_focus()
            tgt_rows = target.rows( (maxcol,), True )
            if offset_inset + tgt_rows <= 0:
                raise ListBoxError("Invalid offset_inset: %r, only %r rows in target!" %(offset_inset, tgt_rows))
            self.offset_rows = 0
            self.inset_fraction = (-offset_inset,tgt_rows)
        self._invalidate()

    def update_pref_col_from_focus(self, size):
        """Update self.pref_col from the focus widget."""
        # TODO: should this not be private?
        (maxcol, maxrow) = size

        widget, old_pos = self._body.get_focus()
        if widget is None: return

        pref_col = None
        if hasattr(widget,'get_pref_col'):
            pref_col = widget.get_pref_col((maxcol,))
        if pref_col is None and hasattr(widget,'get_cursor_coords'):
            coords = widget.get_cursor_coords((maxcol,))
            if type(coords) == tuple:
                pref_col,y = coords
        if pref_col is not None:
            self.pref_col = pref_col


    def change_focus(self, size, position,
            offset_inset = 0, coming_from = None,
            cursor_coords = None, snap_rows = None):
        """
        Change the current focus widget.
        This is used internally by methods that know the widget's *size*.

        See also :meth:`.set_focus`.

        :param size: see :meth:`Widget.render` for details
        :param position: a position compatible with :meth:`self._body.set_focus`
        :param offset_inset: either the number of rows between the
            top of the listbox and the start of the focus widget (+ve
            value) or the number of lines of the focus widget hidden off
            the top edge of the listbox (-ve value) or 0 if the top edge
            of the focus widget is aligned with the top edge of the
            listbox (default if unspecified)
        :type offset_inset: int
        :param coming_from: either 'above', 'below' or unspecified `None`
        :type coming_from: str
        :param cursor_coords: (x, y) tuple indicating the desired
            column and row for the cursor, a (x,) tuple indicating only
            the column for the cursor, or unspecified
        :type cursor_coords: (int, int)
        :param snap_rows: the maximum number of extra rows to scroll
            when trying to "snap" a selectable focus into the view
        :type snap_rows: int
        """
        (maxcol, maxrow) = size

        # update pref_col before change
        if cursor_coords:
            self.pref_col = cursor_coords[0]
        else:
            self.update_pref_col_from_focus((maxcol,maxrow))

        self._invalidate()
        self._body.set_focus(position)
        target, _ignore = self._body.get_focus()
        tgt_rows = target.rows( (maxcol,), True)
        if snap_rows is None:
            snap_rows = maxrow - 1

        # "snap" to selectable widgets
        align_top = 0
        align_bottom = maxrow - tgt_rows

        if ( coming_from == 'above'
                and target.selectable()
                and offset_inset > align_bottom ):
            if snap_rows >= offset_inset - align_bottom:
                offset_inset = align_bottom
            elif snap_rows >= offset_inset - align_top:
                offset_inset = align_top
            else:
                offset_inset -= snap_rows

        if ( coming_from == 'below'
                and target.selectable()
                and offset_inset < align_top ):
            if snap_rows >= align_top - offset_inset:
                offset_inset = align_top
            elif snap_rows >= align_bottom - offset_inset:
                offset_inset = align_bottom
            else:
                offset_inset += snap_rows

        # convert offset_inset to offset_rows or inset_fraction
        if offset_inset >= 0:
            self.offset_rows = offset_inset
            self.inset_fraction = (0,1)
        else:
            if offset_inset + tgt_rows <= 0:
                raise ListBoxError("Invalid offset_inset: %s, only %s rows in target!" %(offset_inset, tgt_rows))
            self.offset_rows = 0
            self.inset_fraction = (-offset_inset,tgt_rows)

        if cursor_coords is None:
            if coming_from is None:
                return # must either know row or coming_from
            cursor_coords = (self.pref_col,)

        if not hasattr(target,'move_cursor_to_coords'):
            return

        attempt_rows = []

        if len(cursor_coords) == 1:
            # only column (not row) specified
            # start from closest edge and move inwards
            (pref_col,) = cursor_coords
            if coming_from=='above':
                attempt_rows = range( 0, tgt_rows )
            else:
                assert coming_from == 'below', "must specify coming_from ('above' or 'below') if cursor row is not specified"
                attempt_rows = range( tgt_rows, -1, -1)
        else:
            # both column and row specified
            # start from preferred row and move back to closest edge
            (pref_col, pref_row) = cursor_coords
            if pref_row < 0 or pref_row >= tgt_rows:
                raise ListBoxError("cursor_coords row outside valid range for target. pref_row:%r target_rows:%r"%(pref_row,tgt_rows))

            if coming_from=='above':
                attempt_rows = range( pref_row, -1, -1 )
            elif coming_from=='below':
                attempt_rows = range( pref_row, tgt_rows )
            else:
                attempt_rows = [pref_row]

        for row in attempt_rows:
            if target.move_cursor_to_coords((maxcol,),pref_col,row):
                break

    def get_focus_offset_inset(self, size):
        """Return (offset rows, inset rows) for focus widget."""
        (maxcol, maxrow) = size
        focus_widget, pos = self._body.get_focus()
        focus_rows = focus_widget.rows((maxcol,), True)
        offset_rows = self.offset_rows
        inset_rows = 0
        if offset_rows == 0:
            inum, iden = self.inset_fraction
            if inum < 0 or iden < 0 or inum >= iden:
                raise ListBoxError("Invalid inset_fraction: %r"%(self.inset_fraction,))
            inset_rows = focus_rows * inum // iden
            if inset_rows and inset_rows >= focus_rows:
                raise ListBoxError("urwid inset_fraction error (please report)")
        return offset_rows, inset_rows


    def make_cursor_visible(self, size):
        """Shift the focus widget so that its cursor is visible."""
        (maxcol, maxrow) = size

        focus_widget, pos = self._body.get_focus()
        if focus_widget is None:
            return
        if not focus_widget.selectable():
            return
        if not hasattr(focus_widget,'get_cursor_coords'):
            return
        cursor = focus_widget.get_cursor_coords((maxcol,))
        if cursor is None:
            return
        cx, cy = cursor
        offset_rows, inset_rows = self.get_focus_offset_inset(
            (maxcol, maxrow))

        if cy < inset_rows:
            self.shift_focus( (maxcol,maxrow), - (cy) )
            return

        if offset_rows - inset_rows + cy >= maxrow:
            self.shift_focus( (maxcol,maxrow), maxrow-cy-1 )
            return


    def keypress(self, size, key):
        """Move selection through the list elements scrolling when
        necessary. Keystrokes are first passed to widget in focus
        in case that widget can handle them.

        Keystrokes handled by this widget are:
         'up'        up one line (or widget)
         'down'      down one line (or widget)
         'page up'   move cursor up one listbox length (or widget)
         'page down' move cursor down one listbox length (or widget)
        """
        (maxcol, maxrow) = size

        if self.set_focus_pending or self.set_focus_valign_pending:
            self._set_focus_complete( (maxcol,maxrow), focus=True )

        focus_widget, pos = self._body.get_focus()
        if focus_widget is None: # empty listbox, can't do anything
            return key

        if focus_widget.selectable():
            key = focus_widget.keypress((maxcol,),key)
            if key is None:
                self.make_cursor_visible((maxcol,maxrow))
                return None

        def actual_key(unhandled):
            if unhandled:
                return key

        # pass off the heavy lifting
        if self._command_map[key] == CURSOR_UP:
            return actual_key(self._keypress_up((maxcol, maxrow)))

        if self._command_map[key] == CURSOR_DOWN:
            return actual_key(self._keypress_down((maxcol, maxrow)))

        if self._command_map[key] == CURSOR_PAGE_UP:
            return actual_key(self._keypress_page_up((maxcol, maxrow)))

        if self._command_map[key] == CURSOR_PAGE_DOWN:
            return actual_key(self._keypress_page_down((maxcol, maxrow)))

        if self._command_map[key] == CURSOR_MAX_LEFT:
            return actual_key(self._keypress_max_left())

        if self._command_map[key] == CURSOR_MAX_RIGHT:
            return actual_key(self._keypress_max_right())

        return key

    def _keypress_max_left(self):
        self.focus_position = next(iter(self.body.positions()))
        self.set_focus_valign('top')
        return True

    def _keypress_max_right(self):
        self.focus_position = next(iter(self.body.positions(reverse=True)))
        self.set_focus_valign('bottom')
        return True

    def _keypress_up(self, size):
        (maxcol, maxrow) = size

        middle, top, bottom = self.calculate_visible(
            (maxcol,maxrow), True)
        if middle is None: return True

        focus_row_offset,focus_widget,focus_pos,_ignore,cursor = middle
        trim_top, fill_above = top

        row_offset = focus_row_offset

        # look for selectable widget above
        pos = focus_pos
        widget = None
        for widget, pos, rows in fill_above:
            row_offset -= rows
            if rows and widget.selectable():
                # this one will do
                self.change_focus((maxcol,maxrow), pos,
                    row_offset, 'below')
                return

        # at this point we must scroll
        row_offset += 1
        self._invalidate()

        while row_offset > 0:
            # need to scroll in another candidate widget
            widget, pos = self._body.get_prev(pos)
            if widget is None:
                # cannot scroll any further
                return True # keypress not handled
            rows = widget.rows((maxcol,), True)
            row_offset -= rows
            if rows and widget.selectable():
                # this one will do
                self.change_focus((maxcol,maxrow), pos,
                    row_offset, 'below')
                return

        if not focus_widget.selectable() or focus_row_offset+1>=maxrow:
            # just take top one if focus is not selectable
            # or if focus has moved out of view
            if widget is None:
                self.shift_focus((maxcol,maxrow), row_offset)
                return
            self.change_focus((maxcol,maxrow), pos,
                row_offset, 'below')
            return

        # check if cursor will stop scroll from taking effect
        if cursor is not None:
            x,y = cursor
            if y+focus_row_offset+1 >= maxrow:
                # cursor position is a problem,
                # choose another focus
                if widget is None:
                    # try harder to get prev widget
                    widget, pos = self._body.get_prev(pos)
                    if widget is None:
                        return # can't do anything
                    rows = widget.rows((maxcol,), True)
                    row_offset -= rows

                if -row_offset >= rows:
                    # must scroll further than 1 line
                    row_offset = - (rows-1)

                self.change_focus((maxcol,maxrow),pos,
                    row_offset, 'below')
                return

        # if all else fails, just shift the current focus.
        self.shift_focus((maxcol,maxrow), focus_row_offset+1)


    def _keypress_down(self, size):
        (maxcol, maxrow) = size

        middle, top, bottom = self.calculate_visible(
            (maxcol,maxrow), True)
        if middle is None: return True

        focus_row_offset,focus_widget,focus_pos,focus_rows,cursor=middle
        trim_bottom, fill_below = bottom

        row_offset = focus_row_offset + focus_rows
        rows = focus_rows

        # look for selectable widget below
        pos = focus_pos
        widget = None
        for widget, pos, rows in fill_below:
            if rows and widget.selectable():
                # this one will do
                self.change_focus((maxcol,maxrow), pos,
                    row_offset, 'above')
                return
            row_offset += rows

        # at this point we must scroll
        row_offset -= 1
        self._invalidate()

        while row_offset < maxrow:
            # need to scroll in another candidate widget
            widget, pos = self._body.get_next(pos)
            if widget is None:
                # cannot scroll any further
                return True # keypress not handled
            rows = widget.rows((maxcol,))
            if rows and widget.selectable():
                # this one will do
                self.change_focus((maxcol,maxrow), pos,
                    row_offset, 'above')
                return
            row_offset += rows

        if not focus_widget.selectable() or focus_row_offset+focus_rows-1 <= 0:
            # just take bottom one if current is not selectable
            # or if focus has moved out of view
            if widget is None:
                self.shift_focus((maxcol,maxrow),
                    row_offset-rows)
                return
            # FIXME: catch this bug in testcase
            #self.change_focus((maxcol,maxrow), pos,
            #    row_offset+rows, 'above')
            self.change_focus((maxcol,maxrow), pos,
                row_offset-rows, 'above')
            return

        # check if cursor will stop scroll from taking effect
        if cursor is not None:
            x,y = cursor
            if y+focus_row_offset-1 < 0:
                # cursor position is a problem,
                # choose another focus
                if widget is None:
                    # try harder to get next widget
                    widget, pos = self._body.get_next(pos)
                    if widget is None:
                        return # can't do anything
                else:
                    row_offset -= rows

                if row_offset >= maxrow:
                    # must scroll further than 1 line
                    row_offset = maxrow-1

                self.change_focus((maxcol,maxrow),pos,
                    row_offset, 'above', )
                return

        # if all else fails, keep the current focus.
        self.shift_focus((maxcol,maxrow), focus_row_offset-1)


    def _keypress_page_up(self, size):
        (maxcol, maxrow) = size

        middle, top, bottom = self.calculate_visible(
            (maxcol,maxrow), True)
        if middle is None: return True

        row_offset, focus_widget, focus_pos, focus_rows, cursor = middle
        trim_top, fill_above = top

        # topmost_visible is row_offset rows above top row of
        # focus (+ve) or -row_offset rows below top row of focus (-ve)
        topmost_visible = row_offset

        # scroll_from_row is (first match)
        # 1. topmost visible row if focus is not selectable
        # 2. row containing cursor if focus has a cursor
        # 3. top row of focus widget if it is visible
        # 4. topmost visible row otherwise
        if not focus_widget.selectable():
            scroll_from_row = topmost_visible
        elif cursor is not None:
            x,y = cursor
            scroll_from_row = -y
        elif row_offset >= 0:
            scroll_from_row = 0
        else:
            scroll_from_row = topmost_visible

        # snap_rows is maximum extra rows to scroll when
        # snapping to new a focus
        snap_rows = topmost_visible - scroll_from_row

        # move row_offset to the new desired value (1 "page" up)
        row_offset = scroll_from_row + maxrow

        # not used below:
        scroll_from_row = topmost_visible = None


        # gather potential target widgets
        t = []
        # add current focus
        t.append((row_offset,focus_widget,focus_pos,focus_rows))
        pos = focus_pos
        # include widgets from calculate_visible(..)
        for widget, pos, rows in fill_above:
            row_offset -= rows
            t.append( (row_offset, widget, pos, rows) )
        # add newly visible ones, including within snap_rows
        snap_region_start = len(t)
        while row_offset > -snap_rows:
            widget, pos = self._body.get_prev(pos)
            if widget is None: break
            rows = widget.rows((maxcol,))
            row_offset -= rows
            # determine if one below puts current one into snap rgn
            if row_offset > 0:
                snap_region_start += 1
            t.append( (row_offset, widget, pos, rows) )

        # if we can't fill the top we need to adjust the row offsets
        row_offset, w, p, r = t[-1]
        if row_offset > 0:
            adjust = - row_offset
            t = [(ro+adjust, w, p, r) for (ro,w,p,r) in t]

        # if focus_widget (first in t) is off edge, remove it
        row_offset, w, p, r = t[0]
        if row_offset >= maxrow:
            del t[0]
            snap_region_start -= 1

        # we'll need this soon
        self.update_pref_col_from_focus((maxcol,maxrow))

        # choose the topmost selectable and (newly) visible widget
        # search within snap_rows then visible region
        search_order = (list(xrange(snap_region_start, len(t)))
            + list(xrange(snap_region_start-1, -1, -1)))
        #assert 0, repr((t, search_order))
        bad_choices = []
        cut_off_selectable_chosen = 0
        for i in search_order:
            row_offset, widget, pos, rows = t[i]
            if not widget.selectable():
                continue

            if not rows:
                continue

            # try selecting this widget
            pref_row = max(0, -row_offset)

            # if completely within snap region, adjust row_offset
            if rows + row_offset <= 0:
                self.change_focus( (maxcol,maxrow), pos,
                    -(rows-1), 'below',
                    (self.pref_col, rows-1),
                    snap_rows-((-row_offset)-(rows-1)))
            else:
                self.change_focus( (maxcol,maxrow), pos,
                    row_offset, 'below',
                    (self.pref_col, pref_row), snap_rows )

            # if we're as far up as we can scroll, take this one
            if (fill_above and self._body.get_prev(fill_above[-1][1])
                == (None,None) ):
                pass #return

            # find out where that actually puts us
            middle, top, bottom = self.calculate_visible(
                (maxcol,maxrow), True)
            act_row_offset, _ign1, _ign2, _ign3, _ign4 = middle

            # discard chosen widget if it will reduce scroll amount
            # because of a fixed cursor (absolute last resort)
            if act_row_offset > row_offset+snap_rows:
                bad_choices.append(i)
                continue
            if act_row_offset < row_offset:
                bad_choices.append(i)
                continue

            # also discard if off top edge (second last resort)
            if act_row_offset < 0:
                bad_choices.append(i)
                cut_off_selectable_chosen = 1
                continue

            return

        # anything selectable is better than what follows:
        if cut_off_selectable_chosen:
            return

        if fill_above and focus_widget.selectable():
            # if we're at the top and have a selectable, return
            if self._body.get_prev(fill_above[-1][1]) == (None,None):
                pass #return

        # if still none found choose the topmost widget
        good_choices = [j for j in search_order if j not in bad_choices]
        for i in good_choices + search_order:
            row_offset, widget, pos, rows = t[i]
            if pos == focus_pos: continue

            if not rows: # never focus a 0-height widget
                continue

            # if completely within snap region, adjust row_offset
            if rows + row_offset <= 0:
                snap_rows -= (-row_offset) - (rows-1)
                row_offset = -(rows-1)

            self.change_focus( (maxcol,maxrow), pos,
                row_offset, 'below', None,
                snap_rows )
            return

        # no choices available, just shift current one
        self.shift_focus((maxcol, maxrow), min(maxrow-1,row_offset))

        # final check for pathological case where we may fall short
        middle, top, bottom = self.calculate_visible(
            (maxcol,maxrow), True)
        act_row_offset, _ign1, pos, _ign2, _ign3 = middle
        if act_row_offset >= row_offset:
            # no problem
            return

        # fell short, try to select anything else above
        if not t:
            return
        _ign1, _ign2, pos, _ign3 = t[-1]
        widget, pos = self._body.get_prev(pos)
        if widget is None:
            # no dice, we're stuck here
            return
        # bring in only one row if possible
        rows = widget.rows((maxcol,), True)
        self.change_focus((maxcol,maxrow), pos, -(rows-1),
            'below', (self.pref_col, rows-1), 0 )


    def _keypress_page_down(self, size):
        (maxcol, maxrow) = size

        middle, top, bottom = self.calculate_visible(
            (maxcol,maxrow), True)
        if middle is None: return True

        row_offset, focus_widget, focus_pos, focus_rows, cursor = middle
        trim_bottom, fill_below = bottom

        # bottom_edge is maxrow-focus_pos rows below top row of focus
        bottom_edge = maxrow - row_offset

        # scroll_from_row is (first match)
        # 1. bottom edge if focus is not selectable
        # 2. row containing cursor + 1 if focus has a cursor
        # 3. bottom edge of focus widget if it is visible
        # 4. bottom edge otherwise
        if not focus_widget.selectable():
            scroll_from_row = bottom_edge
        elif cursor is not None:
            x,y = cursor
            scroll_from_row = y + 1
        elif bottom_edge >= focus_rows:
            scroll_from_row = focus_rows
        else:
            scroll_from_row = bottom_edge

        # snap_rows is maximum extra rows to scroll when
        # snapping to new a focus
        snap_rows = bottom_edge - scroll_from_row

        # move row_offset to the new desired value (1 "page" down)
        row_offset = -scroll_from_row

        # not used below:
        scroll_from_row = bottom_edge = None


        # gather potential target widgets
        t = []
        # add current focus
        t.append((row_offset,focus_widget,focus_pos,focus_rows))
        pos = focus_pos
        row_offset += focus_rows
        # include widgets from calculate_visible(..)
        for widget, pos, rows in fill_below:
            t.append( (row_offset, widget, pos, rows) )
            row_offset += rows
        # add newly visible ones, including within snap_rows
        snap_region_start = len(t)
        while row_offset < maxrow+snap_rows:
            widget, pos = self._body.get_next(pos)
            if widget is None: break
            rows = widget.rows((maxcol,))
            t.append( (row_offset, widget, pos, rows) )
            row_offset += rows
            # determine if one above puts current one into snap rgn
            if row_offset < maxrow:
                snap_region_start += 1

        # if we can't fill the bottom we need to adjust the row offsets
        row_offset, w, p, rows = t[-1]
        if row_offset + rows < maxrow:
            adjust = maxrow - (row_offset + rows)
            t = [(ro+adjust, w, p, r) for (ro,w,p,r) in t]

        # if focus_widget (first in t) is off edge, remove it
        row_offset, w, p, rows = t[0]
        if row_offset+rows <= 0:
            del t[0]
            snap_region_start -= 1

        # we'll need this soon
        self.update_pref_col_from_focus((maxcol,maxrow))

        # choose the bottommost selectable and (newly) visible widget
        # search within snap_rows then visible region
        search_order = (list(xrange(snap_region_start, len(t)))
            + list(xrange(snap_region_start-1, -1, -1)))
        #assert 0, repr((t, search_order))
        bad_choices = []
        cut_off_selectable_chosen = 0
        for i in search_order:
            row_offset, widget, pos, rows = t[i]
            if not widget.selectable():
                continue

            if not rows:
                continue

            # try selecting this widget
            pref_row = min(maxrow-row_offset-1, rows-1)

            # if completely within snap region, adjust row_offset
            if row_offset >= maxrow:
                self.change_focus( (maxcol,maxrow), pos,
                    maxrow-1, 'above',
                    (self.pref_col, 0),
                    snap_rows+maxrow-row_offset-1 )
            else:
                self.change_focus( (maxcol,maxrow), pos,
                    row_offset, 'above',
                    (self.pref_col, pref_row), snap_rows )

            # find out where that actually puts us
            middle, top, bottom = self.calculate_visible(
                (maxcol,maxrow), True)
            act_row_offset, _ign1, _ign2, _ign3, _ign4 = middle

            # discard chosen widget if it will reduce scroll amount
            # because of a fixed cursor (absolute last resort)
            if act_row_offset < row_offset-snap_rows:
                bad_choices.append(i)
                continue
            if act_row_offset > row_offset:
                bad_choices.append(i)
                continue

            # also discard if off top edge (second last resort)
            if act_row_offset+rows > maxrow:
                bad_choices.append(i)
                cut_off_selectable_chosen = 1
                continue

            return

        # anything selectable is better than what follows:
        if cut_off_selectable_chosen:
            return

        # if still none found choose the bottommost widget
        good_choices = [j for j in search_order if j not in bad_choices]
        for i in good_choices + search_order:
            row_offset, widget, pos, rows = t[i]
            if pos == focus_pos: continue

            if not rows: # never focus a 0-height widget
                continue

            # if completely within snap region, adjust row_offset
            if row_offset >= maxrow:
                snap_rows -= snap_rows+maxrow-row_offset-1
                row_offset = maxrow-1

            self.change_focus( (maxcol,maxrow), pos,
                row_offset, 'above', None,
                snap_rows )
            return


        # no choices available, just shift current one
        self.shift_focus((maxcol, maxrow), max(1-focus_rows,row_offset))

        # final check for pathological case where we may fall short
        middle, top, bottom = self.calculate_visible(
            (maxcol,maxrow), True)
        act_row_offset, _ign1, pos, _ign2, _ign3 = middle
        if act_row_offset <= row_offset:
            # no problem
            return

        # fell short, try to select anything else below
        if not t:
            return
        _ign1, _ign2, pos, _ign3 = t[-1]
        widget, pos = self._body.get_next(pos)
        if widget is None:
            # no dice, we're stuck here
            return
        # bring in only one row if possible
        rows = widget.rows((maxcol,), True)
        self.change_focus((maxcol,maxrow), pos, maxrow-1,
            'above', (self.pref_col, 0), 0 )

    def mouse_event(self, size, event, button, col, row, focus):
        """
        Pass the event to the contained widgets.
        May change focus on button 1 press.
        """
        (maxcol, maxrow) = size
        middle, top, bottom = self.calculate_visible((maxcol, maxrow),
            focus=True)
        if middle is None:
            return False

        _ignore, focus_widget, focus_pos, focus_rows, cursor = middle
        trim_top, fill_above = top
        _ignore, fill_below = bottom

        fill_above.reverse() # fill_above is in bottom-up order
        w_list = ( fill_above +
            [ (focus_widget, focus_pos, focus_rows) ] +
            fill_below )

        wrow = -trim_top
        for w, w_pos, w_rows in w_list:
            if wrow + w_rows > row:
                break
            wrow += w_rows
        else:
            return False

        focus = focus and w == focus_widget
        if is_mouse_press(event) and button==1:
            if w.selectable():
                self.change_focus((maxcol,maxrow), w_pos, wrow)

        if not hasattr(w,'mouse_event'):
            return False

        return w.mouse_event((maxcol,), event, button, col, row-wrow,
            focus)


    def ends_visible(self, size, focus=False):
        """
        Return a list that may contain ``'top'`` and/or ``'bottom'``.

        i.e. this function will return one of: [], [``'top'``],
        [``'bottom'``] or [``'top'``, ``'bottom'``].

        convenience function for checking whether the top and bottom
        of the list are visible
        """
        (maxcol, maxrow) = size
        l = []
        middle,top,bottom = self.calculate_visible( (maxcol,maxrow),
            focus=focus )
        if middle is None: # empty listbox
            return ['top','bottom']
        trim_top, above = top
        trim_bottom, below = bottom

        if trim_bottom == 0:
            row_offset, w, pos, rows, c = middle
            row_offset += rows
            for w, pos, rows in below:
                row_offset += rows
            if row_offset < maxrow:
                l.append('bottom')
            elif self._body.get_next(pos) == (None,None):
                l.append('bottom')

        if trim_top == 0:
            row_offset, w, pos, rows, c = middle
            for w, pos, rows in above:
                row_offset -= rows
            if self._body.get_prev(pos) == (None,None):
                l.insert(0, 'top')

        return l

    def __iter__(self):
        """
        Return an iterator over the positions in this ListBox.

        If self._body does not implement positions() then iterate
        from the focus widget down to the bottom, then from above
        the focus up to the top.  This is the best we can do with
        a minimal list walker implementation.
        """
        positions_fn = getattr(self._body, 'positions', None)
        if positions_fn:
            for pos in positions_fn():
                yield pos
            return

        focus_widget, focus_pos = self._body.get_focus()
        if focus_widget is None:
            return
        pos = focus_pos
        while True:
            yield pos
            w, pos = self._body.get_next(pos)
            if not w: break
        pos = focus_pos
        while True:
            w, pos = self._body.get_prev(pos)
            if not w: break
            yield pos

    def __reversed__(self):
        """
        Return a reversed iterator over the positions in this ListBox.

        If :attr:`body` does not implement :meth:`positions` then iterate
        from above the focus widget up to the top, then from the focus
        widget down to the bottom.  Note that this is not actually the
        reverse of what `__iter__()` produces, but this is the best we can
        do with a minimal list walker implementation.
        """
        positions_fn = getattr(self._body, 'positions', None)
        if positions_fn:
            for pos in positions_fn(reverse=True):
                yield pos
            return

        focus_widget, focus_pos = self._body.get_focus()
        if focus_widget is None:
            return
        pos = focus_pos
        while True:
            w, pos = self._body.get_prev(pos)
            if not w: break
            yield pos
        pos = focus_pos
        while True:
            yield pos
            w, pos = self._body.get_next(pos)
            if not w: break


