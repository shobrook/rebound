#!/usr/bin/python
#
# Urwid container widget classes
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

from itertools import chain, repeat
from urwid.compat import xrange

from urwid.util import is_mouse_press
from urwid.widget import (Widget, Divider, FLOW, FIXED, PACK, BOX, WidgetWrap,
    GIVEN, WEIGHT, LEFT, RIGHT, RELATIVE, TOP, BOTTOM, CLIP, RELATIVE_100)
from urwid.decoration import (Padding, Filler, calculate_left_right_padding,
    calculate_top_bottom_filler, normalize_align, normalize_width,
    normalize_valign, normalize_height, simplify_align, simplify_width,
    simplify_valign, simplify_height)
from urwid.monitored_list import MonitoredList, MonitoredFocusList
from urwid.canvas import (CompositeCanvas, CanvasOverlay, CanvasCombine,
    SolidCanvas, CanvasJoin)


class WidgetContainerMixin(object):
    """
    Mixin class for widget containers implementing common container methods
    """
    def __getitem__(self, position):
        """
        Container short-cut for self.contents[position][0].base_widget
        which means "give me the child widget at position without any
        widget decorations".

        This allows for concise traversal of nested container widgets
        such as:

            my_widget[position0][position1][position2] ...
        """
        return self.contents[position][0].base_widget

    def get_focus_path(self):
        """
        Return the .focus_position values starting from this container
        and proceeding along each child widget until reaching a leaf
        (non-container) widget.
        """
        out = []
        w = self
        while True:
            try:
                p = w.focus_position
            except IndexError:
                return out
            out.append(p)
            w = w.focus.base_widget

    def set_focus_path(self, positions):
        """
        Set the .focus_position property starting from this container
        widget and proceeding along newly focused child widgets.  Any
        failed assignment due do incompatible position types or invalid
        positions will raise an IndexError.

        This method may be used to restore a particular widget to the
        focus by passing in the value returned from an earlier call to
        get_focus_path().

        positions -- sequence of positions
        """
        w = self
        for p in positions:
            if p != w.focus_position:
                w.focus_position = p # modifies w.focus
            w = w.focus.base_widget

    def get_focus_widgets(self):
        """
        Return the .focus values starting from this container
        and proceeding along each child widget until reaching a leaf
        (non-container) widget.

        Note that the list does not contain the topmost container widget
        (i.e., on which this method is called), but does include the
        lowest leaf widget.
        """
        out = []
        w = self
        while True:
            w = w.base_widget.focus
            if w is None:
                return out
            out.append(w)

class WidgetContainerListContentsMixin(object):
    """
    Mixin class for widget containers whose positions are indexes into
    a list available as self.contents.
    """
    def __iter__(self):
        """
        Return an iterable of positions for this container from first
        to last.
        """
        return iter(xrange(len(self.contents)))

    def __reversed__(self):
        """
        Return an iterable of positions for this container from last
        to first.
        """
        return iter(xrange(len(self.contents) - 1, -1, -1))


class GridFlowError(Exception):
    pass

class GridFlow(WidgetWrap, WidgetContainerMixin, WidgetContainerListContentsMixin):
    """
    The GridFlow widget is a flow widget that renders all the widgets it
    contains the same width and it arranges them from left to right and top to
    bottom.
    """
    def sizing(self):
        return frozenset([FLOW])

    def __init__(self, cells, cell_width, h_sep, v_sep, align):
        """
        :param cells: list of flow widgets to display
        :param cell_width: column width for each cell
        :param h_sep: blank columns between each cell horizontally
        :param v_sep: blank rows between cells vertically
            (if more than one row is required to display all the cells)
        :param align: horizontal alignment of cells, one of\:
            'left', 'center', 'right', ('relative', percentage 0=left 100=right)
        """
        self._contents = MonitoredFocusList([
            (w, (GIVEN, cell_width)) for w in cells])
        self._contents.set_modified_callback(self._invalidate)
        self._contents.set_focus_changed_callback(lambda f: self._invalidate())
        self._contents.set_validate_contents_modified(self._contents_modified)
        self._cell_width = cell_width
        self.h_sep = h_sep
        self.v_sep = v_sep
        self.align = align
        self._cache_maxcol = None
        self.__super.__init__(None)
        # set self._w to something other than None
        self.get_display_widget(((h_sep+cell_width)*len(cells),))

    def _invalidate(self):
        self._cache_maxcol = None
        self.__super._invalidate()

    def _contents_modified(self, slc, new_items):
        for item in new_items:
            try:
                w, (t, n) = item
                if t != GIVEN:
                    raise ValueError
            except (TypeError, ValueError):
                raise GridFlowError("added content invalid %r" % (item,))

    def _get_cells(self):
        ml = MonitoredList(w for w, t in self.contents)
        def user_modified():
            self._set_cells(ml)
        ml.set_modified_callback(user_modified)
        return ml
    def _set_cells(self, widgets):
        focus_position = self.focus_position
        self.contents = [
            (new, (GIVEN, self._cell_width)) for new in widgets]
        if focus_position < len(widgets):
            self.focus_position = focus_position
    cells = property(_get_cells, _set_cells, doc="""
        A list of the widgets in this GridFlow

        .. note:: only for backwards compatibility. You should use the new
            use the new standard container property :attr:`contents` to modify
            GridFlow contents.
        """)

    def _get_cell_width(self):
        return self._cell_width
    def _set_cell_width(self, width):
        focus_position = self.focus_position
        self.contents = [
            (w, (GIVEN, width)) for (w, options) in self.contents]
        self.focus_position = focus_position
        self._cell_width = width
    cell_width = property(_get_cell_width, _set_cell_width, doc="""
        The width of each cell in the GridFlow. Setting this value affects
        all cells.
        """)

    def _get_contents(self):
        return self._contents
    def _set_contents(self, c):
        self._contents[:] = c
    contents = property(_get_contents, _set_contents, doc="""
        The contents of this GridFlow as a list of (widget, options)
        tuples.

        options is currently a tuple in the form `('fixed', number)`.
        number is the number of screen columns to allocate to this cell.
        'fixed' is the only type accepted at this time.

        This list may be modified like a normal list and the GridFlow
        widget will update automatically.

        .. seealso:: Create new options tuples with the :meth:`options` method.
        """)

    def options(self, width_type=GIVEN, width_amount=None):
        """
        Return a new options tuple for use in a GridFlow's .contents list.

        width_type -- 'given' is the only value accepted
        width_amount -- None to use the default cell_width for this GridFlow
        """
        if width_type != GIVEN:
            raise GridFlowError("invalid width_type: %r" % (width_type,))
        if width_amount is None:
            width_amount = self._cell_width
        return (width_type, width_amount)

    def set_focus(self, cell):
        """
        Set the cell in focus, for backwards compatibility.

        .. note:: only for backwards compatibility. You may also use the new
            standard container property :attr:`focus_position` to get the focus.

        :param cell: contained element to focus
        :type cell: Widget or int
        """
        if isinstance(cell, int):
            return self._set_focus_position(cell)
        return self._set_focus_cell(cell)

    def get_focus(self):
        """
        Return the widget in focus, for backwards compatibility.

        .. note:: only for backwards compatibility. You may also use the new
            standard container property :attr:`focus` to get the focus.
        """
        if not self.contents:
            return None
        return self.contents[self.focus_position][0]
    focus = property(get_focus,
        doc="the child widget in focus or None when GridFlow is empty")

    def _set_focus_cell(self, cell):
        for i, (w, options) in enumerate(self.contents):
            if cell == w:
                self.focus_position = i
                return
        raise ValueError("Widget not found in GridFlow contents: %r" % (cell,))
    focus_cell = property(get_focus, _set_focus_cell, doc="""
        The widget in focus, for backwards compatibility.

        .. note:: only for backwards compatibility. You should use the new
            use the new standard container property :attr:`focus` to get the
            widget in focus and :attr:`focus_position` to get/set the cell in
            focus by index.
        """)

    def _get_focus_position(self):
        """
        Return the index of the widget in focus or None if this GridFlow is
        empty.
        """
        if not self.contents:
            raise IndexError("No focus_position, GridFlow is empty")
        return self.contents.focus
    def _set_focus_position(self, position):
        """
        Set the widget in focus.

        position -- index of child widget to be made focus
        """
        try:
            if position < 0 or position >= len(self.contents):
                raise IndexError
        except (TypeError, IndexError):
            raise IndexError("No GridFlow child widget at position %s" % (position,))
        self.contents.focus = position
    focus_position = property(_get_focus_position, _set_focus_position, doc="""
        index of child widget in focus. Raises :exc:`IndexError` if read when
        GridFlow is empty, or when set to an invalid index.
        """)

    def get_display_widget(self, size):
        """
        Arrange the cells into columns (and possibly a pile) for
        display, input or to calculate rows, and update the display
        widget.
        """
        (maxcol,) = size
        # use cache if possible
        if self._cache_maxcol == maxcol:
            return self._w

        self._cache_maxcol = maxcol
        self._w = self.generate_display_widget(size)

        return self._w

    def generate_display_widget(self, size):
        """
        Actually generate display widget (ignoring cache)
        """
        (maxcol,) = size
        divider = Divider()
        if not self.contents:
            return divider

        if self.v_sep > 1:
            # increase size of divider
            divider.top = self.v_sep-1

        c = None
        p = Pile([])
        used_space = 0

        for i, (w, (width_type, width_amount)) in enumerate(self.contents):
            if c is None or maxcol - used_space < width_amount:
                # starting a new row
                if self.v_sep:
                    p.contents.append((divider, p.options()))
                c = Columns([], self.h_sep)
                column_focused = False
                pad = Padding(c, self.align)
                # extra attribute to reference contents position
                pad.first_position = i
                p.contents.append((pad, p.options()))

            c.contents.append((w, c.options(GIVEN, width_amount)))
            if ((i == self.focus_position) or
                (not column_focused and w.selectable())):
                c.focus_position = len(c.contents) - 1
                column_focused = True
            if i == self.focus_position:
                p.focus_position = len(p.contents) - 1
            used_space = (sum(x[1][1] for x in c.contents) +
                self.h_sep * len(c.contents))
            if width_amount > maxcol:
                # special case: display is too narrow for the given
                # width so we remove the Columns for better behaviour
                # FIXME: determine why this is necessary
                pad.original_widget=w
            pad.width = used_space - self.h_sep

        if self.v_sep:
            # remove first divider
            del p.contents[:1]

        return p

    def _set_focus_from_display_widget(self):
        """
        Set the focus to the item in focus in the display widget.
        """
        # display widget (self._w) is always built as:
        #
        # Pile([
        #     Padding(
        #         Columns([ # possibly
        #         cell, ...])),
        #     Divider(), # possibly
        #     ...])

        pile_focus = self._w.focus
        if not pile_focus:
            return
        c = pile_focus.base_widget
        if c.focus:
            col_focus_position = c.focus_position
        else:
            col_focus_position = 0
        # pad.first_position was set by generate_display_widget() above
        self.focus_position = pile_focus.first_position + col_focus_position


    def keypress(self, size, key):
        """
        Pass keypress to display widget for handling.
        Captures focus changes.
        """
        self.get_display_widget(size)
        key = self.__super.keypress(size, key)
        if key is None:
            self._set_focus_from_display_widget()
        return key

    def rows(self, size, focus=False):
        self.get_display_widget(size)
        return self.__super.rows(size, focus=focus)

    def render(self, size, focus=False ):
        self.get_display_widget(size)
        return self.__super.render(size, focus)

    def get_cursor_coords(self, size):
        """Get cursor from display widget."""
        self.get_display_widget(size)
        return self.__super.get_cursor_coords(size)

    def move_cursor_to_coords(self, size, col, row):
        """Set the widget in focus based on the col + row."""
        self.get_display_widget(size)
        rval = self.__super.move_cursor_to_coords(size, col, row)
        self._set_focus_from_display_widget()
        return rval

    def mouse_event(self, size, event, button, col, row, focus):
        self.get_display_widget(size)
        self.__super.mouse_event(size, event, button, col, row, focus)
        self._set_focus_from_display_widget()
        return True # at a minimum we adjusted our focus

    def get_pref_col(self, size):
        """Return pref col from display widget."""
        self.get_display_widget(size)
        return self.__super.get_pref_col(size)



class OverlayError(Exception):
    pass

class Overlay(Widget, WidgetContainerMixin, WidgetContainerListContentsMixin):
    """
    Overlay contains two box widgets and renders one on top of the other
    """
    _selectable = True
    _sizing = frozenset([BOX])

    _DEFAULT_BOTTOM_OPTIONS = (
        LEFT, None, RELATIVE, 100, None, 0, 0,
        TOP, None, RELATIVE, 100, None, 0, 0)

    def __init__(self, top_w, bottom_w, align, width, valign, height,
            min_width=None, min_height=None, left=0, right=0, top=0, bottom=0):
        """
        :param top_w: a flow, box or fixed widget to overlay "on top"
        :type top_w: Widget
        :param bottom_w: a box widget to appear "below" previous widget
        :type bottom_w: Widget
        :param align: alignment, one of ``'left'``, ``'center'``, ``'right'`` or
            (``'relative'``, *percentage* 0=left 100=right)
        :type align: str
        :param width: width type, one of:

            ``'pack'``
              if *top_w* is a fixed widget
            *given width*
              integer number of columns wide
            (``'relative'``, *percentage of total width*)
              make *top_w* width related to container width

        :param valign: alignment mode, one of ``'top'``, ``'middle'``, ``'bottom'`` or
            (``'relative'``, *percentage* 0=top 100=bottom)
        :param height: one of:

            ``'pack'``
              if *top_w* is a flow or fixed widget
            *given height*
              integer number of rows high
            (``'relative'``, *percentage of total height*)
              make *top_w* height related to container height
        :param min_width: the minimum number of columns for *top_w* when width
            is not fixed
        :type min_width: int
        :param min_height: minimum number of rows for *top_w* when height
            is not fixed
        :type min_height: int
        :param left: a fixed number of columns to add on the left
        :type left: int
        :param right: a fixed number of columns to add on the right
        :type right: int
        :param top: a fixed number of rows to add on the top
        :type top: int
        :param bottom: a fixed number of rows to add on the bottom
        :type bottom: int

        Overlay widgets behave similarly to :class:`Padding` and :class:`Filler`
        widgets when determining the size and position of *top_w*. *bottom_w* is
        always rendered the full size available "below" *top_w*.
        """
        self.__super.__init__()

        self.top_w = top_w
        self.bottom_w = bottom_w

        self.set_overlay_parameters(align, width, valign, height,
            min_width, min_height, left, right, top, bottom)

    def options(self, align_type, align_amount, width_type, width_amount,
            valign_type, valign_amount, height_type, height_amount,
            min_width=None, min_height=None, left=0, right=0, top=0, bottom=0):
        """
        Return a new options tuple for use in this Overlay's .contents mapping.

        This is the common container API to create options for replacing the
        top widget of this Overlay.  It is provided for completeness
        but is not necessarily the easiest way to change the overlay parameters.
        See also :meth:`.set_overlay_parameters`
        """

        return (align_type, align_amount, width_type, width_amount,
            min_width, left, right, valign_type, valign_amount,
            height_type, height_amount, min_height, top, bottom)

    def set_overlay_parameters(self, align, width, valign, height,
            min_width=None, min_height=None, left=0, right=0, top=0, bottom=0):
        """
        Adjust the overlay size and position parameters.

        See :class:`__init__() <Overlay>` for a description of the parameters.
        """

        # convert obsolete parameters 'fixed ...':
        if isinstance(align, tuple):
            if align[0] == 'fixed left':
                left = align[1]
                align = LEFT
            elif align[0] == 'fixed right':
                right = align[1]
                align = RIGHT
        if isinstance(width, tuple):
            if width[0] == 'fixed left':
                left = width[1]
                width = RELATIVE_100
            elif width[0] == 'fixed right':
                right = width[1]
                width = RELATIVE_100
        if isinstance(valign, tuple):
            if valign[0] == 'fixed top':
                top = valign[1]
                valign = TOP
            elif valign[0] == 'fixed bottom':
                bottom = valign[1]
                valign = BOTTOM
        if isinstance(height, tuple):
            if height[0] == 'fixed bottom':
                bottom = height[1]
                height = RELATIVE_100
            elif height[0] == 'fixed top':
                top = height[1]
                height = RELATIVE_100

        if width is None: # more obsolete values accepted
            width = PACK
        if height is None:
            height = PACK

        align_type, align_amount = normalize_align(align, OverlayError)
        width_type, width_amount = normalize_width(width, OverlayError)
        valign_type, valign_amount = normalize_valign(valign, OverlayError)
        height_type, height_amount = normalize_height(height, OverlayError)

        if height_type in (GIVEN, PACK):
            min_height = None

        # use container API to set the parameters
        self.contents[1] = (self.top_w, self.options(
            align_type, align_amount, width_type, width_amount,
            valign_type, valign_amount, height_type, height_amount,
            min_width, min_height, left, right, top, bottom))

    def selectable(self):
        """Return selectable from top_w."""
        return self.top_w.selectable()

    def keypress(self, size, key):
        """Pass keypress to top_w."""
        return self.top_w.keypress(self.top_w_size(size,
            *self.calculate_padding_filler(size, True)), key)

    def _get_focus(self):
        """
        Currently self.top_w is always the focus of an Overlay
        """
        return self.top_w
    focus = property(_get_focus,
        doc="the top widget in this overlay is always in focus")

    def _get_focus_position(self):
        """
        Return the top widget position (currently always 1).
        """
        return 1
    def _set_focus_position(self, position):
        """
        Set the widget in focus.  Currently only position 0 is accepted.

        position -- index of child widget to be made focus
        """
        if position != 1:
            raise IndexError("Overlay widget focus_position currently "
                "must always be set to 1, not %s" % (position,))
    focus_position = property(_get_focus_position, _set_focus_position,
        doc="index of child widget in focus, currently always 1")

    def _contents(self):
        class OverlayContents(object):
            def __len__(inner_self):
                return 2
            __getitem__ = self._contents__getitem__
            __setitem__ = self._contents__setitem__
        return OverlayContents()
    def _contents__getitem__(self, index):
        if index == 0:
            return (self.bottom_w, self._DEFAULT_BOTTOM_OPTIONS)
        if index == 1:
            return (self.top_w, (
                self.align_type, self.align_amount,
                self.width_type, self.width_amount,
                self.min_width, self.left,
                self.right, self.valign_type, self.valign_amount,
                self.height_type, self.height_amount,
                self.min_height, self.top, self.bottom))
        raise IndexError("Overlay.contents has no position %r"
            % (index,))
    def _contents__setitem__(self, index, value):
        try:
            value_w, value_options = value
        except (ValueError, TypeError):
            raise OverlayError("added content invalid: %r" % (value,))
        if index == 0:
            if value_options != self._DEFAULT_BOTTOM_OPTIONS:
                raise OverlayError("bottom_options must be set to "
                    "%r" % (self._DEFAULT_BOTTOM_OPTIONS,))
            self.bottom_w = value_w
        elif index == 1:
            try:
                (align_type, align_amount, width_type, width_amount,
                    min_width, left, right, valign_type, valign_amount,
                    height_type, height_amount, min_height, top, bottom,
                    ) = value_options
            except (ValueError, TypeError):
                raise OverlayError("top_options is invalid: %r"
                    % (value_options,))
            # normalize first, this is where errors are raised
            align_type, align_amount = normalize_align(
                simplify_align(align_type, align_amount), OverlayError)
            width_type, width_amount = normalize_width(
                simplify_width(width_type, width_amount), OverlayError)
            valign_type, valign_amoun = normalize_valign(
                simplify_valign(valign_type, valign_amount), OverlayError)
            height_type, height_amount = normalize_height(
                simplify_height(height_type, height_amount), OverlayError)
            self.align_type = align_type
            self.align_amount = align_amount
            self.width_type = width_type
            self.width_amount = width_amount
            self.valign_type = valign_type
            self.valign_amount = valign_amount
            self.height_type = height_type
            self.height_amount = height_amount
            self.left = left
            self.right = right
            self.top = top
            self.bottom = bottom
            self.min_width = min_width
            self.min_height = min_height
        else:
            raise IndexError("Overlay.contents has no position %r"
                % (index,))
        self._invalidate()
    contents = property(_contents, doc="""
        a list-like object similar to::

            [(bottom_w, bottom_options)),
             (top_w, top_options)]

        This object may be used to read or update top and bottom widgets and
        top widgets's options, but no widgets may be added or removed.

        `top_options` takes the form
        `(align_type, align_amount, width_type, width_amount, min_width, left,
        right, valign_type, valign_amount, height_type, height_amount,
        min_height, top, bottom)`

        bottom_options is always
        `('left', None, 'relative', 100, None, 0, 0,
        'top', None, 'relative', 100, None, 0, 0)`
        which means that bottom widget always covers the full area of the Overlay.
        writing a different value for `bottom_options` raises an
        :exc:`OverlayError`.
        """)

    def get_cursor_coords(self, size):
        """Return cursor coords from top_w, if any."""
        if not hasattr(self.top_w, 'get_cursor_coords'):
            return None
        (maxcol, maxrow) = size
        left, right, top, bottom = self.calculate_padding_filler(size,
            True)
        x, y = self.top_w.get_cursor_coords(
            (maxcol-left-right, maxrow-top-bottom) )
        if y >= maxrow:  # required??
            y = maxrow-1
        return x+left, y+top

    def calculate_padding_filler(self, size, focus):
        """Return (padding left, right, filler top, bottom)."""
        (maxcol, maxrow) = size
        height = None
        if self.width_type == PACK:
            width, height = self.top_w.pack((),focus=focus)
            if not height:
                raise OverlayError("fixed widget must have a height")
            left, right = calculate_left_right_padding(maxcol,
                self.align_type, self.align_amount, CLIP, width,
                None, self.left, self.right)
        else:
            left, right = calculate_left_right_padding(maxcol,
                self.align_type, self.align_amount,
                self.width_type, self.width_amount,
                self.min_width, self.left, self.right)

        if height:
            # top_w is a fixed widget
            top, bottom = calculate_top_bottom_filler(maxrow,
                self.valign_type, self.valign_amount,
                GIVEN, height, None, self.top, self.bottom)
            if maxrow-top-bottom < height:
                bottom = maxrow-top-height
        elif self.height_type == PACK:
            # top_w is a flow widget
            height = self.top_w.rows((maxcol,),focus=focus)
            top, bottom =  calculate_top_bottom_filler(maxrow,
                self.valign_type, self.valign_amount,
                GIVEN, height, None, self.top, self.bottom)
            if height > maxrow: # flow widget rendered too large
                bottom = maxrow - height
        else:
            top, bottom = calculate_top_bottom_filler(maxrow,
                self.valign_type, self.valign_amount,
                self.height_type, self.height_amount,
                self.min_height, self.top, self.bottom)
        return left, right, top, bottom

    def top_w_size(self, size, left, right, top, bottom):
        """Return the size to pass to top_w."""
        if self.width_type == PACK:
            # top_w is a fixed widget
            return ()
        maxcol, maxrow = size
        if self.width_type != PACK and self.height_type == PACK:
            # top_w is a flow widget
            return (maxcol-left-right,)
        return (maxcol-left-right, maxrow-top-bottom)


    def render(self, size, focus=False):
        """Render top_w overlayed on bottom_w."""
        left, right, top, bottom = self.calculate_padding_filler(size,
            focus)
        bottom_c = self.bottom_w.render(size)
        if not bottom_c.cols() or not bottom_c.rows():
            return CompositeCanvas(bottom_c)

        top_c = self.top_w.render(
            self.top_w_size(size, left, right, top, bottom), focus)
        top_c = CompositeCanvas(top_c)
        if left < 0 or right < 0:
            top_c.pad_trim_left_right(min(0, left), min(0, right))
        if top < 0 or bottom < 0:
            top_c.pad_trim_top_bottom(min(0, top), min(0, bottom))

        return CanvasOverlay(top_c, bottom_c, left, top)


    def mouse_event(self, size, event, button, col, row, focus):
        """Pass event to top_w, ignore if outside of top_w."""
        if not hasattr(self.top_w, 'mouse_event'):
            return False

        left, right, top, bottom = self.calculate_padding_filler(size,
            focus)
        maxcol, maxrow = size
        if ( col<left or col>=maxcol-right or
            row<top or row>=maxrow-bottom ):
            return False

        return self.top_w.mouse_event(
            self.top_w_size(size, left, right, top, bottom),
            event, button, col-left, row-top, focus )


class FrameError(Exception):
    pass

class Frame(Widget, WidgetContainerMixin):
    """
    Frame widget is a box widget with optional header and footer
    flow widgets placed above and below the box widget.

    .. note:: The main difference between a Frame and a :class:`Pile` widget
        defined as: `Pile([('pack', header), body, ('pack', footer)])` is that
        the Frame will not automatically change focus up and down in response to
        keystrokes.
    """

    _selectable = True
    _sizing = frozenset([BOX])

    def __init__(self, body, header=None, footer=None, focus_part='body'):
        """
        :param body: a box widget for the body of the frame
        :type body: Widget
        :param header: a flow widget for above the body (or None)
        :type header: Widget
        :param footer: a flow widget for below the body (or None)
        :type footer: Widget
        :param focus_part:  'header', 'footer' or 'body'
        :type focus_part: str
        """
        self.__super.__init__()

        self._header = header
        self._body = body
        self._footer = footer
        self.focus_part = focus_part

    def get_header(self):
        return self._header
    def set_header(self, header):
        self._header = header
        if header is None and self.focus_part == 'header':
            self.focus_part = 'body'
        self._invalidate()
    header = property(get_header, set_header)

    def get_body(self):
        return self._body
    def set_body(self, body):
        self._body = body
        self._invalidate()
    body = property(get_body, set_body)

    def get_footer(self):
        return self._footer
    def set_footer(self, footer):
        self._footer = footer
        if footer is None and self.focus_part == 'footer':
            self.focus_part = 'body'
        self._invalidate()
    footer = property(get_footer, set_footer)

    def set_focus(self, part):
        """
        Determine which part of the frame is in focus.

        .. note:: included for backwards compatibility. You should rather use
            the container property :attr:`.focus_position` to set this value.

        :param part: 'header', 'footer' or 'body'
        :type part: str
        """
        if part not in ('header', 'footer', 'body'):
            raise IndexError('Invalid position for Frame: %s' % (part,))
        if (part == 'header' and self._header is None) or (
                part == 'footer' and self._footer is None):
            raise IndexError('This Frame has no %s' % (part,))
        self.focus_part = part
        self._invalidate()

    def get_focus(self):
        """
        Return an indicator which part of the frame is in focus

        .. note:: included for backwards compatibility. You should rather use
            the container property :attr:`.focus_position` to get this value.

        :returns: one of 'header', 'footer' or 'body'.
        :rtype: str
        """
        return self.focus_part

    def _get_focus(self):
        return {
            'header': self._header,
            'footer': self._footer,
            'body': self._body
            }[self.focus_part]
    focus = property(_get_focus, doc="""
        child :class:`Widget` in focus: the body, header or footer widget.
        This is a read-only property.""")

    focus_position = property(get_focus, set_focus, doc="""
        writeable property containing an indicator which part of the frame
        that is in focus: `'body', 'header'` or `'footer'`.
        """)

    def _contents(self):
        class FrameContents(object):
            def __len__(inner_self):
                return len(inner_self.keys())
            def items(inner_self):
                return [(k, inner_self[k]) for k in inner_self.keys()]
            def values(inner_self):
                return [inner_self[k] for k in inner_self.keys()]
            def update(inner_self, E=None, **F):
                if E:
                    keys = getattr(E, 'keys', None)
                    if keys:
                        for k in E:
                            inner_self[k] = E[k]
                    else:
                        for k, v in E:
                            inner_self[k] = v
                for k in F:
                    inner_self[k] = F[k]
            keys = self._contents_keys
            __getitem__ = self._contents__getitem__
            __setitem__ = self._contents__setitem__
            __delitem__ = self._contents__delitem__
        return FrameContents()
    def _contents_keys(self):
        keys = ['body']
        if self._header:
            keys.append('header')
        if self._footer:
            keys.append('footer')
        return keys
    def _contents__getitem__(self, key):
        if key == 'body':
            return (self._body, None)
        if key == 'header' and self._header:
            return (self._header, None)
        if key == 'footer' and self._footer:
            return (self._footer, None)
        raise KeyError("Frame.contents has no key: %r" % (key,))
    def _contents__setitem__(self, key, value):
        if key not in ('body', 'header', 'footer'):
            raise KeyError("Frame.contents has no key: %r" % (key,))
        try:
            value_w, value_options = value
            if value_options is not None:
                raise ValueError
        except (ValueError, TypeError):
            raise FrameError("added content invalid: %r" % (value,))
        if key == 'body':
            self.body = value_w
        elif key == 'footer':
            self.footer = value_w
        else:
            self.header = value_w
    def _contents__delitem__(self, key):
        if key not in ('header', 'footer'):
            raise KeyError("Frame.contents can't remove key: %r" % (key,))
        if (key == 'header' and self._header is None
                ) or (key == 'footer' and self._footer is None):
            raise KeyError("Frame.contents has no key: %r" % (key,))
        if key == 'header':
            self.header = None
        else:
            self.footer = None
    contents = property(_contents, doc="""
        a dict-like object similar to::

            {
                'body': (body_widget, None),
                'header': (header_widget, None),  # if frame has a header
                'footer': (footer_widget, None) # if frame has a footer
            }

        This object may be used to read or update the contents of the Frame.

        The values are similar to the list-like .contents objects used
        in other containers with (:class:`Widget`, options) tuples, but are
        constrained to keys for each of the three usual parts of a Frame.
        When other keys are used a :exc:`KeyError` will be raised.

        Currently all options are `None`, but using the :meth:`options` method
        to create the options value is recommended for forwards
        compatibility.
        """)

    def options(self):
        """
        There are currently no options for Frame contents.

        Return None as a placeholder for future options.
        """
        return None

    def frame_top_bottom(self, size, focus):
        """
        Calculate the number of rows for the header and footer.

        :param size: See :meth:`Widget.render` for details
        :type size: widget size
        :param focus: ``True`` if this widget is in focus
        :type focus: bool
        :returns: `(head rows, foot rows),(orig head, orig foot)`
                  orig head/foot are from rows() calls.
        :rtype: (int, int), (int, int)
        """
        (maxcol, maxrow) = size
        frows = hrows = 0

        if self.header:
            hrows = self.header.rows((maxcol,),
                self.focus_part=='header' and focus)

        if self.footer:
            frows = self.footer.rows((maxcol,),
                self.focus_part=='footer' and focus)

        remaining = maxrow

        if self.focus_part == 'footer':
            if frows >= remaining:
                return (0, remaining),(hrows, frows)

            remaining -= frows
            if hrows >= remaining:
                return (remaining, frows),(hrows, frows)

        elif self.focus_part == 'header':
            if hrows >= maxrow:
                return (remaining, 0),(hrows, frows)

            remaining -= hrows
            if frows >= remaining:
                return (hrows, remaining),(hrows, frows)

        elif hrows + frows >= remaining:
            # self.focus_part == 'body'
            rless1 = max(0, remaining-1)
            if frows >= remaining-1:
                return (0, rless1),(hrows, frows)

            remaining -= frows
            rless1 = max(0, remaining-1)
            return (rless1,frows),(hrows, frows)

        return (hrows, frows),(hrows, frows)


    def render(self, size, focus=False):
        (maxcol, maxrow) = size
        (htrim, ftrim),(hrows, frows) = self.frame_top_bottom(
            (maxcol, maxrow), focus)

        combinelist = []
        depends_on = []

        head = None
        if htrim and htrim < hrows:
            head = Filler(self.header, 'top').render(
                (maxcol, htrim),
                focus and self.focus_part == 'header')
        elif htrim:
            head = self.header.render((maxcol,),
                focus and self.focus_part == 'header')
            assert head.rows() == hrows, "rows, render mismatch"
        if head:
            combinelist.append((head, 'header',
                self.focus_part == 'header'))
            depends_on.append(self.header)

        if ftrim+htrim < maxrow:
            body = self.body.render((maxcol, maxrow-ftrim-htrim),
                focus and self.focus_part == 'body')
            combinelist.append((body, 'body',
                self.focus_part == 'body'))
            depends_on.append(self.body)

        foot = None
        if ftrim and ftrim < frows:
            foot = Filler(self.footer, 'bottom').render(
                (maxcol, ftrim),
                focus and self.focus_part == 'footer')
        elif ftrim:
            foot = self.footer.render((maxcol,),
                focus and self.focus_part == 'footer')
            assert foot.rows() == frows, "rows, render mismatch"
        if foot:
            combinelist.append((foot, 'footer',
                self.focus_part == 'footer'))
            depends_on.append(self.footer)

        return CanvasCombine(combinelist)


    def keypress(self, size, key):
        """Pass keypress to widget in focus."""
        (maxcol, maxrow) = size

        if self.focus_part == 'header' and self.header is not None:
            if not self.header.selectable():
                return key
            return self.header.keypress((maxcol,),key)
        if self.focus_part == 'footer' and self.footer is not None:
            if not self.footer.selectable():
                return key
            return self.footer.keypress((maxcol,),key)
        if self.focus_part != 'body':
            return key
        remaining = maxrow
        if self.header is not None:
            remaining -= self.header.rows((maxcol,))
        if self.footer is not None:
            remaining -= self.footer.rows((maxcol,))
        if remaining <= 0: return key

        if not self.body.selectable():
            return key
        return self.body.keypress( (maxcol, remaining), key )


    def mouse_event(self, size, event, button, col, row, focus):
        """
        Pass mouse event to appropriate part of frame.
        Focus may be changed on button 1 press.
        """
        (maxcol, maxrow) = size
        (htrim, ftrim),(hrows, frows) = self.frame_top_bottom(
            (maxcol, maxrow), focus)

        if row < htrim: # within header
            focus = focus and self.focus_part == 'header'
            if is_mouse_press(event) and button==1:
                if self.header.selectable():
                    self.set_focus('header')
            if not hasattr(self.header, 'mouse_event'):
                return False
            return self.header.mouse_event( (maxcol,), event,
                button, col, row, focus )

        if row >= maxrow-ftrim: # within footer
            focus = focus and self.focus_part == 'footer'
            if is_mouse_press(event) and button==1:
                if self.footer.selectable():
                    self.set_focus('footer')
            if not hasattr(self.footer, 'mouse_event'):
                return False
            return self.footer.mouse_event( (maxcol,), event,
                button, col, row-maxrow+frows, focus )

        # within body
        focus = focus and self.focus_part == 'body'
        if is_mouse_press(event) and button==1:
            if self.body.selectable():
                self.set_focus('body')

        if not hasattr(self.body, 'mouse_event'):
            return False
        return self.body.mouse_event( (maxcol, maxrow-htrim-ftrim),
            event, button, col, row-htrim, focus )

    def __iter__(self):
        """
        Return an iterator over the positions in this Frame top to bottom.
        """
        if self._header:
            yield 'header'
        yield 'body'
        if self._footer:
            yield 'footer'

    def __reversed__(self):
        """
        Return an iterator over the positions in this Frame bottom to top.
        """
        if self._footer:
            yield 'footer'
        yield 'body'
        if self._header:
            yield 'header'


class PileError(Exception):
    pass

class Pile(Widget, WidgetContainerMixin, WidgetContainerListContentsMixin):
    """
    A pile of widgets stacked vertically from top to bottom
    """
    _sizing = frozenset([FLOW, BOX])

    def __init__(self, widget_list, focus_item=None):
        """
        :param widget_list: child widgets
        :type widget_list: iterable
        :param focus_item: child widget that gets the focus initially.
            Chooses the first selectable widget if unset.
        :type focus_item: Widget or int

        *widget_list* may also contain tuples such as:

        (*given_height*, *widget*)
            always treat *widget* as a box widget and give it *given_height* rows,
            where given_height is an int
        (``'pack'``, *widget*)
            allow *widget* to calculate its own height by calling its :meth:`rows`
            method, ie. treat it as a flow widget.
        (``'weight'``, *weight*, *widget*)
            if the pile is treated as a box widget then treat widget as a box
            widget with a height based on its relative weight value, otherwise
            treat the same as (``'pack'``, *widget*).

        Widgets not in a tuple are the same as (``'weight'``, ``1``, *widget*)`

        .. note:: If the Pile is treated as a box widget there must be at least
            one ``'weight'`` tuple in :attr:`widget_list`.
        """
        self.__super.__init__()
        self._contents = MonitoredFocusList()
        self._contents.set_modified_callback(self._invalidate)
        self._contents.set_focus_changed_callback(lambda f: self._invalidate())
        self._contents.set_validate_contents_modified(self._contents_modified)

        focus_item = focus_item
        for i, original in enumerate(widget_list):
            w = original
            if not isinstance(w, tuple):
                self.contents.append((w, (WEIGHT, 1)))
            elif w[0] in (FLOW, PACK):
                f, w = w
                self.contents.append((w, (PACK, None)))
            elif len(w) == 2:
                height, w = w
                self.contents.append((w, (GIVEN, height)))
            elif w[0] == FIXED: # backwards compatibility
                _ignore, height, w = w
                self.contents.append((w, (GIVEN, height)))
            elif w[0] == WEIGHT:
                f, height, w = w
                self.contents.append((w, (f, height)))
            else:
                raise PileError(
                    "initial widget list item invalid %r" % (original,))
            if focus_item is None and w.selectable():
                focus_item = i

        if self.contents and focus_item is not None:
            self.set_focus(focus_item)

        self.pref_col = 0

    def _contents_modified(self, slc, new_items):
        for item in new_items:
            try:
                w, (t, n) = item
                if t not in (PACK, GIVEN, WEIGHT):
                    raise ValueError
            except (TypeError, ValueError):
                raise PileError("added content invalid: %r" % (item,))

    def _get_widget_list(self):
        ml = MonitoredList(w for w, t in self.contents)
        def user_modified():
            self._set_widget_list(ml)
        ml.set_modified_callback(user_modified)
        return ml
    def _set_widget_list(self, widgets):
        focus_position = self.focus_position
        self.contents = [
            (new, options) for (new, (w, options)) in zip(widgets,
                # need to grow contents list if widgets is longer
                chain(self.contents, repeat((None, (WEIGHT, 1)))))]
        if focus_position < len(widgets):
            self.focus_position = focus_position
    widget_list = property(_get_widget_list, _set_widget_list, doc="""
        A list of the widgets in this Pile

        .. note:: only for backwards compatibility. You should use the new
            standard container property :attr:`contents`.
        """)

    def _get_item_types(self):
        ml = MonitoredList(
            # return the old item type names
            ({GIVEN: FIXED, PACK: FLOW}.get(f, f), height)
            for w, (f, height) in self.contents)
        def user_modified():
            self._set_item_types(ml)
        ml.set_modified_callback(user_modified)
        return ml
    def _set_item_types(self, item_types):
        focus_position = self.focus_position
        self.contents = [
            (w, ({FIXED: GIVEN, FLOW: PACK}.get(new_t, new_t), new_height))
            for ((new_t, new_height), (w, options))
            in zip(item_types, self.contents)]
        if focus_position < len(item_types):
            self.focus_position = focus_position
    item_types = property(_get_item_types, _set_item_types, doc="""
        A list of the options values for widgets in this Pile.

        .. note:: only for backwards compatibility. You should use the new
            standard container property :attr:`contents`.
        """)

    def _get_contents(self):
        return self._contents
    def _set_contents(self, c):
        self._contents[:] = c
    contents = property(_get_contents, _set_contents, doc="""
        The contents of this Pile as a list of (widget, options) tuples.

        options currently may be one of

        (``'pack'``, ``None``)
            allow widget to calculate its own height by calling its
            :meth:`rows <Widget.rows>` method, i.e. treat it as a flow widget.
        (``'given'``, *n*)
            Always treat widget as a box widget with a given height of *n* rows.
        (``'weight'``, *w*)
            If the Pile itself is treated as a box widget then
            the value *w* will be used as a relative weight for assigning rows
            to this box widget. If the Pile is being treated as a flow
            widget then this is the same as (``'pack'``, ``None``) and the *w*
            value is ignored.

        If the Pile itself is treated as a box widget then at least one
        widget must have a (``'weight'``, *w*) options value, or the Pile will
        not be able to grow to fill the required number of rows.

        This list may be modified like a normal list and the Pile widget
        will updated automatically.

        .. seealso:: Create new options tuples with the :meth:`options` method
        """)

    def options(self, height_type=WEIGHT, height_amount=1):
        """
        Return a new options tuple for use in a Pile's :attr:`contents` list.

        :param height_type: ``'pack'``, ``'given'`` or ``'weight'``
        :param height_amount: ``None`` for ``'pack'``, a number of rows for
            ``'fixed'`` or a weight value (number) for ``'weight'``
        """

        if height_type == PACK:
            return (PACK, None)
        if height_type not in (GIVEN, WEIGHT):
            raise PileError('invalid height_type: %r' % (height_type,))
        return (height_type, height_amount)

    def selectable(self):
        """Return True if the focus item is selectable."""
        w = self.focus
        return w is not None and w.selectable()

    def set_focus(self, item):
        """
        Set the item in focus, for backwards compatibility.

        .. note:: only for backwards compatibility. You should use the new
            standard container property :attr:`focus_position`.
            to set the position by integer index instead.

        :param item: element to focus
        :type item: Widget or int
        """
        if isinstance(item, int):
            return self._set_focus_position(item)
        for i, (w, options) in enumerate(self.contents):
            if item == w:
                self.focus_position = i
                return
        raise ValueError("Widget not found in Pile contents: %r" % (item,))

    def get_focus(self):
        """
        Return the widget in focus, for backwards compatibility.  You may
        also use the new standard container property .focus to get the
        child widget in focus.
        """
        if not self.contents:
            return None
        return self.contents[self.focus_position][0]
    focus = property(get_focus,
        doc="the child widget in focus or None when Pile is empty")

    focus_item = property(get_focus, set_focus, doc="""
        A property for reading and setting the widget in focus.

        .. note::

            only for backwards compatibility. You should use the new
            standard container properties :attr:`focus` and
            :attr:`focus_position` to get the child widget in focus or modify the
            focus position.
        """)

    def _get_focus_position(self):
        """
        Return the index of the widget in focus or None if this Pile is
        empty.
        """
        if not self.contents:
            raise IndexError("No focus_position, Pile is empty")
        return self.contents.focus
    def _set_focus_position(self, position):
        """
        Set the widget in focus.

        position -- index of child widget to be made focus
        """
        try:
            if position < 0 or position >= len(self.contents):
                raise IndexError
        except (TypeError, IndexError):
            raise IndexError("No Pile child widget at position %s" % (position,))
        self.contents.focus = position
    focus_position = property(_get_focus_position, _set_focus_position, doc="""
        index of child widget in focus. Raises :exc:`IndexError` if read when
        Pile is empty, or when set to an invalid index.
        """)

    def get_pref_col(self, size):
        """Return the preferred column for the cursor, or None."""
        if not self.selectable():
            return None
        self._update_pref_col_from_focus(size)
        return self.pref_col

    def get_item_size(self, size, i, focus, item_rows=None):
        """
        Return a size appropriate for passing to self.contents[i][0].render
        """
        maxcol = size[0]
        w, (f, height) = self.contents[i]
        if f == GIVEN:
            return (maxcol, height)
        elif f == WEIGHT and len(size) == 2:
            if not item_rows:
                item_rows = self.get_item_rows(size, focus)
            return (maxcol, item_rows[i])
        else:
            return (maxcol,)

    def get_item_rows(self, size, focus):
        """
        Return a list of the number of rows used by each widget
        in self.contents
        """
        remaining = None
        maxcol = size[0]
        if len(size) == 2:
            remaining = size[1]

        l = []

        if remaining is None:
            # pile is a flow widget
            for w, (f, height) in self.contents:
                if f == GIVEN:
                    l.append(height)
                else:
                    l.append(w.rows((maxcol,),
                        focus=focus and self.focus_item == w))
            return l

        # pile is a box widget
        # do an extra pass to calculate rows for each widget
        wtotal = 0
        for w, (f, height) in self.contents:
            if f == PACK:
                rows = w.rows((maxcol,), focus=focus and self.focus_item == w)
                l.append(rows)
                remaining -= rows
            elif f == GIVEN:
                l.append(height)
                remaining -= height
            elif height:
                l.append(None)
                wtotal += height
            else:
                l.append(0) # zero-weighted items treated as ('given', 0)

        if wtotal == 0:
            raise PileError("No weighted widgets found for Pile treated as a box widget")

        if remaining < 0:
            remaining = 0

        for i, (w, (f, height)) in enumerate(self.contents):
            li = l[i]
            if li is None:
                rows = int(float(remaining) * height / wtotal + 0.5)
                l[i] = rows
                remaining -= rows
                wtotal -= height
        return l

    def render(self, size, focus=False):
        maxcol = size[0]
        item_rows = None

        combinelist = []
        for i, (w, (f, height)) in enumerate(self.contents):
            item_focus = self.focus_item == w
            canv = None
            if f == GIVEN:
                canv = w.render((maxcol, height), focus=focus and item_focus)
            elif f == PACK or len(size)==1:
                canv = w.render((maxcol,), focus=focus and item_focus)
            else:
                if item_rows is None:
                    item_rows = self.get_item_rows(size, focus)
                rows = item_rows[i]
                if rows>0:
                    canv = w.render((maxcol, rows), focus=focus and item_focus)
            if canv:
                combinelist.append((canv, i, item_focus))
        if not combinelist:
            return SolidCanvas(" ", size[0], (size[1:]+(0,))[0])

        out = CanvasCombine(combinelist)
        if len(size) == 2 and size[1] != out.rows():
            # flow/fixed widgets rendered too large/small
            out = CompositeCanvas(out)
            out.pad_trim_top_bottom(0, size[1] - out.rows())
        return out

    def get_cursor_coords(self, size):
        """Return the cursor coordinates of the focus widget."""
        if not self.selectable():
            return None
        if not hasattr(self.focus_item, 'get_cursor_coords'):
            return None

        i = self.focus_position
        w, (f, height) = self.contents[i]
        item_rows = None
        maxcol = size[0]
        if f == GIVEN or (f == WEIGHT and len(size) == 2):
            if f == GIVEN:
                maxrow = height
            else:
                if item_rows is None:
                    item_rows = self.get_item_rows(size, focus=True)
                maxrow = item_rows[i]
            coords = self.focus_item.get_cursor_coords((maxcol, maxrow))
        else:
            coords = self.focus_item.get_cursor_coords((maxcol,))

        if coords is None:
            return None
        x,y = coords
        if i > 0:
            if item_rows is None:
                item_rows = self.get_item_rows(size, focus=True)
            for r in item_rows[:i]:
                y += r
        return x, y

    def rows(self, size, focus=False ):
        return sum(self.get_item_rows(size, focus))

    def keypress(self, size, key ):
        """Pass the keypress to the widget in focus.
        Unhandled 'up' and 'down' keys may cause a focus change."""
        if not self.contents:
            return key

        item_rows = None
        if len(size) == 2:
            item_rows = self.get_item_rows(size, focus=True)

        i = self.focus_position
        if self.selectable():
            tsize = self.get_item_size(size, i, True, item_rows)
            key = self.focus.keypress(tsize, key)
            if self._command_map[key] not in ('cursor up', 'cursor down'):
                return key

        if self._command_map[key] == 'cursor up':
            candidates = list(range(i-1, -1, -1)) # count backwards to 0
        else: # self._command_map[key] == 'cursor down'
            candidates = list(range(i+1, len(self.contents)))

        if not item_rows:
            item_rows = self.get_item_rows(size, focus=True)

        for j in candidates:
            if not self.contents[j][0].selectable():
                continue

            self._update_pref_col_from_focus(size)
            self.focus_position = j
            if not hasattr(self.focus, 'move_cursor_to_coords'):
                return

            rows = item_rows[j]
            if self._command_map[key] == 'cursor up':
                rowlist = list(range(rows-1, -1, -1))
            else: # self._command_map[key] == 'cursor down'
                rowlist = list(range(rows))
            for row in rowlist:
                tsize = self.get_item_size(size, j, True, item_rows)
                if self.focus_item.move_cursor_to_coords(
                        tsize, self.pref_col, row):
                    break
            return

        # nothing to select
        return key

    def _update_pref_col_from_focus(self, size):
        """Update self.pref_col from the focus widget."""

        if not hasattr(self.focus, 'get_pref_col'):
            return
        i = self.focus_position
        tsize = self.get_item_size(size, i, True)
        pref_col = self.focus.get_pref_col(tsize)
        if pref_col is not None:
            self.pref_col = pref_col

    def move_cursor_to_coords(self, size, col, row):
        """Capture pref col and set new focus."""
        self.pref_col = col

        #FIXME guessing focus==True
        focus=True
        wrow = 0
        item_rows = self.get_item_rows(size, focus)
        for i, (r, w) in enumerate(zip(item_rows,
                (w for (w, options) in self.contents))):
            if wrow + r > row:
                break
            wrow += r
        else:
            return False

        if not w.selectable():
            return False

        if hasattr(w, 'move_cursor_to_coords'):
            tsize = self.get_item_size(size, i, focus, item_rows)
            rval = w.move_cursor_to_coords(tsize, col, row-wrow)
            if rval is False:
                return False

        self.focus_position = i
        return True

    def mouse_event(self, size, event, button, col, row, focus):
        """
        Pass the event to the contained widget.
        May change focus on button 1 press.
        """
        wrow = 0
        item_rows = self.get_item_rows(size, focus)
        for i, (r, w) in enumerate(zip(item_rows,
                (w for (w, options) in self.contents))):
            if wrow + r > row:
                break
            wrow += r
        else:
            return False

        focus = focus and self.focus_item == w
        if is_mouse_press(event) and button == 1:
            if w.selectable():
                self.focus_position = i

        if not hasattr(w, 'mouse_event'):
            return False

        tsize = self.get_item_size(size, i, focus, item_rows)
        return w.mouse_event(tsize, event, button, col, row-wrow,
            focus)



class ColumnsError(Exception):
    pass


class Columns(Widget, WidgetContainerMixin, WidgetContainerListContentsMixin):
    """
    Widgets arranged horizontally in columns from left to right
    """
    _sizing = frozenset([FLOW, BOX])

    def __init__(self, widget_list, dividechars=0, focus_column=None,
        min_width=1, box_columns=None):
        """
        :param widget_list: iterable of flow or box widgets
        :param dividechars: number of blank characters between columns
        :param focus_column: index into widget_list of column in focus,
            if ``None`` the first selectable widget will be chosen.
        :param min_width: minimum width for each column which is not
            calling widget.pack() in *widget_list*.
        :param box_columns: a list of column indexes containing box widgets
            whose height is set to the maximum of the rows
            required by columns not listed in *box_columns*.

        *widget_list* may also contain tuples such as:

        (*given_width*, *widget*)
            make this column *given_width* screen columns wide, where *given_width*
            is an int
        (``'pack'``, *widget*)
            call :meth:`pack() <Widget.pack>` to calculate the width of this column
        (``'weight'``, *weight*, *widget*)
            give this column a relative *weight* (number) to calculate its width from the
            screen columns remaining

        Widgets not in a tuple are the same as (``'weight'``, ``1``, *widget*)

        If the Columns widget is treated as a box widget then all children
        are treated as box widgets, and *box_columns* is ignored.

        If the Columns widget is treated as a flow widget then the rows
        are calculated as the largest rows() returned from all columns
        except the ones listed in *box_columns*.  The box widgets in
        *box_columns* will be displayed with this calculated number of rows,
        filling the full height.
        """
        self.__super.__init__()
        self._contents = MonitoredFocusList()
        self._contents.set_modified_callback(self._invalidate)
        self._contents.set_focus_changed_callback(lambda f: self._invalidate())
        self._contents.set_validate_contents_modified(self._contents_modified)

        box_columns = set(box_columns or ())

        for i, original in enumerate(widget_list):
            w = original
            if not isinstance(w, tuple):
                self.contents.append((w, (WEIGHT, 1, i in box_columns)))
            elif w[0] in (FLOW, PACK): # 'pack' used to be called 'flow'
                f = PACK
                _ignored, w = w
                self.contents.append((w, (f, None, i in box_columns)))
            elif len(w) == 2:
                width, w = w
                self.contents.append((w, (GIVEN, width, i in box_columns)))
            elif w[0] == FIXED: # backwards compatibility
                f = GIVEN
                _ignored, width, w = w
                self.contents.append((w, (GIVEN, width, i in box_columns)))
            elif w[0] == WEIGHT:
                f, width, w = w
                self.contents.append((w, (f, width, i in box_columns)))
            else:
                raise ColumnsError(
                    "initial widget list item invalid: %r" % (original,))
            if focus_column is None and w.selectable():
                focus_column = i

        self.dividechars = dividechars

        if self.contents and focus_column is not None:
            self.focus_position = focus_column
        if focus_column is None:
            focus_column = 0
        self.pref_col = None
        self.min_width = min_width
        self._cache_maxcol = None

    def _contents_modified(self, slc, new_items):
        for item in new_items:
            try:
                w, (t, n, b) = item
                if t not in (PACK, GIVEN, WEIGHT):
                    raise ValueError
            except (TypeError, ValueError):
                raise ColumnsError("added content invalid %r" % (item,))

    def _get_widget_list(self):
        ml = MonitoredList(w for w, t in self.contents)
        def user_modified():
            self._set_widget_list(ml)
        ml.set_modified_callback(user_modified)
        return ml
    def _set_widget_list(self, widgets):
        focus_position = self.focus_position
        self.contents = [
            (new, options) for (new, (w, options)) in zip(widgets,
                # need to grow contents list if widgets is longer
                chain(self.contents, repeat((None, (WEIGHT, 1, False)))))]
        if focus_position < len(widgets):
            self.focus_position = focus_position
    widget_list = property(_get_widget_list, _set_widget_list, doc="""
        A list of the widgets in this Columns

        .. note:: only for backwards compatibility. You should use the new
            standard container property :attr:`contents`.
        """)

    def _get_column_types(self):
        ml = MonitoredList(
            # return the old column type names
            ({GIVEN: FIXED, PACK: FLOW}.get(t, t), n)
            for w, (t, n, b) in self.contents)
        def user_modified():
            self._set_column_types(ml)
        ml.set_modified_callback(user_modified)
        return ml
    def _set_column_types(self, column_types):
        focus_position = self.focus_position
        self.contents = [
            (w, ({FIXED: GIVEN, FLOW: PACK}.get(new_t, new_t), new_n, b))
            for ((new_t, new_n), (w, (t, n, b)))
            in zip(column_types, self.contents)]
        if focus_position < len(column_types):
            self.focus_position = focus_position
    column_types = property(_get_column_types, _set_column_types, doc="""
        A list of the old partial options values for widgets in this Pile,
        for backwards compatibility only.  You should use the new standard
        container property .contents to modify Pile contents.
        """)

    def _get_box_columns(self):
        ml = MonitoredList(
            i for i, (w, (t, n, b)) in enumerate(self.contents) if b)
        def user_modified():
            self._set_box_columns(ml)
        ml.set_modified_callback(user_modified)
        return ml
    def _set_box_columns(self, box_columns):
        box_columns = set(box_columns)
        self.contents = [
            (w, (t, n, i in box_columns))
            for (i, (w, (t, n, b))) in enumerate(self.contents)]
    box_columns = property(_get_box_columns, _set_box_columns, doc="""
        A list of the indexes of the columns that are to be treated as
        box widgets when the Columns is treated as a flow widget.

        .. note:: only for backwards compatibility. You should use the new
            standard container property :attr:`contents`.
        """)

    def _get_has_pack_type(self):
        import warnings
        warnings.warn(".has_flow_type is deprecated, "
            "read values from .contents instead.", DeprecationWarning)
        return PACK in self.column_types
    def _set_has_pack_type(self, value):
        import warnings
        warnings.warn(".has_flow_type is deprecated, "
            "read values from .contents instead.", DeprecationWarning)
    has_flow_type = property(_get_has_pack_type, _set_has_pack_type, doc="""
        .. deprecated:: 1.0 Read values from :attr:`contents` instead.
        """)

    def _get_contents(self):
        return self._contents
    def _set_contents(self, c):
        self._contents[:] = c
    contents = property(_get_contents, _set_contents, doc="""
        The contents of this Columns as a list of `(widget, options)` tuples.
        This list may be modified like a normal list and the Columns
        widget will update automatically.

        .. seealso:: Create new options tuples with the :meth:`options` method
        """)

    def options(self, width_type=WEIGHT, width_amount=1, box_widget=False):
        """
        Return a new options tuple for use in a Pile's .contents list.

        This sets an entry's width type: one of the following:

        ``'pack'``
            Call the widget's :meth:`Widget.pack` method to determine how wide
            this column should be. *width_amount* is ignored.
        ``'given'``
            Make column exactly width_amount screen-columns wide.
        ``'weight'``
            Allocate the remaining space to this column by using
            *width_amount* as a weight value.

        :param width_type: ``'pack'``, ``'given'`` or ``'weight'``
        :param width_amount: ``None`` for ``'pack'``, a number of screen columns
            for ``'given'`` or a weight value (number) for ``'weight'``
        :param box_widget: set to `True` if this widget is to be treated as a box
            widget when the Columns widget itself is treated as a flow widget.
        :type box_widget: bool
        """
        if width_type == PACK:
            width_amount = None
        if width_type not in (PACK, GIVEN, WEIGHT):
            raise ColumnsError('invalid width_type: %r' % (width_type,))
        return (width_type, width_amount, box_widget)

    def _invalidate(self):
        self._cache_maxcol = None
        self.__super._invalidate()

    def set_focus_column(self, num):
        """
        Set the column in focus by its index in :attr:`widget_list`.

        :param num: index of focus-to-be entry
        :type num: int

        .. note:: only for backwards compatibility. You may also use the new
            standard container property :attr:`focus_position` to set the focus.
        """
        self._set_focus_position(num)

    def get_focus_column(self):
        """
        Return the focus column index.

        .. note:: only for backwards compatibility. You may also use the new
            standard container property :attr:`focus_position` to get the focus.
        """
        return self.focus_position

    def set_focus(self, item):
        """
        Set the item in focus

        .. note:: only for backwards compatibility. You may also use the new
            standard container property :attr:`focus_position` to get the focus.

        :param item: widget or integer index"""
        if isinstance(item, int):
            return self._set_focus_position(item)
        for i, (w, options) in enumerate(self.contents):
            if item == w:
                self.focus_position = i
                return
        raise ValueError("Widget not found in Columns contents: %r" % (item,))

    def get_focus(self):
        """
        Return the widget in focus, for backwards compatibility.  You may
        also use the new standard container property .focus to get the
        child widget in focus.
        """
        if not self.contents:
            return None
        return self.contents[self.focus_position][0]
    focus = property(get_focus,
        doc="the child widget in focus or None when Columns is empty")

    def _get_focus_position(self):
        """
        Return the index of the widget in focus or None if this Columns is
        empty.
        """
        if not self.widget_list:
            raise IndexError("No focus_position, Columns is empty")
        return self.contents.focus
    def _set_focus_position(self, position):
        """
        Set the widget in focus.

        position -- index of child widget to be made focus
        """
        try:
            if position < 0 or position >= len(self.contents):
                raise IndexError
        except (TypeError, IndexError):
            raise IndexError("No Columns child widget at position %s" % (position,))
        self.contents.focus = position
    focus_position = property(_get_focus_position, _set_focus_position, doc="""
        index of child widget in focus. Raises :exc:`IndexError` if read when
        Columns is empty, or when set to an invalid index.
        """)

    focus_col = property(_get_focus_position, _set_focus_position, doc="""
        A property for reading and setting the index of the column in
        focus.

        .. note:: only for backwards compatibility. You may also use the new
            standard container property :attr:`focus_position` to get the focus.
        """)

    def column_widths(self, size, focus=False):
        """
        Return a list of column widths.

        0 values in the list mean hide corresponding column completely
        """
        maxcol = size[0]
        # FIXME: get rid of this check and recalculate only when
        # a 'pack' widget has been modified.
        if maxcol == self._cache_maxcol and not any(
                t == PACK for w, (t, n, b) in self.contents):
            return self._cache_column_widths

        widths = []

        weighted = []
        shared = maxcol + self.dividechars

        for i, (w, (t, width, b)) in enumerate(self.contents):
            if t == GIVEN:
                static_w = width
            elif t == PACK:
                # FIXME: should be able to pack with a different
                # maxcol value
                static_w = w.pack((maxcol,), focus)[0]
            else:
                static_w = self.min_width

            if shared < static_w + self.dividechars and i > self.focus_position:
                break

            widths.append(static_w)
            shared -= static_w + self.dividechars
            if t not in (GIVEN, PACK):
                weighted.append((width, i))

        # drop columns on the left until we fit
        for i, w in enumerate(widths):
            if shared >= 0:
                break
            shared += widths[i] + self.dividechars
            widths[i] = 0
            if weighted and weighted[0][1] == i:
                del weighted[0]

        if shared:
            # divide up the remaining space between weighted cols
            weighted.sort()
            wtotal = sum(weight for weight, i in weighted)
            grow = shared + len(weighted) * self.min_width
            for weight, i in weighted:
                width = int(float(grow) * weight / wtotal + 0.5)
                width = max(self.min_width, width)
                widths[i] = width
                grow -= width
                wtotal -= weight

        self._cache_maxcol = maxcol
        self._cache_column_widths = widths
        return widths

    def render(self, size, focus=False):
        """
        Render columns and return canvas.

        :param size: see :meth:`Widget.render` for details
        :param focus: ``True`` if this widget is in focus
        :type focus: bool
        """
        widths = self.column_widths(size, focus)

        box_maxrow = None
        if len(size) == 1:
            box_maxrow = 1
            # two-pass mode to determine maxrow for box columns
            for i, (mc, (w, (t, n, b))) in enumerate(zip(widths, self.contents)):
                if b:
                    continue
                rows = w.rows((mc,),
                    focus = focus and self.focus_position == i)
                box_maxrow = max(box_maxrow, rows)

        l = []
        for i, (mc, (w, (t, n, b))) in enumerate(zip(widths, self.contents)):
            # if the widget has a width of 0, hide it
            if mc <= 0:
                continue

            if box_maxrow and b:
                sub_size = (mc, box_maxrow)
            else:
                sub_size = (mc,) + size[1:]

            canv = w.render(sub_size,
                focus = focus and self.focus_position == i)

            if i < len(widths) - 1:
                mc += self.dividechars
            l.append((canv, i, self.focus_position == i, mc))

        if not l:
            return SolidCanvas(" ", size[0], (size[1:]+(1,))[0])

        canv = CanvasJoin(l)
        if canv.cols() < size[0]:
            canv.pad_trim_left_right(0, size[0] - canv.cols())
        return canv

    def get_cursor_coords(self, size):
        """Return the cursor coordinates from the focus widget."""
        w, (t, n, b) = self.contents[self.focus_position]

        if not w.selectable():
            return None
        if not hasattr(w, 'get_cursor_coords'):
            return None

        widths = self.column_widths(size)
        if len(widths) <= self.focus_position:
            return None
        colw = widths[self.focus_position]

        if len(size) == 1 and b:
            coords = w.get_cursor_coords((colw, self.rows(size)))
        else:
            coords = w.get_cursor_coords((colw,)+size[1:])
        if coords is None:
            return None
        x, y = coords
        x += sum([self.dividechars + wc
            for wc in widths[:self.focus_position] if wc > 0])
        return x, y

    def move_cursor_to_coords(self, size, col, row):
        """
        Choose a selectable column to focus based on the coords.

        see :meth:`Widget.move_cursor_coords` for details
        """
        widths = self.column_widths(size)

        best = None
        x = 0
        for i, (width, (w, options)) in enumerate(zip(widths, self.contents)):
            end = x + width
            if w.selectable():
                if col != RIGHT and (col == LEFT or x > col) and best is None:
                    # no other choice
                    best = i, x, end, w, options
                    break
                if col != RIGHT and x > col and col-best[2] < x-col:
                    # choose one on left
                    break
                best = i, x, end, w, options
                if col != RIGHT and col < end:
                    # choose this one
                    break
            x = end + self.dividechars

        if best is None:
            return False
        i, x, end, w, (t, n, b) = best
        if hasattr(w, 'move_cursor_to_coords'):
            if isinstance(col, int):
                move_x = min(max(0, col - x), end - x - 1)
            else:
                move_x = col
            if len(size) == 1 and b:
                rval = w.move_cursor_to_coords((end - x, self.rows(size)),
                    move_x, row)
            else:
                rval = w.move_cursor_to_coords((end - x,) + size[1:],
                    move_x, row)
            if rval is False:
                return False

        self.focus_position = i
        self.pref_col = col
        return True

    def mouse_event(self, size, event, button, col, row, focus):
        """
        Send event to appropriate column.
        May change focus on button 1 press.
        """
        widths = self.column_widths(size)

        x = 0
        for i, (width, (w, (t, n, b))) in enumerate(zip(widths, self.contents)):
            if col < x:
                return False
            w = self.widget_list[i]
            end = x + width

            if col >= end:
                x = end + self.dividechars
                continue

            focus = focus and self.focus_col == i
            if is_mouse_press(event) and button == 1:
                if w.selectable():
                    self.focus_position = i

            if not hasattr(w, 'mouse_event'):
                return False

            if len(size) == 1 and b:
                return w.mouse_event((end - x, self.rows(size)), event, button,
                    col - x, row, focus)
            return w.mouse_event((end - x,) + size[1:], event, button,
                col - x, row, focus)
        return False

    def get_pref_col(self, size):
        """Return the pref col from the column in focus."""
        widths = self.column_widths(size)

        w, (t, n, b) = self.contents[self.focus_position]
        if len(widths) <= self.focus_position:
            return 0
        col = None
        cwidth = widths[self.focus_position]
        if hasattr(w, 'get_pref_col'):
            if len(size) == 1 and b:
                col = w.get_pref_col((cwidth, self.rows(size)))
            else:
                col = w.get_pref_col((cwidth,) + size[1:])
            if isinstance(col, int):
                col += self.focus_col * self.dividechars
                col += sum(widths[:self.focus_position])
        if col is None:
            col = self.pref_col
        if col is None and w.selectable():
            col = cwidth // 2
            col += self.focus_position * self.dividechars
            col += sum(widths[:self.focus_position] )
        return col

    def rows(self, size, focus=False):
        """
        Return the number of rows required by the columns.
        This only makes sense if :attr:`widget_list` contains flow widgets.

        see :meth:`Widget.rows` for details
        """
        widths = self.column_widths(size, focus)

        rows = 1
        for i, (mc, (w, (t, n, b))) in enumerate(zip(widths, self.contents)):
            if b:
                continue
            rows = max(rows,
                w.rows((mc,), focus=focus and self.focus_position == i))
        return rows

    def keypress(self, size, key):
        """
        Pass keypress to the focus column.

        :param size: `(maxcol,)` if :attr:`widget_list` contains flow widgets or
            `(maxcol, maxrow)` if it contains box widgets.
        :type size: int, int
        """
        if self.focus_position is None: return key

        widths = self.column_widths(size)
        if self.focus_position >= len(widths):
            return key

        i = self.focus_position
        mc = widths[i]
        w, (t, n, b) = self.contents[i]
        if self._command_map[key] not in ('cursor up', 'cursor down',
            'cursor page up', 'cursor page down'):
            self.pref_col = None
        if len(size) == 1 and b:
            key = w.keypress((mc, self.rows(size, True)), key)
        else:
            key = w.keypress((mc,) + size[1:], key)

        if self._command_map[key] not in ('cursor left', 'cursor right'):
            return key

        if self._command_map[key] == 'cursor left':
            candidates = list(range(i-1, -1, -1)) # count backwards to 0
        else: # key == 'right'
            candidates = list(range(i+1, len(self.contents)))

        for j in candidates:
            if not self.contents[j][0].selectable():
                continue

            self.focus_position = j
            return
        return key


    def selectable(self):
        """Return the selectable value of the focus column."""
        w = self.focus
        return w is not None and w.selectable()






def _test():
    import doctest
    doctest.testmod()

if __name__=='__main__':
    _test()
