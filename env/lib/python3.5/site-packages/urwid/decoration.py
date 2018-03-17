#!/usr/bin/python
#
# Urwid widget decoration classes
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

from urwid.util import int_scale
from urwid.widget import (Widget, WidgetError,
    BOX, FLOW, LEFT, CENTER, RIGHT, PACK, CLIP, GIVEN, RELATIVE, RELATIVE_100,
    TOP, MIDDLE, BOTTOM, delegate_to_widget_mixin)
from urwid.split_repr import remove_defaults
from urwid.canvas import CompositeCanvas, SolidCanvas
from urwid.widget import Divider, Edit, Text, SolidFill # doctests


class WidgetDecoration(Widget):  # "decorator" was already taken
    """
    original_widget -- the widget being decorated

    This is a base class for decoration widgets, widgets
    that contain one or more widgets and only ever have
    a single focus.  This type of widget will affect the
    display or behaviour of the original_widget but it is
    not part of determining a chain of focus.

    Don't actually do this -- use a WidgetDecoration subclass
    instead, these are not real widgets:

    >>> WidgetDecoration(Text(u"hi"))
    <WidgetDecoration flow widget <Text flow widget 'hi'>>
    """
    def __init__(self, original_widget):
        self._original_widget = original_widget
    def _repr_words(self):
        return self.__super._repr_words() + [repr(self._original_widget)]

    def _get_original_widget(self):
        return self._original_widget
    def _set_original_widget(self, original_widget):
        self._original_widget = original_widget
        self._invalidate()
    original_widget = property(_get_original_widget, _set_original_widget)

    def _get_base_widget(self):
        """
        Return the widget without decorations.  If there is only one
        Decoration then this is the same as original_widget.

        >>> t = Text('hello')
        >>> wd1 = WidgetDecoration(t)
        >>> wd2 = WidgetDecoration(wd1)
        >>> wd3 = WidgetDecoration(wd2)
        >>> wd3.original_widget is wd2
        True
        >>> wd3.base_widget is t
        True
        """
        w = self
        while hasattr(w, '_original_widget'):
            w = w._original_widget
        return w

    base_widget = property(_get_base_widget)

    def selectable(self):
        return self._original_widget.selectable()

    def sizing(self):
        return self._original_widget.sizing()


class WidgetPlaceholder(delegate_to_widget_mixin('_original_widget'),
        WidgetDecoration):
    """
    This is a do-nothing decoration widget that can be used for swapping
    between widgets without modifying the container of this widget.

    This can be useful for making an interface with a number of distinct
    pages or for showing and hiding menu or status bars.

    The widget displayed is stored as the self.original_widget property and
    can be changed by assigning a new widget to it.
    """
    pass


class AttrMapError(WidgetError):
    pass

class AttrMap(delegate_to_widget_mixin('_original_widget'), WidgetDecoration):
    """
    AttrMap is a decoration that maps one set of attributes to another.
    This object will pass all function calls and variable references to the
    wrapped widget.
    """
    def __init__(self, w, attr_map, focus_map=None):
        """
        :param w: widget to wrap (stored as self.original_widget)
        :type w: widget

        :param attr_map: attribute to apply to *w*, or dict of old display
            attribute: new display attribute mappings
        :type attr_map: display attribute or dict

        :param focus_map: attribute to apply when in focus or dict of
            old display attribute: new display attribute mappings;
            if ``None`` use *attr*
        :type focus_map: display attribute or dict

        >>> AttrMap(Divider(u"!"), 'bright')
        <AttrMap flow widget <Divider flow widget '!'> attr_map={None: 'bright'}>
        >>> AttrMap(Edit(), 'notfocus', 'focus')
        <AttrMap selectable flow widget <Edit selectable flow widget '' edit_pos=0> attr_map={None: 'notfocus'} focus_map={None: 'focus'}>
        >>> size = (5,)
        >>> am = AttrMap(Text(u"hi"), 'greeting', 'fgreet')
        >>> next(am.render(size, focus=False).content()) # ... = b in Python 3
        [('greeting', None, ...'hi   ')]
        >>> next(am.render(size, focus=True).content())
        [('fgreet', None, ...'hi   ')]
        >>> am2 = AttrMap(Text(('word', u"hi")), {'word':'greeting', None:'bg'})
        >>> am2
        <AttrMap flow widget <Text flow widget 'hi'> attr_map={'word': 'greeting', None: 'bg'}>
        >>> next(am2.render(size).content())
        [('greeting', None, ...'hi'), ('bg', None, ...'   ')]
        """
        self.__super.__init__(w)

        if type(attr_map) != dict:
            self.set_attr_map({None: attr_map})
        else:
            self.set_attr_map(attr_map)

        if focus_map is not None and type(focus_map) != dict:
            self.set_focus_map({None: focus_map})
        else:
            self.set_focus_map(focus_map)

    def _repr_attrs(self):
        # only include the focus_attr when it takes effect (not None)
        d = dict(self.__super._repr_attrs(), attr_map=self._attr_map)
        if self._focus_map is not None:
            d['focus_map'] = self._focus_map
        return d

    def get_attr_map(self):
        # make a copy so ours is not accidentally modified
        # FIXME: a dictionary that detects modifications would be better
        return dict(self._attr_map)
    def set_attr_map(self, attr_map):
        """
        Set the attribute mapping dictionary {from_attr: to_attr, ...}

        Note this function does not accept a single attribute the way the
        constructor does.  You must specify {None: attribute} instead.

        >>> w = AttrMap(Text(u"hi"), None)
        >>> w.set_attr_map({'a':'b'})
        >>> w
        <AttrMap flow widget <Text flow widget 'hi'> attr_map={'a': 'b'}>
        """
        for from_attr, to_attr in attr_map.items():
            if not from_attr.__hash__ or not to_attr.__hash__:
                raise AttrMapError("%r:%r attribute mapping is invalid.  "
                    "Attributes must be hashable" % (from_attr, to_attr))
        self._attr_map = attr_map
        self._invalidate()
    attr_map = property(get_attr_map, set_attr_map)

    def get_focus_map(self):
        # make a copy so ours is not accidentally modified
        # FIXME: a dictionary that detects modifications would be better
        if self._focus_map:
            return dict(self._focus_map)
    def set_focus_map(self, focus_map):
        """
        Set the focus attribute mapping dictionary
        {from_attr: to_attr, ...}

        If None this widget will use the attr mapping instead (no change
        when in focus).

        Note this function does not accept a single attribute the way the
        constructor does.  You must specify {None: attribute} instead.

        >>> w = AttrMap(Text(u"hi"), {})
        >>> w.set_focus_map({'a':'b'})
        >>> w
        <AttrMap flow widget <Text flow widget 'hi'> attr_map={} focus_map={'a': 'b'}>
        >>> w.set_focus_map(None)
        >>> w
        <AttrMap flow widget <Text flow widget 'hi'> attr_map={}>
        """
        if focus_map is not None:
            for from_attr, to_attr in focus_map.items():
                if not from_attr.__hash__ or not to_attr.__hash__:
                    raise AttrMapError("%r:%r attribute mapping is invalid.  "
                        "Attributes must be hashable" % (from_attr, to_attr))
        self._focus_map = focus_map
        self._invalidate()
    focus_map = property(get_focus_map, set_focus_map)

    def render(self, size, focus=False):
        """
        Render wrapped widget and apply attribute. Return canvas.
        """
        attr_map = self._attr_map
        if focus and self._focus_map is not None:
            attr_map = self._focus_map
        canv = self._original_widget.render(size, focus=focus)
        canv = CompositeCanvas(canv)
        canv.fill_attr_apply(attr_map)
        return canv



class AttrWrap(AttrMap):
    def __init__(self, w, attr, focus_attr=None):
        """
        w -- widget to wrap (stored as self.original_widget)
        attr -- attribute to apply to w
        focus_attr -- attribute to apply when in focus, if None use attr

        This widget is a special case of the new AttrMap widget, and it
        will pass all function calls and variable references to the wrapped
        widget.  This class is maintained for backwards compatibility only,
        new code should use AttrMap instead.

        >>> AttrWrap(Divider(u"!"), 'bright')
        <AttrWrap flow widget <Divider flow widget '!'> attr='bright'>
        >>> AttrWrap(Edit(), 'notfocus', 'focus')
        <AttrWrap selectable flow widget <Edit selectable flow widget '' edit_pos=0> attr='notfocus' focus_attr='focus'>
        >>> size = (5,)
        >>> aw = AttrWrap(Text(u"hi"), 'greeting', 'fgreet')
        >>> next(aw.render(size, focus=False).content())
        [('greeting', None, ...'hi   ')]
        >>> next(aw.render(size, focus=True).content())
        [('fgreet', None, ...'hi   ')]
        """
        self.__super.__init__(w, attr, focus_attr)

    def _repr_attrs(self):
        # only include the focus_attr when it takes effect (not None)
        d = dict(self.__super._repr_attrs(), attr=self.attr)
        del d['attr_map']
        if 'focus_map' in d:
            del d['focus_map']
        if self.focus_attr is not None:
            d['focus_attr'] = self.focus_attr
        return d

    # backwards compatibility, widget used to be stored as w
    get_w = WidgetDecoration._get_original_widget
    set_w = WidgetDecoration._set_original_widget
    w = property(get_w, set_w)

    def get_attr(self):
        return self.attr_map[None]
    def set_attr(self, attr):
        """
        Set the attribute to apply to the wrapped widget

        >> w = AttrWrap(Divider("-"), None)
        >> w.set_attr('new_attr')
        >> w
        <AttrWrap flow widget <Divider flow widget '-'> attr='new_attr'>
        """
        self.set_attr_map({None: attr})
    attr = property(get_attr, set_attr)

    def get_focus_attr(self):
        focus_map = self.focus_map
        if focus_map:
            return focus_map[None]
    def set_focus_attr(self, focus_attr):
        """
        Set the attribute to apply to the wapped widget when it is in
        focus

        If None this widget will use the attr instead (no change when in
        focus).

        >> w = AttrWrap(Divider("-"), 'old')
        >> w.set_focus_attr('new_attr')
        >> w
        <AttrWrap flow widget <Divider flow widget '-'> attr='old' focus_attr='new_attr'>
        >> w.set_focus_attr(None)
        >> w
        <AttrWrap flow widget <Divider flow widget '-'> attr='old'>
        """
        self.set_focus_map({None: focus_attr})
    focus_attr = property(get_focus_attr, set_focus_attr)

    def __getattr__(self,name):
        """
        Call getattr on wrapped widget.  This has been the longstanding
        behaviour of AttrWrap, but is discouraged.  New code should be
        using AttrMap and .base_widget or .original_widget instead.
        """
        return getattr(self._original_widget, name)


    def sizing(self):
        return self._original_widget.sizing()


class BoxAdapterError(Exception):
    pass

class BoxAdapter(WidgetDecoration):
    """
    Adapter for using a box widget where a flow widget would usually go
    """
    no_cache = ["rows"]

    def __init__(self, box_widget, height):
        """
        Create a flow widget that contains a box widget

        :param box_widget: box widget to wrap
        :type box_widget: Widget
        :param height: number of rows for box widget
        :type height: int

        >>> BoxAdapter(SolidFill(u"x"), 5) # 5-rows of x's
        <BoxAdapter flow widget <SolidFill box widget 'x'> height=5>
        """
        if hasattr(box_widget, 'sizing') and BOX not in box_widget.sizing():
            raise BoxAdapterError("%r is not a box widget" %
                box_widget)
        WidgetDecoration.__init__(self,box_widget)

        self.height = height

    def _repr_attrs(self):
        return dict(self.__super._repr_attrs(), height=self.height)

    # originally stored as box_widget, keep for compatibility
    box_widget = property(WidgetDecoration._get_original_widget,
        WidgetDecoration._set_original_widget)

    def sizing(self):
        return set([FLOW])

    def rows(self, size, focus=False):
        """
        Return the predetermined height (behave like a flow widget)

        >>> BoxAdapter(SolidFill(u"x"), 5).rows((20,))
        5
        """
        return self.height

    # The next few functions simply tack-on our height and pass through
    # to self._original_widget
    def get_cursor_coords(self, size):
        (maxcol,) = size
        if not hasattr(self._original_widget,'get_cursor_coords'):
            return None
        return self._original_widget.get_cursor_coords((maxcol, self.height))

    def get_pref_col(self, size):
        (maxcol,) = size
        if not hasattr(self._original_widget,'get_pref_col'):
            return None
        return self._original_widget.get_pref_col((maxcol, self.height))

    def keypress(self, size, key):
        (maxcol,) = size
        return self._original_widget.keypress((maxcol, self.height), key)

    def move_cursor_to_coords(self, size, col, row):
        (maxcol,) = size
        if not hasattr(self._original_widget,'move_cursor_to_coords'):
            return True
        return self._original_widget.move_cursor_to_coords((maxcol,
            self.height), col, row )

    def mouse_event(self, size, event, button, col, row, focus):
        (maxcol,) = size
        if not hasattr(self._original_widget,'mouse_event'):
            return False
        return self._original_widget.mouse_event((maxcol, self.height),
            event, button, col, row, focus)

    def render(self, size, focus=False):
        (maxcol,) = size
        canv = self._original_widget.render((maxcol, self.height), focus)
        canv = CompositeCanvas(canv)
        return canv

    def __getattr__(self, name):
        """
        Pass calls to box widget.
        """
        return getattr(self.box_widget, name)



class PaddingError(Exception):
    pass

class Padding(WidgetDecoration):
    def __init__(self, w, align=LEFT, width=RELATIVE_100, min_width=None,
            left=0, right=0):
        """
        :param w: a box, flow or fixed widget to pad on the left and/or right
            this widget is stored as self.original_widget
        :type w: Widget

        :param align: one of: ``'left'``, ``'center'``, ``'right'``
            (``'relative'``, *percentage* 0=left 100=right)

        :param width: one of:

            *given width*
              integer number of columns for self.original_widget

            ``'pack'``
              try to pack self.original_widget to its ideal size

            (``'relative'``, *percentage of total width*)
              make width depend on the container's width

            ``'clip'``
              to enable clipping mode for a fixed widget

        :param min_width: the minimum number of columns for
            self.original_widget or ``None``
        :type min_width: int

        :param left: a fixed number of columns to pad on the left
        :type left: int

        :param right: a fixed number of columns to pad on the right
        :type right: int

        Clipping Mode: (width= ``'clip'``)
        In clipping mode this padding widget will behave as a flow
        widget and self.original_widget will be treated as a fixed
        widget.  self.original_widget will will be clipped to fit
        the available number of columns.  For example if align is
        ``'left'`` then self.original_widget may be clipped on the right.

        >>> size = (7,)
        >>> def pr(w):
        ...     for t in w.render(size).text:
        ...         print("|%s|" % (t.decode('ascii'),))
        >>> pr(Padding(Text(u"Head"), ('relative', 20), 'pack'))
        | Head  |
        >>> pr(Padding(Divider(u"-"), left=2, right=1))
        |  ---- |
        >>> pr(Padding(Divider(u"*"), 'center', 3))
        |  ***  |
        >>> p=Padding(Text(u"1234"), 'left', 2, None, 1, 1)
        >>> p
        <Padding flow widget <Text flow widget '1234'> left=1 right=1 width=2>
        >>> pr(p)   # align against left
        | 12    |
        | 34    |
        >>> p.align = 'right'
        >>> pr(p)   # align against right
        |    12 |
        |    34 |
        >>> pr(Padding(Text(u"hi\\nthere"), 'right', 'pack')) # pack text first
        |  hi   |
        |  there|
        """
        self.__super.__init__(w)

        # convert obsolete parameters 'fixed left' and 'fixed right':
        if type(align) == tuple and align[0] in ('fixed left',
            'fixed right'):
            if align[0]=='fixed left':
                left = align[1]
                align = LEFT
            else:
                right = align[1]
                align = RIGHT
        if type(width) == tuple and width[0] in ('fixed left',
            'fixed right'):
            if width[0]=='fixed left':
                left = width[1]
            else:
                right = width[1]
            width = RELATIVE_100

        # convert old clipping mode width=None to width='clip'
        if width is None:
            width = CLIP

        self.left = left
        self.right = right
        self._align_type, self._align_amount = normalize_align(align,
            PaddingError)
        self._width_type, self._width_amount = normalize_width(width,
            PaddingError)
        self.min_width = min_width

    def sizing(self):
        if self._width_type == CLIP:
            return set([FLOW])
        return self.original_widget.sizing()

    def _repr_attrs(self):
        attrs = dict(self.__super._repr_attrs(),
            align=self.align,
            width=self.width,
            left=self.left,
            right=self.right,
            min_width=self.min_width)
        return remove_defaults(attrs, Padding.__init__)

    def _get_align(self):
        """
        Return the padding alignment setting.
        """
        return simplify_align(self._align_type, self._align_amount)
    def _set_align(self, align):
        """
        Set the padding alignment.
        """
        self._align_type, self._align_amount = normalize_align(align,
            PaddingError)
        self._invalidate()
    align = property(_get_align, _set_align)

    def _get_width(self):
        """
        Return the padding width.
        """
        return simplify_width(self._width_type, self._width_amount)
    def _set_width(self, width):
        """
        Set the padding width.
        """
        self._width_type, self._width_amount = normalize_width(width,
            PaddingError)
        self._invalidate()
    width = property(_get_width, _set_width)

    def render(self, size, focus=False):
        left, right = self.padding_values(size, focus)

        maxcol = size[0]
        maxcol -= left+right

        if self._width_type == CLIP:
            canv = self._original_widget.render((), focus)
        else:
            canv = self._original_widget.render((maxcol,)+size[1:], focus)
        if canv.cols() == 0:
            canv = SolidCanvas(' ', size[0], canv.rows())
            canv = CompositeCanvas(canv)
            canv.set_depends([self._original_widget])
            return canv
        canv = CompositeCanvas(canv)
        canv.set_depends([self._original_widget])
        if left != 0 or right != 0:
            canv.pad_trim_left_right(left, right)

        return canv

    def padding_values(self, size, focus):
        """Return the number of columns to pad on the left and right.

        Override this method to define custom padding behaviour."""
        maxcol = size[0]
        if self._width_type == CLIP:
            width, ignore = self._original_widget.pack((), focus=focus)
            return calculate_left_right_padding(maxcol,
                self._align_type, self._align_amount,
                CLIP, width, None, self.left, self.right)
        if self._width_type == PACK:
            maxwidth = max(maxcol - self.left - self.right,
                self.min_width or 0)
            (width, ignore) = self._original_widget.pack((maxwidth,),
                focus=focus)
            return calculate_left_right_padding(maxcol,
                self._align_type, self._align_amount,
                GIVEN, width, self.min_width,
                self.left, self.right)
        return calculate_left_right_padding(maxcol,
            self._align_type, self._align_amount,
            self._width_type, self._width_amount,
            self.min_width, self.left, self.right)

    def rows(self, size, focus=False):
        """Return the rows needed for self.original_widget."""
        (maxcol,) = size
        left, right = self.padding_values(size, focus)
        if self._width_type == PACK:
            pcols, prows = self._original_widget.pack((maxcol-left-right,),
                focus)
            return prows
        if self._width_type == CLIP:
            fcols, frows = self._original_widget.pack((), focus)
            return frows
        return self._original_widget.rows((maxcol-left-right,), focus=focus)

    def keypress(self, size, key):
        """Pass keypress to self._original_widget."""
        maxcol = size[0]
        left, right = self.padding_values(size, True)
        maxvals = (maxcol-left-right,)+size[1:]
        return self._original_widget.keypress(maxvals, key)

    def get_cursor_coords(self,size):
        """Return the (x,y) coordinates of cursor within self._original_widget."""
        if not hasattr(self._original_widget,'get_cursor_coords'):
            return None
        left, right = self.padding_values(size, True)
        maxcol = size[0]
        maxvals = (maxcol-left-right,)+size[1:]
        if maxvals[0] == 0:
            return None
        coords = self._original_widget.get_cursor_coords(maxvals)
        if coords is None:
            return None
        x, y = coords
        return x+left, y

    def move_cursor_to_coords(self, size, x, y):
        """Set the cursor position with (x,y) coordinates of self._original_widget.

        Returns True if move succeeded, False otherwise.
        """
        if not hasattr(self._original_widget,'move_cursor_to_coords'):
            return True
        left, right = self.padding_values(size, True)
        maxcol = size[0]
        maxvals = (maxcol-left-right,)+size[1:]
        if type(x)==int:
            if x < left:
                x = left
            elif x >= maxcol-right:
                x = maxcol-right-1
            x -= left
        return self._original_widget.move_cursor_to_coords(maxvals, x, y)

    def mouse_event(self, size, event, button, x, y, focus):
        """Send mouse event if position is within self._original_widget."""
        if not hasattr(self._original_widget,'mouse_event'):
            return False
        left, right = self.padding_values(size, focus)
        maxcol = size[0]
        if x < left or x >= maxcol-right:
            return False
        maxvals = (maxcol-left-right,)+size[1:]
        return self._original_widget.mouse_event(maxvals, event, button, x-left, y,
            focus)


    def get_pref_col(self, size):
        """Return the preferred column from self._original_widget, or None."""
        if not hasattr(self._original_widget,'get_pref_col'):
            return None
        left, right = self.padding_values(size, True)
        maxcol = size[0]
        maxvals = (maxcol-left-right,)+size[1:]
        x = self._original_widget.get_pref_col(maxvals)
        if type(x) == int:
            return x+left
        return x


class FillerError(Exception):
    pass

class Filler(WidgetDecoration):
    def __init__(self, body, valign=MIDDLE, height=PACK, min_height=None,
            top=0, bottom=0):
        """
        :param body: a flow widget or box widget to be filled around (stored
            as self.original_widget)
        :type body: Widget

        :param valign: one of:
            ``'top'``, ``'middle'``, ``'bottom'``,
            (``'relative'``, *percentage* 0=top 100=bottom)

        :param height: one of:

            ``'pack'``
              if body is a flow widget

            *given height*
              integer number of rows for self.original_widget

            (``'relative'``, *percentage of total height*)
              make height depend on container's height

        :param min_height: one of:

            ``None``
              if no minimum or if body is a flow widget

            *minimum height*
              integer number of rows for the widget when height not fixed

        :param top: a fixed number of rows to fill at the top
        :type top: int
        :param bottom: a fixed number of rows to fill at the bottom
        :type bottom: int

        If body is a flow widget then height must be ``'flow'`` and
        *min_height* will be ignored.

        Filler widgets will try to satisfy height argument first by
        reducing the valign amount when necessary.  If height still
        cannot be satisfied it will also be reduced.
        """
        self.__super.__init__(body)

        # convert old parameters to the new top/bottom values
        if isinstance(height, tuple):
            if height[0] == 'fixed top':
                if not isinstance(valign, tuple) or valign[0] != 'fixed bottom':
                    raise FillerError("fixed top height may only be used "
                        "with fixed bottom valign")
                top = height[1]
                height = RELATIVE_100
            elif height[0] == 'fixed bottom':
                if not isinstance(valign, tuple) or valign[0] != 'fixed top':
                    raise FillerError("fixed bottom height may only be used "
                        "with fixed top valign")
                bottom = height[1]
                height = RELATIVE_100
        if isinstance(valign, tuple):
            if valign[0] == 'fixed top':
                top = valign[1]
                valign = TOP
            elif valign[0] == 'fixed bottom':
                bottom = valign[1]
                valign = BOTTOM

        # convert old flow mode parameter height=None to height='flow'
        if height is None or height == FLOW:
            height = PACK

        self.top = top
        self.bottom = bottom
        self.valign_type, self.valign_amount = normalize_valign(valign,
            FillerError)
        self.height_type, self.height_amount = normalize_height(height,
            FillerError)

        if self.height_type not in (GIVEN, PACK):
            self.min_height = min_height
        else:
            self.min_height = None

    def sizing(self):
        return set([BOX]) # always a box widget

    def _repr_attrs(self):
        attrs = dict(self.__super._repr_attrs(),
            valign=simplify_valign(self.valign_type, self.valign_amount),
            height=simplify_height(self.height_type, self.height_amount),
            top=self.top,
            bottom=self.bottom,
            min_height=self.min_height)
        return remove_defaults(attrs, Filler.__init__)

    # backwards compatibility, widget used to be stored as body
    get_body = WidgetDecoration._get_original_widget
    set_body = WidgetDecoration._set_original_widget
    body = property(get_body, set_body)

    def selectable(self):
        """Return selectable from body."""
        return self._original_widget.selectable()

    def filler_values(self, size, focus):
        """
        Return the number of rows to pad on the top and bottom.

        Override this method to define custom padding behaviour.
        """
        (maxcol, maxrow) = size

        if self.height_type == PACK:
            height = self._original_widget.rows((maxcol,),focus=focus)
            return calculate_top_bottom_filler(maxrow,
                self.valign_type, self.valign_amount,
                GIVEN, height,
                None, self.top, self.bottom)

        return calculate_top_bottom_filler(maxrow,
            self.valign_type, self.valign_amount,
            self.height_type, self.height_amount,
            self.min_height, self.top, self.bottom)


    def render(self, size, focus=False):
        """Render self.original_widget with space above and/or below."""
        (maxcol, maxrow) = size
        top, bottom = self.filler_values(size, focus)

        if self.height_type == PACK:
            canv = self._original_widget.render((maxcol,), focus)
        else:
            canv = self._original_widget.render((maxcol,maxrow-top-bottom),focus)
        canv = CompositeCanvas(canv)

        if maxrow and canv.rows() > maxrow and canv.cursor is not None:
            cx, cy = canv.cursor
            if cy >= maxrow:
                canv.trim(cy-maxrow+1,maxrow-top-bottom)
        if canv.rows() > maxrow:
            canv.trim(0, maxrow)
            return canv
        canv.pad_trim_top_bottom(top, bottom)
        return canv


    def keypress(self, size, key):
        """Pass keypress to self.original_widget."""
        (maxcol, maxrow) = size
        if self.height_type == PACK:
            return self._original_widget.keypress((maxcol,), key)

        top, bottom = self.filler_values((maxcol,maxrow), True)
        return self._original_widget.keypress((maxcol,maxrow-top-bottom), key)

    def get_cursor_coords(self, size):
        """Return cursor coords from self.original_widget if any."""
        (maxcol, maxrow) = size
        if not hasattr(self._original_widget, 'get_cursor_coords'):
            return None

        top, bottom = self.filler_values(size, True)
        if self.height_type == PACK:
            coords = self._original_widget.get_cursor_coords((maxcol,))
        else:
            coords = self._original_widget.get_cursor_coords(
                (maxcol,maxrow-top-bottom))
        if not coords:
            return None
        x, y = coords
        if y >= maxrow:
            y = maxrow-1
        return x, y+top

    def get_pref_col(self, size):
        """Return pref_col from self.original_widget if any."""
        (maxcol, maxrow) = size
        if not hasattr(self._original_widget, 'get_pref_col'):
            return None

        if self.height_type == PACK:
            x = self._original_widget.get_pref_col((maxcol,))
        else:
            top, bottom = self.filler_values(size, True)
            x = self._original_widget.get_pref_col(
                (maxcol, maxrow-top-bottom))

        return x

    def move_cursor_to_coords(self, size, col, row):
        """Pass to self.original_widget."""
        (maxcol, maxrow) = size
        if not hasattr(self._original_widget, 'move_cursor_to_coords'):
            return True

        top, bottom = self.filler_values(size, True)
        if row < top or row >= maxcol-bottom:
            return False

        if self.height_type == PACK:
            return self._original_widget.move_cursor_to_coords((maxcol,),
                col, row-top)
        return self._original_widget.move_cursor_to_coords(
            (maxcol, maxrow-top-bottom), col, row-top)

    def mouse_event(self, size, event, button, col, row, focus):
        """Pass to self.original_widget."""
        (maxcol, maxrow) = size
        if not hasattr(self._original_widget, 'mouse_event'):
            return False

        top, bottom = self.filler_values(size, True)
        if row < top or row >= maxrow-bottom:
            return False

        if self.height_type == PACK:
            return self._original_widget.mouse_event((maxcol,),
                event, button, col, row-top, focus)
        return self._original_widget.mouse_event((maxcol, maxrow-top-bottom),
            event, button,col, row-top, focus)

class WidgetDisable(WidgetDecoration):
    """
    A decoration widget that disables interaction with the widget it
    wraps.  This widget always passes focus=False to the wrapped widget,
    even if it somehow does become the focus.
    """
    no_cache = ["rows"]
    ignore_focus = True

    def selectable(self):
        return False
    def rows(self, size, focus=False):
        return self._original_widget.rows(size, False)
    def sizing(self):
        return self._original_widget.sizing()
    def pack(self, size, focus=False):
        return self._original_widget.pack(size, False)
    def render(self, size, focus=False):
        canv = self._original_widget.render(size, False)
        return CompositeCanvas(canv)

def normalize_align(align, err):
    """
    Split align into (align_type, align_amount).  Raise exception err
    if align doesn't match a valid alignment.
    """
    if align in (LEFT, CENTER, RIGHT):
        return (align, None)
    elif type(align) == tuple and len(align) == 2 and align[0] == RELATIVE:
        return align
    raise err("align value %r is not one of 'left', 'center', "
        "'right', ('relative', percentage 0=left 100=right)"
        % (align,))

def simplify_align(align_type, align_amount):
    """
    Recombine (align_type, align_amount) into an align value.
    Inverse of normalize_align.
    """
    if align_type == RELATIVE:
        return (align_type, align_amount)
    return align_type

def normalize_width(width, err):
    """
    Split width into (width_type, width_amount).  Raise exception err
    if width doesn't match a valid alignment.
    """
    if width in (CLIP, PACK):
        return (width, None)
    elif type(width) == int:
        return (GIVEN, width)
    elif type(width) == tuple and len(width) == 2 and width[0] == RELATIVE:
        return width
    raise err("width value %r is not one of fixed number of columns, "
        "'pack', ('relative', percentage of total width), 'clip'"
        % (width,))

def simplify_width(width_type, width_amount):
    """
    Recombine (width_type, width_amount) into an width value.
    Inverse of normalize_width.
    """
    if width_type in (CLIP, PACK):
        return width_type
    elif width_type == GIVEN:
        return width_amount
    return (width_type, width_amount)

def normalize_valign(valign, err):
    """
    Split align into (valign_type, valign_amount).  Raise exception err
    if align doesn't match a valid alignment.
    """
    if valign in (TOP, MIDDLE, BOTTOM):
        return (valign, None)
    elif (isinstance(valign, tuple) and len(valign) == 2 and
            valign[0] == RELATIVE):
        return valign
    raise err("valign value %r is not one of 'top', 'middle', "
        "'bottom', ('relative', percentage 0=left 100=right)"
        % (valign,))

def simplify_valign(valign_type, valign_amount):
    """
    Recombine (valign_type, valign_amount) into an valign value.
    Inverse of normalize_valign.
    """
    if valign_type == RELATIVE:
        return (valign_type, valign_amount)
    return valign_type

def normalize_height(height, err):
    """
    Split height into (height_type, height_amount).  Raise exception err
    if height isn't valid.
    """
    if height in (FLOW, PACK):
        return (height, None)
    elif (isinstance(height, tuple) and len(height) == 2 and
            height[0] == RELATIVE):
        return height
    elif isinstance(height, int):
        return (GIVEN, height)
    raise err("height value %r is not one of fixed number of columns, "
        "'pack', ('relative', percentage of total height)"
        % (height,))

def simplify_height(height_type, height_amount):
    """
    Recombine (height_type, height_amount) into an height value.
    Inverse of normalize_height.
    """
    if height_type in (FLOW, PACK):
        return height_type
    elif height_type == GIVEN:
        return height_amount
    return (height_type, height_amount)


def calculate_top_bottom_filler(maxrow, valign_type, valign_amount, height_type,
        height_amount, min_height, top, bottom):
    """
    Return the amount of filler (or clipping) on the top and
    bottom part of maxrow rows to satisfy the following:

    valign_type -- 'top', 'middle', 'bottom', 'relative'
    valign_amount -- a percentage when align_type=='relative'
    height_type -- 'given', 'relative', 'clip'
    height_amount -- a percentage when width_type=='relative'
        otherwise equal to the height of the widget
    min_height -- a desired minimum width for the widget or None
    top -- a fixed number of rows to fill on the top
    bottom -- a fixed number of rows to fill on the bottom

    >>> ctbf = calculate_top_bottom_filler
    >>> ctbf(15, 'top', 0, 'given', 10, None, 2, 0)
    (2, 3)
    >>> ctbf(15, 'relative', 0, 'given', 10, None, 2, 0)
    (2, 3)
    >>> ctbf(15, 'relative', 100, 'given', 10, None, 2, 0)
    (5, 0)
    >>> ctbf(15, 'middle', 0, 'given', 4, None, 2, 0)
    (6, 5)
    >>> ctbf(15, 'middle', 0, 'given', 18, None, 2, 0)
    (0, 0)
    >>> ctbf(20, 'top', 0, 'relative', 60, None, 0, 0)
    (0, 8)
    >>> ctbf(20, 'relative', 30, 'relative', 60, None, 0, 0)
    (2, 6)
    >>> ctbf(20, 'relative', 30, 'relative', 60, 14, 0, 0)
    (2, 4)
    """
    if height_type == RELATIVE:
        maxheight = max(maxrow - top - bottom, 0)
        height = int_scale(height_amount, 101, maxheight + 1)
        if min_height is not None:
            height = max(height, min_height)
    else:
        height = height_amount

    standard_alignments = {TOP:0, MIDDLE:50, BOTTOM:100}
    valign = standard_alignments.get(valign_type, valign_amount)

    # add the remainder of top/bottom to the filler
    filler = maxrow - height - top - bottom
    bottom += int_scale(100 - valign, 101, filler + 1)
    top = maxrow - height - bottom

    # reduce filler if we are clipping an edge
    if bottom < 0 < top:
        shift = min(top, -bottom)
        top -= shift
        bottom += shift
    elif top < 0 < bottom:
        shift = min(bottom, -top)
        bottom -= shift
        top += shift

    # no negative values for filler at the moment
    top = max(top, 0)
    bottom = max(bottom, 0)

    return top, bottom


def calculate_left_right_padding(maxcol, align_type, align_amount,
    width_type, width_amount, min_width, left, right):
    """
    Return the amount of padding (or clipping) on the left and
    right part of maxcol columns to satisfy the following:

    align_type -- 'left', 'center', 'right', 'relative'
    align_amount -- a percentage when align_type=='relative'
    width_type -- 'fixed', 'relative', 'clip'
    width_amount -- a percentage when width_type=='relative'
        otherwise equal to the width of the widget
    min_width -- a desired minimum width for the widget or None
    left -- a fixed number of columns to pad on the left
    right -- a fixed number of columns to pad on the right

    >>> clrp = calculate_left_right_padding
    >>> clrp(15, 'left', 0, 'given', 10, None, 2, 0)
    (2, 3)
    >>> clrp(15, 'relative', 0, 'given', 10, None, 2, 0)
    (2, 3)
    >>> clrp(15, 'relative', 100, 'given', 10, None, 2, 0)
    (5, 0)
    >>> clrp(15, 'center', 0, 'given', 4, None, 2, 0)
    (6, 5)
    >>> clrp(15, 'left', 0, 'clip', 18, None, 0, 0)
    (0, -3)
    >>> clrp(15, 'right', 0, 'clip', 18, None, 0, -1)
    (-2, -1)
    >>> clrp(15, 'center', 0, 'given', 18, None, 2, 0)
    (0, 0)
    >>> clrp(20, 'left', 0, 'relative', 60, None, 0, 0)
    (0, 8)
    >>> clrp(20, 'relative', 30, 'relative', 60, None, 0, 0)
    (2, 6)
    >>> clrp(20, 'relative', 30, 'relative', 60, 14, 0, 0)
    (2, 4)
    """
    if width_type == RELATIVE:
        maxwidth = max(maxcol - left - right, 0)
        width = int_scale(width_amount, 101, maxwidth + 1)
        if min_width is not None:
            width = max(width, min_width)
    else:
        width = width_amount

    standard_alignments = {LEFT:0, CENTER:50, RIGHT:100}
    align = standard_alignments.get(align_type, align_amount)

    # add the remainder of left/right the padding
    padding = maxcol - width - left - right
    right += int_scale(100 - align, 101, padding + 1)
    left = maxcol - width - right

    # reduce padding if we are clipping an edge
    if right < 0 and left > 0:
        shift = min(left, -right)
        left -= shift
        right += shift
    elif left < 0 and right > 0:
        shift = min(right, -left)
        right -= shift
        left += shift

    # only clip if width_type == 'clip'
    if width_type != CLIP and (left < 0 or right < 0):
        left = max(left, 0)
        right = max(right, 0)

    return left, right



def _test():
    import doctest
    doctest.testmod()

if __name__=='__main__':
    _test()
