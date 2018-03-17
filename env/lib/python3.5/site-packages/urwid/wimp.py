#!/usr/bin/python
#
# Urwid Window-Icon-Menu-Pointer-style widget classes
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

from urwid.widget import (Text, WidgetWrap, delegate_to_widget_mixin, BOX,
    FLOW)
from urwid.canvas import CompositeCanvas
from urwid.signals import connect_signal
from urwid.container import Columns, Overlay
from urwid.util import is_mouse_press
from urwid.text_layout import calc_coords
from urwid.signals import disconnect_signal # doctests
from urwid.split_repr import python3_repr
from urwid.decoration import WidgetDecoration
from urwid.command_map import ACTIVATE

class SelectableIcon(Text):
    _selectable = True
    def __init__(self, text, cursor_position=1):
        """
        :param text: markup for this widget; see :class:`Text` for
                     description of text markup
        :param cursor_position: position the cursor will appear in the
                                text when this widget is in focus

        This is a text widget that is selectable.  A cursor
        displayed at a fixed location in the text when in focus.
        This widget has no special handling of keyboard or mouse input.
        """
        self.__super.__init__(text)
        self._cursor_position = cursor_position

    def render(self, size, focus=False):
        """
        Render the text content of this widget with a cursor when
        in focus.

        >>> si = SelectableIcon(u"[!]")
        >>> si
        <SelectableIcon selectable flow widget '[!]'>
        >>> si.render((4,), focus=True).cursor
        (1, 0)
        >>> si = SelectableIcon("((*))", 2)
        >>> si.render((8,), focus=True).cursor
        (2, 0)
        >>> si.render((2,), focus=True).cursor
        (0, 1)
        """
        c = self.__super.render(size, focus)
        if focus:
            # create a new canvas so we can add a cursor
            c = CompositeCanvas(c)
            c.cursor = self.get_cursor_coords(size)
        return c

    def get_cursor_coords(self, size):
        """
        Return the position of the cursor if visible.  This method
        is required for widgets that display a cursor.
        """
        if self._cursor_position > len(self.text):
            return None
        # find out where the cursor will be displayed based on
        # the text layout
        (maxcol,) = size
        trans = self.get_line_translation(maxcol)
        x, y = calc_coords(self.text, trans, self._cursor_position)
        if maxcol <= x:
            return None
        return x, y

    def keypress(self, size, key):
        """
        No keys are handled by this widget.  This method is
        required for selectable widgets.
        """
        return key

class CheckBoxError(Exception):
    pass

class CheckBox(WidgetWrap):
    def sizing(self):
        return frozenset([FLOW])

    states = {
        True: SelectableIcon("[X]"),
        False: SelectableIcon("[ ]"),
        'mixed': SelectableIcon("[#]") }
    reserve_columns = 4

    # allow users of this class to listen for change events
    # sent when the state of this widget is modified
    # (this variable is picked up by the MetaSignals metaclass)
    signals = ["change", 'postchange']

    def __init__(self, label, state=False, has_mixed=False,
             on_state_change=None, user_data=None):
        """
        :param label: markup for check box label
        :param state: False, True or "mixed"
        :param has_mixed: True if "mixed" is a state to cycle through
        :param on_state_change: shorthand for connect_signal()
                                function call for a single callback
        :param user_data: user_data for on_state_change

        Signals supported: ``'change'``, ``"postchange"``

        Register signal handler with::

          urwid.connect_signal(check_box, 'change', callback, user_data)

        where callback is callback(check_box, new_state [,user_data])
        Unregister signal handlers with::

          urwid.disconnect_signal(check_box, 'change', callback, user_data)

        >>> CheckBox(u"Confirm")
        <CheckBox selectable flow widget 'Confirm' state=False>
        >>> CheckBox(u"Yogourt", "mixed", True)
        <CheckBox selectable flow widget 'Yogourt' state='mixed'>
        >>> cb = CheckBox(u"Extra onions", True)
        >>> cb
        <CheckBox selectable flow widget 'Extra onions' state=True>
        >>> cb.render((20,), focus=True).text # ... = b in Python 3
        [...'[X] Extra onions    ']
        """
        self.__super.__init__(None) # self.w set by set_state below
        self._label = Text("")
        self.has_mixed = has_mixed
        self._state = None
        # The old way of listening for a change was to pass the callback
        # in to the constructor.  Just convert it to the new way:
        if on_state_change:
            connect_signal(self, 'change', on_state_change, user_data)
        self.set_label(label)
        self.set_state(state)

    def _repr_words(self):
        return self.__super._repr_words() + [
            python3_repr(self.label)]

    def _repr_attrs(self):
        return dict(self.__super._repr_attrs(),
            state=self.state)

    def set_label(self, label):
        """
        Change the check box label.

        label -- markup for label.  See Text widget for description
        of text markup.

        >>> cb = CheckBox(u"foo")
        >>> cb
        <CheckBox selectable flow widget 'foo' state=False>
        >>> cb.set_label(('bright_attr', u"bar"))
        >>> cb
        <CheckBox selectable flow widget 'bar' state=False>
        """
        self._label.set_text(label)
        # no need to call self._invalidate(). WidgetWrap takes care of
        # that when self.w changes

    def get_label(self):
        """
        Return label text.

        >>> cb = CheckBox(u"Seriously")
        >>> print(cb.get_label())
        Seriously
        >>> print(cb.label)
        Seriously
        >>> cb.set_label([('bright_attr', u"flashy"), u" normal"])
        >>> print(cb.label)  #  only text is returned
        flashy normal
        """
        return self._label.text
    label = property(get_label)

    def set_state(self, state, do_callback=True):
        """
        Set the CheckBox state.

        state -- True, False or "mixed"
        do_callback -- False to suppress signal from this change

        >>> changes = []
        >>> def callback_a(cb, state, user_data):
        ...     changes.append("A %r %r" % (state, user_data))
        >>> def callback_b(cb, state):
        ...     changes.append("B %r" % state)
        >>> cb = CheckBox('test', False, False)
        >>> key1 = connect_signal(cb, 'change', callback_a, "user_a")
        >>> key2 = connect_signal(cb, 'change', callback_b)
        >>> cb.set_state(True) # both callbacks will be triggered
        >>> cb.state
        True
        >>> disconnect_signal(cb, 'change', callback_a, "user_a")
        >>> cb.state = False
        >>> cb.state
        False
        >>> cb.set_state(True)
        >>> cb.state
        True
        >>> cb.set_state(False, False) # don't send signal
        >>> changes
        ["A True 'user_a'", 'B True', 'B False', 'B True']
        """
        if self._state == state:
            return

        if state not in self.states:
            raise CheckBoxError("%s Invalid state: %s" % (
                repr(self), repr(state)))

        # self._state is None is a special case when the CheckBox
        # has just been created
        old_state = self._state
        if do_callback and old_state is not None:
            self._emit('change', state)
        self._state = state
        # rebuild the display widget with the new state
        self._w = Columns( [
            ('fixed', self.reserve_columns, self.states[state] ),
            self._label ] )
        self._w.focus_col = 0
        if do_callback and old_state is not None:
            self._emit('postchange', old_state)

    def get_state(self):
        """Return the state of the checkbox."""
        return self._state
    state = property(get_state, set_state)

    def keypress(self, size, key):
        """
        Toggle state on 'activate' command.

        >>> assert CheckBox._command_map[' '] == 'activate'
        >>> assert CheckBox._command_map['enter'] == 'activate'
        >>> size = (10,)
        >>> cb = CheckBox('press me')
        >>> cb.state
        False
        >>> cb.keypress(size, ' ')
        >>> cb.state
        True
        >>> cb.keypress(size, ' ')
        >>> cb.state
        False
        """
        if self._command_map[key] != ACTIVATE:
            return key

        self.toggle_state()

    def toggle_state(self):
        """
        Cycle to the next valid state.

        >>> cb = CheckBox("3-state", has_mixed=True)
        >>> cb.state
        False
        >>> cb.toggle_state()
        >>> cb.state
        True
        >>> cb.toggle_state()
        >>> cb.state
        'mixed'
        >>> cb.toggle_state()
        >>> cb.state
        False
        """
        if self.state == False:
            self.set_state(True)
        elif self.state == True:
            if self.has_mixed:
                self.set_state('mixed')
            else:
                self.set_state(False)
        elif self.state == 'mixed':
            self.set_state(False)

    def mouse_event(self, size, event, button, x, y, focus):
        """
        Toggle state on button 1 press.

        >>> size = (20,)
        >>> cb = CheckBox("clickme")
        >>> cb.state
        False
        >>> cb.mouse_event(size, 'mouse press', 1, 2, 0, True)
        True
        >>> cb.state
        True
        """
        if button != 1 or not is_mouse_press(event):
            return False
        self.toggle_state()
        return True


class RadioButton(CheckBox):
    states = {
        True: SelectableIcon("(X)"),
        False: SelectableIcon("( )"),
        'mixed': SelectableIcon("(#)") }
    reserve_columns = 4

    def __init__(self, group, label, state="first True",
             on_state_change=None, user_data=None):
        """
        :param group: list for radio buttons in same group
        :param label: markup for radio button label
        :param state: False, True, "mixed" or "first True"
        :param on_state_change: shorthand for connect_signal()
                                function call for a single 'change' callback
        :param user_data: user_data for on_state_change

        This function will append the new radio button to group.
        "first True" will set to True if group is empty.

        Signals supported: ``'change'``, ``"postchange"``

        Register signal handler with::

          urwid.connect_signal(radio_button, 'change', callback, user_data)

        where callback is callback(radio_button, new_state [,user_data])
        Unregister signal handlers with::

          urwid.disconnect_signal(radio_button, 'change', callback, user_data)

        >>> bgroup = [] # button group
        >>> b1 = RadioButton(bgroup, u"Agree")
        >>> b2 = RadioButton(bgroup, u"Disagree")
        >>> len(bgroup)
        2
        >>> b1
        <RadioButton selectable flow widget 'Agree' state=True>
        >>> b2
        <RadioButton selectable flow widget 'Disagree' state=False>
        >>> b2.render((15,), focus=True).text # ... = b in Python 3
        [...'( ) Disagree   ']
        """
        if state=="first True":
            state = not group

        self.group = group
        self.__super.__init__(label, state, False, on_state_change,
            user_data)
        group.append(self)



    def set_state(self, state, do_callback=True):
        """
        Set the RadioButton state.

        state -- True, False or "mixed"

        do_callback -- False to suppress signal from this change

        If state is True all other radio buttons in the same button
        group will be set to False.

        >>> bgroup = [] # button group
        >>> b1 = RadioButton(bgroup, u"Agree")
        >>> b2 = RadioButton(bgroup, u"Disagree")
        >>> b3 = RadioButton(bgroup, u"Unsure")
        >>> b1.state, b2.state, b3.state
        (True, False, False)
        >>> b2.set_state(True)
        >>> b1.state, b2.state, b3.state
        (False, True, False)
        >>> def relabel_button(radio_button, new_state):
        ...     radio_button.set_label(u"Think Harder!")
        >>> key = connect_signal(b3, 'change', relabel_button)
        >>> b3
        <RadioButton selectable flow widget 'Unsure' state=False>
        >>> b3.set_state(True) # this will trigger the callback
        >>> b3
        <RadioButton selectable flow widget 'Think Harder!' state=True>
        """
        if self._state == state:
            return

        self.__super.set_state(state, do_callback)

        # if we're clearing the state we don't have to worry about
        # other buttons in the button group
        if state is not True:
            return

        # clear the state of each other radio button
        for cb in self.group:
            if cb is self: continue
            if cb._state:
                cb.set_state(False)


    def toggle_state(self):
        """
        Set state to True.

        >>> bgroup = [] # button group
        >>> b1 = RadioButton(bgroup, "Agree")
        >>> b2 = RadioButton(bgroup, "Disagree")
        >>> b1.state, b2.state
        (True, False)
        >>> b2.toggle_state()
        >>> b1.state, b2.state
        (False, True)
        >>> b2.toggle_state()
        >>> b1.state, b2.state
        (False, True)
        """
        self.set_state(True)


class Button(WidgetWrap):
    def sizing(self):
        return frozenset([FLOW])

    button_left = Text("<")
    button_right = Text(">")

    signals = ["click"]

    def __init__(self, label, on_press=None, user_data=None):
        """
        :param label: markup for button label
        :param on_press: shorthand for connect_signal()
                         function call for a single callback
        :param user_data: user_data for on_press

        Signals supported: ``'click'``

        Register signal handler with::

          urwid.connect_signal(button, 'click', callback, user_data)

        where callback is callback(button [,user_data])
        Unregister signal handlers with::

          urwid.disconnect_signal(button, 'click', callback, user_data)

        >>> Button(u"Ok")
        <Button selectable flow widget 'Ok'>
        >>> b = Button("Cancel")
        >>> b.render((15,), focus=True).text # ... = b in Python 3
        [...'< Cancel      >']
        """
        self._label = SelectableIcon("", 0)
        cols = Columns([
            ('fixed', 1, self.button_left),
            self._label,
            ('fixed', 1, self.button_right)],
            dividechars=1)
        self.__super.__init__(cols)

        # The old way of listening for a change was to pass the callback
        # in to the constructor.  Just convert it to the new way:
        if on_press:
            connect_signal(self, 'click', on_press, user_data)

        self.set_label(label)

    def _repr_words(self):
        # include button.label in repr(button)
        return self.__super._repr_words() + [
            python3_repr(self.label)]

    def set_label(self, label):
        """
        Change the button label.

        label -- markup for button label

        >>> b = Button("Ok")
        >>> b.set_label(u"Yup yup")
        >>> b
        <Button selectable flow widget 'Yup yup'>
        """
        self._label.set_text(label)

    def get_label(self):
        """
        Return label text.

        >>> b = Button(u"Ok")
        >>> print(b.get_label())
        Ok
        >>> print(b.label)
        Ok
        """
        return self._label.text
    label = property(get_label)

    def keypress(self, size, key):
        """
        Send 'click' signal on 'activate' command.

        >>> assert Button._command_map[' '] == 'activate'
        >>> assert Button._command_map['enter'] == 'activate'
        >>> size = (15,)
        >>> b = Button(u"Cancel")
        >>> clicked_buttons = []
        >>> def handle_click(button):
        ...     clicked_buttons.append(button.label)
        >>> key = connect_signal(b, 'click', handle_click)
        >>> b.keypress(size, 'enter')
        >>> b.keypress(size, ' ')
        >>> clicked_buttons # ... = u in Python 2
        [...'Cancel', ...'Cancel']
        """
        if self._command_map[key] != ACTIVATE:
            return key

        self._emit('click')

    def mouse_event(self, size, event, button, x, y, focus):
        """
        Send 'click' signal on button 1 press.

        >>> size = (15,)
        >>> b = Button(u"Ok")
        >>> clicked_buttons = []
        >>> def handle_click(button):
        ...     clicked_buttons.append(button.label)
        >>> key = connect_signal(b, 'click', handle_click)
        >>> b.mouse_event(size, 'mouse press', 1, 4, 0, True)
        True
        >>> b.mouse_event(size, 'mouse press', 2, 4, 0, True) # ignored
        False
        >>> clicked_buttons # ... = u in Python 2
        [...'Ok']
        """
        if button != 1 or not is_mouse_press(event):
            return False

        self._emit('click')
        return True


class PopUpLauncher(delegate_to_widget_mixin('_original_widget'),
        WidgetDecoration):
    def __init__(self, original_widget):
        self.__super.__init__(original_widget)
        self._pop_up_widget = None

    def create_pop_up(self):
        """
        Subclass must override this method and return a widget
        to be used for the pop-up.  This method is called once each time
        the pop-up is opened.
        """
        raise NotImplementedError("Subclass must override this method")

    def get_pop_up_parameters(self):
        """
        Subclass must override this method and have it return a dict, eg:

        {'left':0, 'top':1, 'overlay_width':30, 'overlay_height':4}

        This method is called each time this widget is rendered.
        """
        raise NotImplementedError("Subclass must override this method")

    def open_pop_up(self):
        self._pop_up_widget = self.create_pop_up()
        self._invalidate()

    def close_pop_up(self):
        self._pop_up_widget = None
        self._invalidate()

    def render(self, size, focus=False):
        canv = self.__super.render(size, focus)
        if self._pop_up_widget:
            canv = CompositeCanvas(canv)
            canv.set_pop_up(self._pop_up_widget, **self.get_pop_up_parameters())
        return canv


class PopUpTarget(WidgetDecoration):
    # FIXME: this whole class is a terrible hack and must be fixed
    # when layout and rendering are separated
    _sizing = set([BOX])
    _selectable = True

    def __init__(self, original_widget):
        self.__super.__init__(original_widget)
        self._pop_up = None
        self._current_widget = self._original_widget

    def _update_overlay(self, size, focus):
        canv = self._original_widget.render(size, focus=focus)
        self._cache_original_canvas = canv # imperfect performance hack
        pop_up = canv.get_pop_up()
        if pop_up:
            left, top, (
                w, overlay_width, overlay_height) = pop_up
            if self._pop_up != w:
                self._pop_up = w
                self._current_widget = Overlay(w, self._original_widget,
                    ('fixed left', left), overlay_width,
                    ('fixed top', top), overlay_height)
            else:
                self._current_widget.set_overlay_parameters(
                    ('fixed left', left), overlay_width,
                    ('fixed top', top), overlay_height)
        else:
            self._pop_up = None
            self._current_widget = self._original_widget

    def render(self, size, focus=False):
        self._update_overlay(size, focus)
        return self._current_widget.render(size, focus=focus)
    def get_cursor_coords(self, size):
        self._update_overlay(size, True)
        return self._current_widget.get_cursor_coords(size)
    def get_pref_col(self, size):
        self._update_overlay(size, True)
        return self._current_widget.get_pref_col(size)
    def keypress(self, size, key):
        self._update_overlay(size, True)
        return self._current_widget.keypress(size, key)
    def move_cursor_to_coords(self, size, x, y):
        self._update_overlay(size, True)
        return self._current_widget.move_cursor_to_coords(size, x, y)
    def mouse_event(self, size, event, button, x, y, focus):
        self._update_overlay(size, focus)
        return self._current_widget.mouse_event(size, event, button, x, y, focus)
    def pack(self, size=None, focus=False):
        self._update_overlay(size, focus)
        return self._current_widget.pack(size)






def _test():
    import doctest
    doctest.testmod()

if __name__=='__main__':
    _test()
