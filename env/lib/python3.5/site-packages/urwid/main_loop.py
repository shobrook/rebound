#!/usr/bin/python
#
# Urwid main loop code
#    Copyright (C) 2004-2012  Ian Ward
#    Copyright (C) 2008 Walter Mundt
#    Copyright (C) 2009 Andrew Psaltis
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

import time
import heapq
import select
import os
import signal
from functools import wraps
from itertools import count
from weakref import WeakKeyDictionary

try:
    import fcntl
except ImportError:
    pass # windows

from urwid.util import StoppingContext, is_mouse_event
from urwid.compat import PYTHON3, reraise
from urwid.command_map import command_map, REDRAW_SCREEN
from urwid.wimp import PopUpTarget
from urwid import signals
from urwid.display_common import INPUT_DESCRIPTORS_CHANGED

PIPE_BUFFER_READ_SIZE = 4096 # can expect this much on Linux, so try for that

class ExitMainLoop(Exception):
    """
    When this exception is raised within a main loop the main loop
    will exit cleanly.
    """
    pass

class CantUseExternalLoop(Exception):
    pass

class MainLoop(object):
    """
    This is the standard main loop implementation for a single interactive
    session.

    :param widget: the topmost widget used for painting the screen, stored as
                   :attr:`widget` and may be modified. Must be a box widget.
    :type widget: widget instance

    :param palette: initial palette for screen
    :type palette: iterable of palette entries

    :param screen: screen to use, default is a new :class:`raw_display.Screen`
                   instance; stored as :attr:`screen`
    :type screen: display module screen instance

    :param handle_mouse: ``True`` to ask :attr:`.screen` to process mouse events
    :type handle_mouse: bool

    :param input_filter: a function to filter input before sending it to
                   :attr:`.widget`, called from :meth:`.input_filter`
    :type input_filter: callable

    :param unhandled_input: a function called when input is not handled by
                            :attr:`.widget`, called from :meth:`.unhandled_input`
    :type unhandled_input: callable

    :param event_loop: if :attr:`.screen` supports external an event loop it may be
                       given here, default is a new :class:`SelectEventLoop` instance;
                       stored as :attr:`.event_loop`
    :type event_loop: event loop instance

    :param pop_ups: `True` to wrap :attr:`.widget` with a :class:`PopUpTarget`
                    instance to allow any widget to open a pop-up anywhere on the screen
    :type pop_ups: boolean


    .. attribute:: screen

        The screen object this main loop uses for screen updates and reading input

    .. attribute:: event_loop

        The event loop object this main loop uses for waiting on alarms and IO
    """

    def __init__(self, widget, palette=(), screen=None,
            handle_mouse=True, input_filter=None, unhandled_input=None,
            event_loop=None, pop_ups=False):
        self._widget = widget
        self.handle_mouse = handle_mouse
        self.pop_ups = pop_ups # triggers property setting side-effect

        if not screen:
            from urwid import raw_display
            screen = raw_display.Screen()

        if palette:
            screen.register_palette(palette)

        self.screen = screen
        self.screen_size = None

        self._unhandled_input = unhandled_input
        self._input_filter = input_filter

        if not hasattr(screen, 'hook_event_loop'
                ) and event_loop is not None:
            raise NotImplementedError("screen object passed "
                "%r does not support external event loops" % (screen,))
        if event_loop is None:
            event_loop = SelectEventLoop()
        self.event_loop = event_loop

        if hasattr(self.screen, 'signal_handler_setter'):
            # Tell the screen what function it must use to set
            # signal handlers
            self.screen.signal_handler_setter = self.event_loop.set_signal_handler

        self._watch_pipes = {}

    def _set_widget(self, widget):
        self._widget = widget
        if self.pop_ups:
            self._topmost_widget.original_widget = self._widget
        else:
            self._topmost_widget = self._widget
    widget = property(lambda self:self._widget, _set_widget, doc=
       """
       Property for the topmost widget used to draw the screen.
       This must be a box widget.
       """)

    def _set_pop_ups(self, pop_ups):
        self._pop_ups = pop_ups
        if pop_ups:
            self._topmost_widget = PopUpTarget(self._widget)
        else:
            self._topmost_widget = self._widget
    pop_ups = property(lambda self:self._pop_ups, _set_pop_ups)

    def set_alarm_in(self, sec, callback, user_data=None):
        """
        Schedule an alarm in *sec* seconds that will call *callback* from the
        within the :meth:`run` method.

        :param sec: seconds until alarm
        :type sec: float
        :param callback: function to call with two parameters: this main loop
                         object and *user_data*
        :type callback: callable
        """
        def cb():
            callback(self, user_data)
        return self.event_loop.alarm(sec, cb)

    def set_alarm_at(self, tm, callback, user_data=None):
        """
        Schedule an alarm at *tm* time that will call *callback* from the
        within the :meth:`run` function. Returns a handle that may be passed to
        :meth:`remove_alarm`.

        :param tm: time to call callback e.g. ``time.time() + 5``
        :type tm: float
        :param callback: function to call with two parameters: this main loop
                         object and *user_data*
        :type callback: callable
        """
        def cb():
            callback(self, user_data)
        return self.event_loop.alarm(tm - time.time(), cb)

    def remove_alarm(self, handle):
        """
        Remove an alarm. Return ``True`` if *handle* was found, ``False``
        otherwise.
        """
        return self.event_loop.remove_alarm(handle)

    def watch_pipe(self, callback):
        """
        Create a pipe for use by a subprocess or thread to trigger a callback
        in the process/thread running the main loop.

        :param callback: function taking one parameter to call from within
                         the process/thread running the main loop
        :type callback: callable

        This method returns a file descriptor attached to the write end of a
        pipe. The read end of the pipe is added to the list of files
        :attr:`event_loop` is watching. When data is written to the pipe the
        callback function will be called and passed a single value containing
        data read from the pipe.

        This method may be used any time you want to update widgets from
        another thread or subprocess.

        Data may be written to the returned file descriptor with
        ``os.write(fd, data)``. Ensure that data is less than 512 bytes (or 4K
        on Linux) so that the callback will be triggered just once with the
        complete value of data passed in.

        If the callback returns ``False`` then the watch will be removed from
        :attr:`event_loop` and the read end of the pipe will be closed. You
        are responsible for closing the write end of the pipe with
        ``os.close(fd)``.
        """
        pipe_rd, pipe_wr = os.pipe()
        fcntl.fcntl(pipe_rd, fcntl.F_SETFL, os.O_NONBLOCK)
        watch_handle = None

        def cb():
            data = os.read(pipe_rd, PIPE_BUFFER_READ_SIZE)
            rval = callback(data)
            if rval is False:
                self.event_loop.remove_watch_file(watch_handle)
                os.close(pipe_rd)

        watch_handle = self.event_loop.watch_file(pipe_rd, cb)
        self._watch_pipes[pipe_wr] = (watch_handle, pipe_rd)
        return pipe_wr

    def remove_watch_pipe(self, write_fd):
        """
        Close the read end of the pipe and remove the watch created by
        :meth:`watch_pipe`. You are responsible for closing the write end of
        the pipe.

        Returns ``True`` if the watch pipe exists, ``False`` otherwise
        """
        try:
            watch_handle, pipe_rd = self._watch_pipes.pop(write_fd)
        except KeyError:
            return False

        if not self.event_loop.remove_watch_file(watch_handle):
            return False
        os.close(pipe_rd)
        return True

    def watch_file(self, fd, callback):
        """
        Call *callback* when *fd* has some data to read. No parameters are
        passed to callback.

        Returns a handle that may be passed to :meth:`remove_watch_file`.
        """
        return self.event_loop.watch_file(fd, callback)

    def remove_watch_file(self, handle):
        """
        Remove a watch file. Returns ``True`` if the watch file
        exists, ``False`` otherwise.
        """
        return self.event_loop.remove_watch_file(handle)


    def run(self):
        """
        Start the main loop handling input events and updating the screen. The
        loop will continue until an :exc:`ExitMainLoop` exception is raised.

        If you would prefer to manage the event loop yourself, don't use this
        method.  Instead, call :meth:`start` before starting the event loop,
        and :meth:`stop` once it's finished.
        """
        try:
            self._run()
        except ExitMainLoop:
            pass

    def _test_run(self):
        """
        >>> w = _refl("widget")   # _refl prints out function calls
        >>> w.render_rval = "fake canvas"  # *_rval is used for return values
        >>> scr = _refl("screen")
        >>> scr.get_input_descriptors_rval = [42]
        >>> scr.get_cols_rows_rval = (20, 10)
        >>> scr.started = True
        >>> scr._urwid_signals = {}
        >>> evl = _refl("event_loop")
        >>> evl.enter_idle_rval = 1
        >>> evl.watch_file_rval = 2
        >>> ml = MainLoop(w, [], scr, event_loop=evl)
        >>> ml.run()    # doctest:+ELLIPSIS
        screen.start()
        screen.set_mouse_tracking()
        screen.unhook_event_loop(...)
        screen.hook_event_loop(...)
        event_loop.enter_idle(<bound method MainLoop.entering_idle...>)
        event_loop.run()
        event_loop.remove_enter_idle(1)
        screen.unhook_event_loop(...)
        screen.stop()
        >>> ml.draw_screen()    # doctest:+ELLIPSIS
        screen.get_cols_rows()
        widget.render((20, 10), focus=True)
        screen.draw_screen((20, 10), 'fake canvas')
        """

    def start(self):
        """
        Sets up the main loop, hooking into the event loop where necessary.
        Starts the :attr:`screen` if it hasn't already been started.

        If you want to control starting and stopping the event loop yourself,
        you should call this method before starting, and call `stop` once the
        loop has finished.  You may also use this method as a context manager,
        which will stop the loop automatically at the end of the block:

            with main_loop.start():
                ...

        Note that some event loop implementations don't handle exceptions
        specially if you manage the event loop yourself.  In particular, the
        Twisted and asyncio loops won't stop automatically when
        :exc:`ExitMainLoop` (or anything else) is raised.
        """
        self.screen.start()

        if self.handle_mouse:
            self.screen.set_mouse_tracking()

        if not hasattr(self.screen, 'hook_event_loop'):
            raise CantUseExternalLoop(
                "Screen {0!r} doesn't support external event loops")

        try:
            signals.connect_signal(self.screen, INPUT_DESCRIPTORS_CHANGED,
                self._reset_input_descriptors)
        except NameError:
            pass
        # watch our input descriptors
        self._reset_input_descriptors()
        self.idle_handle = self.event_loop.enter_idle(self.entering_idle)

        return StoppingContext(self)

    def stop(self):
        """
        Cleans up any hooks added to the event loop.  Only call this if you're
        managing the event loop yourself, after the loop stops.
        """
        self.event_loop.remove_enter_idle(self.idle_handle)
        del self.idle_handle
        signals.disconnect_signal(self.screen, INPUT_DESCRIPTORS_CHANGED,
            self._reset_input_descriptors)
        self.screen.unhook_event_loop(self.event_loop)

        self.screen.stop()

    def _reset_input_descriptors(self):
        self.screen.unhook_event_loop(self.event_loop)
        self.screen.hook_event_loop(self.event_loop, self._update)

    def _run(self):
        try:
            self.start()
        except CantUseExternalLoop:
            try:
                return self._run_screen_event_loop()
            finally:
                self.screen.stop()

        try:
            self.event_loop.run()
        except:
            self.screen.stop() # clean up screen control
            raise
        self.stop()

    def _update(self, keys, raw):
        """
        >>> w = _refl("widget")
        >>> w.selectable_rval = True
        >>> w.mouse_event_rval = True
        >>> scr = _refl("screen")
        >>> scr.get_cols_rows_rval = (15, 5)
        >>> evl = _refl("event_loop")
        >>> ml = MainLoop(w, [], scr, event_loop=evl)
        >>> ml._input_timeout = "old timeout"
        >>> ml._update(['y'], [121])    # doctest:+ELLIPSIS
        screen.get_cols_rows()
        widget.selectable()
        widget.keypress((15, 5), 'y')
        >>> ml._update([("mouse press", 1, 5, 4)], [])
        widget.mouse_event((15, 5), 'mouse press', 1, 5, 4, focus=True)
        >>> ml._update([], [])
        """
        keys = self.input_filter(keys, raw)

        if keys:
            self.process_input(keys)
            if 'window resize' in keys:
                self.screen_size = None

    def _run_screen_event_loop(self):
        """
        This method is used when the screen does not support using
        external event loops.

        The alarms stored in the SelectEventLoop in :attr:`event_loop`
        are modified by this method.
        """
        next_alarm = None

        while True:
            self.draw_screen()

            if not next_alarm and self.event_loop._alarms:
                next_alarm = heapq.heappop(self.event_loop._alarms)

            keys = None
            while not keys:
                if next_alarm:
                    sec = max(0, next_alarm[0] - time.time())
                    self.screen.set_input_timeouts(sec)
                else:
                    self.screen.set_input_timeouts(None)
                keys, raw = self.screen.get_input(True)
                if not keys and next_alarm:
                    sec = next_alarm[0] - time.time()
                    if sec <= 0:
                        break

            keys = self.input_filter(keys, raw)

            if keys:
                self.process_input(keys)

            while next_alarm:
                sec = next_alarm[0] - time.time()
                if sec > 0:
                    break
                tm, tie_break, callback = next_alarm
                callback()

                if self.event_loop._alarms:
                    next_alarm = heapq.heappop(self.event_loop._alarms)
                else:
                    next_alarm = None

            if 'window resize' in keys:
                self.screen_size = None

    def _test_run_screen_event_loop(self):
        """
        >>> w = _refl("widget")
        >>> scr = _refl("screen")
        >>> scr.get_cols_rows_rval = (10, 5)
        >>> scr.get_input_rval = [], []
        >>> ml = MainLoop(w, screen=scr)
        >>> def stop_now(loop, data):
        ...     raise ExitMainLoop()
        >>> handle = ml.set_alarm_in(0, stop_now)
        >>> try:
        ...     ml._run_screen_event_loop()
        ... except ExitMainLoop:
        ...     pass
        screen.get_cols_rows()
        widget.render((10, 5), focus=True)
        screen.draw_screen((10, 5), None)
        screen.set_input_timeouts(0)
        screen.get_input(True)
        """

    def process_input(self, keys):
        """
        This method will pass keyboard input and mouse events to :attr:`widget`.
        This method is called automatically from the :meth:`run` method when
        there is input, but may also be called to simulate input from the user.

        *keys* is a list of input returned from :attr:`screen`'s get_input()
        or get_input_nonblocking() methods.

        Returns ``True`` if any key was handled by a widget or the
        :meth:`unhandled_input` method.
        """
        if not self.screen_size:
            self.screen_size = self.screen.get_cols_rows()

        something_handled = False

        for k in keys:
            if k == 'window resize':
                continue
            if is_mouse_event(k):
                event, button, col, row = k
                if self._topmost_widget.mouse_event(self.screen_size,
                    event, button, col, row, focus=True ):
                    k = None
            elif self._topmost_widget.selectable():
                k = self._topmost_widget.keypress(self.screen_size, k)
            if k:
                if command_map[k] == REDRAW_SCREEN:
                    self.screen.clear()
                    something_handled = True
                else:
                    something_handled |= bool(self.unhandled_input(k))
            else:
                something_handled = True

        return something_handled

    def _test_process_input(self):
        """
        >>> w = _refl("widget")
        >>> w.selectable_rval = True
        >>> scr = _refl("screen")
        >>> scr.get_cols_rows_rval = (10, 5)
        >>> ml = MainLoop(w, [], scr)
        >>> ml.process_input(['enter', ('mouse drag', 1, 14, 20)])
        screen.get_cols_rows()
        widget.selectable()
        widget.keypress((10, 5), 'enter')
        widget.mouse_event((10, 5), 'mouse drag', 1, 14, 20, focus=True)
        True
        """

    def input_filter(self, keys, raw):
        """
        This function is passed each all the input events and raw keystroke
        values. These values are passed to the *input_filter* function
        passed to the constructor. That function must return a list of keys to
        be passed to the widgets to handle. If no *input_filter* was
        defined this implementation will return all the input events.
        """
        if self._input_filter:
            return self._input_filter(keys, raw)
        return keys

    def unhandled_input(self, input):
        """
        This function is called with any input that was not handled by the
        widgets, and calls the *unhandled_input* function passed to the
        constructor. If no *unhandled_input* was defined then the input
        will be ignored.

        *input* is the keyboard or mouse input.

        The *unhandled_input* function should return ``True`` if it handled
        the input.
        """
        if self._unhandled_input:
            return self._unhandled_input(input)

    def entering_idle(self):
        """
        This method is called whenever the event loop is about to enter the
        idle state. :meth:`draw_screen` is called here to update the
        screen when anything has changed.
        """
        if self.screen.started:
            self.draw_screen()

    def draw_screen(self):
        """
        Render the widgets and paint the screen. This method is called
        automatically from :meth:`entering_idle`.

        If you modify the widgets displayed outside of handling input or
        responding to an alarm you will need to call this method yourself
        to repaint the screen.
        """
        if not self.screen_size:
            self.screen_size = self.screen.get_cols_rows()

        canvas = self._topmost_widget.render(self.screen_size, focus=True)
        self.screen.draw_screen(self.screen_size, canvas)


class EventLoop(object):
    """
    Abstract class representing an event loop to be used by :class:`MainLoop`.
    """

    def alarm(self, seconds, callback):
        """
        Call callback() a given time from now.  No parameters are
        passed to callback.

        This method has no default implementation.

        Returns a handle that may be passed to remove_alarm()

        seconds -- floating point time to wait before calling callback
        callback -- function to call from event loop
        """
        raise NotImplementedError()

    def enter_idle(self, callback):
        """
        Add a callback for entering idle.

        This method has no default implementation.

        Returns a handle that may be passed to remove_idle()
        """
        raise NotImplementedError()

    def remove_alarm(self, handle):
        """
        Remove an alarm.

        This method has no default implementation.

        Returns True if the alarm exists, False otherwise
        """
        raise NotImplementedError()

    def remove_enter_idle(self, handle):
        """
        Remove an idle callback.

        This method has no default implementation.

        Returns True if the handle was removed.
        """
        raise NotImplementedError()

    def remove_watch_file(self, handle):
        """
        Remove an input file.

        This method has no default implementation.

        Returns True if the input file exists, False otherwise
        """
        raise NotImplementedError()

    def run(self):
        """
        Start the event loop.  Exit the loop when any callback raises
        an exception.  If ExitMainLoop is raised, exit cleanly.

        This method has no default implementation.
        """
        raise NotImplementedError()

    def watch_file(self, fd, callback):
        """
        Call callback() when fd has some data to read.  No parameters
        are passed to callback.

        This method has no default implementation.

        Returns a handle that may be passed to remove_watch_file()

        fd -- file descriptor to watch for input
        callback -- function to call when input is available
        """
        raise NotImplementedError()

    def set_signal_handler(self, signum, handler):
        """
        Sets the signal handler for signal signum.

        The default implementation of :meth:`set_signal_handler`
        is simply a proxy function that calls :func:`signal.signal()`
        and returns the resulting value.

        signum -- signal number
        handler -- function (taking signum as its single argument),
        or `signal.SIG_IGN`, or `signal.SIG_DFL`
        """
        return signal.signal(signum, handler)

class SelectEventLoop(EventLoop):
    """
    Event loop based on :func:`select.select`
    """

    def __init__(self):
        self._alarms = []
        self._watch_files = {}
        self._idle_handle = 0
        self._idle_callbacks = {}
        self._tie_break = count()

    def alarm(self, seconds, callback):
        """
        Call callback() a given time from now.  No parameters are
        passed to callback.

        Returns a handle that may be passed to remove_alarm()

        seconds -- floating point time to wait before calling callback
        callback -- function to call from event loop
        """
        tm = time.time() + seconds
        handle = (tm, next(self._tie_break), callback)
        heapq.heappush(self._alarms, handle)
        return handle

    def remove_alarm(self, handle):
        """
        Remove an alarm.

        Returns True if the alarm exists, False otherwise
        """
        try:
            self._alarms.remove(handle)
            heapq.heapify(self._alarms)
            return True
        except ValueError:
            return False

    def watch_file(self, fd, callback):
        """
        Call callback() when fd has some data to read.  No parameters
        are passed to callback.

        Returns a handle that may be passed to remove_watch_file()

        fd -- file descriptor to watch for input
        callback -- function to call when input is available
        """
        self._watch_files[fd] = callback
        return fd

    def remove_watch_file(self, handle):
        """
        Remove an input file.

        Returns True if the input file exists, False otherwise
        """
        if handle in self._watch_files:
            del self._watch_files[handle]
            return True
        return False

    def enter_idle(self, callback):
        """
        Add a callback for entering idle.

        Returns a handle that may be passed to remove_idle()
        """
        self._idle_handle += 1
        self._idle_callbacks[self._idle_handle] = callback
        return self._idle_handle

    def remove_enter_idle(self, handle):
        """
        Remove an idle callback.

        Returns True if the handle was removed.
        """
        try:
            del self._idle_callbacks[handle]
        except KeyError:
            return False
        return True

    def _entering_idle(self):
        """
        Call all the registered idle callbacks.
        """
        for callback in self._idle_callbacks.values():
            callback()

    def run(self):
        """
        Start the event loop.  Exit the loop when any callback raises
        an exception.  If ExitMainLoop is raised, exit cleanly.
        """
        try:
            self._did_something = True
            while True:
                try:
                    self._loop()
                except select.error as e:
                    if e.args[0] != 4:
                        # not just something we need to retry
                        raise
        except ExitMainLoop:
            pass

    def _loop(self):
        """
        A single iteration of the event loop
        """
        fds = list(self._watch_files.keys())
        if self._alarms or self._did_something:
            if self._alarms:
                tm = self._alarms[0][0]
                timeout = max(0, tm - time.time())
            if self._did_something and (not self._alarms or
                    (self._alarms and timeout > 0)):
                timeout = 0
                tm = 'idle'
            ready, w, err = select.select(fds, [], fds, timeout)
        else:
            tm = None
            ready, w, err = select.select(fds, [], fds)

        if not ready:
            if tm == 'idle':
                self._entering_idle()
                self._did_something = False
            elif tm is not None:
                # must have been a timeout
                tm, tie_break, alarm_callback = heapq.heappop(self._alarms)
                alarm_callback()
                self._did_something = True

        for fd in ready:
            self._watch_files[fd]()
            self._did_something = True


class GLibEventLoop(EventLoop):
    """
    Event loop based on GLib.MainLoop
    """

    def __init__(self):
        from gi.repository import GLib
        self.GLib = GLib
        self._alarms = []
        self._watch_files = {}
        self._idle_handle = 0
        self._glib_idle_enabled = False # have we called glib.idle_add?
        self._idle_callbacks = {}
        self._loop = GLib.MainLoop()
        self._exc_info = None
        self._enable_glib_idle()
        self._signal_handlers = {}

    def alarm(self, seconds, callback):
        """
        Call callback() a given time from now.  No parameters are
        passed to callback.

        Returns a handle that may be passed to remove_alarm()

        seconds -- floating point time to wait before calling callback
        callback -- function to call from event loop
        """
        @self.handle_exit
        def ret_false():
            callback()
            self._enable_glib_idle()
            return False
        fd = self.GLib.timeout_add(int(seconds*1000), ret_false)
        self._alarms.append(fd)
        return (fd, callback)

    def set_signal_handler(self, signum, handler):
        """
        Sets the signal handler for signal signum.

        .. WARNING::
            Because this method uses the `GLib`-specific `unix_signal_add`
            function, its behaviour is different than `signal.signal().`

            If `signum` is not `SIGHUP`, `SIGINT`, `SIGTERM`, `SIGUSR1`,
            `SIGUSR2` or `SIGWINCH`, this method performs no actions and
            immediately returns None.

            Returns None in all cases (unlike :func:`signal.signal()`).
        ..

        signum -- signal number
        handler -- function (taking signum as its single argument),
        or `signal.SIG_IGN`, or `signal.SIG_DFL`
        """
        glib_signals = [
            signal.SIGHUP,
            signal.SIGINT,
            signal.SIGTERM,
            signal.SIGUSR1,
            signal.SIGUSR2,
            signal.SIGWINCH
        ]

        if signum not in glib_signals:
            # The GLib event loop supports only the signals listed above
            return

        if signum in self._signal_handlers:
            self.GLib.source_remove(self._signal_handlers.pop(signum))

        if handler == signal.SIG_IGN:
            handler = lambda x: None
        elif handler == signal.SIG_DFL:
            return

        def final_handler(signal_number):
            handler(signal_number)
            return self.GLib.SOURCE_CONTINUE

        source = self.GLib.unix_signal_add(self.GLib.PRIORITY_DEFAULT, signum, final_handler, signum)
        self._signal_handlers[signum] = source

    def remove_alarm(self, handle):
        """
        Remove an alarm.

        Returns True if the alarm exists, False otherwise
        """
        try:
            self._alarms.remove(handle[0])
            self.GLib.source_remove(handle[0])
            return True
        except ValueError:
            return False

    def watch_file(self, fd, callback):
        """
        Call callback() when fd has some data to read.  No parameters
        are passed to callback.

        Returns a handle that may be passed to remove_watch_file()

        fd -- file descriptor to watch for input
        callback -- function to call when input is available
        """
        @self.handle_exit
        def io_callback(source, cb_condition):
            callback()
            self._enable_glib_idle()
            return True
        self._watch_files[fd] = \
             self.GLib.io_add_watch(fd,self.GLib.IO_IN,io_callback)
        return fd

    def remove_watch_file(self, handle):
        """
        Remove an input file.

        Returns True if the input file exists, False otherwise
        """
        if handle in self._watch_files:
            self.GLib.source_remove(self._watch_files[handle])
            del self._watch_files[handle]
            return True
        return False

    def enter_idle(self, callback):
        """
        Add a callback for entering idle.

        Returns a handle that may be passed to remove_enter_idle()
        """
        self._idle_handle += 1
        self._idle_callbacks[self._idle_handle] = callback
        return self._idle_handle

    def _enable_glib_idle(self):
        if self._glib_idle_enabled:
            return
        self.GLib.idle_add(self._glib_idle_callback)
        self._glib_idle_enabled = True

    def _glib_idle_callback(self):
        for callback in self._idle_callbacks.values():
            callback()
        self._glib_idle_enabled = False
        return False # ask glib not to call again (or we would be called

    def remove_enter_idle(self, handle):
        """
        Remove an idle callback.

        Returns True if the handle was removed.
        """
        try:
            del self._idle_callbacks[handle]
        except KeyError:
            return False
        return True

    def run(self):
        """
        Start the event loop.  Exit the loop when any callback raises
        an exception.  If ExitMainLoop is raised, exit cleanly.
        """
        try:
            self._loop.run()
        finally:
            if self._loop.is_running():
                self._loop.quit()
        if self._exc_info:
            # An exception caused us to exit, raise it now
            exc_info = self._exc_info
            self._exc_info = None
            reraise(*exc_info)

    def handle_exit(self,f):
        """
        Decorator that cleanly exits the :class:`GLibEventLoop` if
        :exc:`ExitMainLoop` is thrown inside of the wrapped function. Store the
        exception info if some other exception occurs, it will be reraised after
        the loop quits.

        *f* -- function to be wrapped
        """
        def wrapper(*args,**kargs):
            try:
                return f(*args,**kargs)
            except ExitMainLoop:
                self._loop.quit()
            except:
                import sys
                self._exc_info = sys.exc_info()
                if self._loop.is_running():
                    self._loop.quit()
            return False
        return wrapper


class TornadoEventLoop(EventLoop):
    """ This is an Urwid-specific event loop to plug into its MainLoop.
        It acts as an adaptor for Tornado's IOLoop which does all
        heavy lifting except idle-callbacks.

        Notice, since Tornado has no concept of idle callbacks we
        monkey patch ioloop._impl.poll() function to be able to detect
        potential idle periods.
    """
    _ioloop_registry = WeakKeyDictionary()  # {<ioloop> : {<handle> : <idle_func>}}
    _max_idle_handle = 0

    class PollProxy(object):
        """ A simple proxy for a Python's poll object that wraps the .poll() method
            in order to detect idle periods and call Urwid callbacks
        """
        def __init__(self, poll_obj, idle_map):
            self.__poll_obj = poll_obj
            self.__idle_map = idle_map
            self._idle_done = False
            self._prev_timeout = 0

        def __getattr__(self, name):
            return getattr(self.__poll_obj, name)

        def poll(self, timeout):
            if timeout > self._prev_timeout:
                # if timeout increased we assume a timer event was handled
                self._idle_done = False
            self._prev_timeout = timeout
            start = time.time()

            # any IO pending wins
            events = self.__poll_obj.poll(0)
            if events:
                self._idle_done = False
                return events

            # our chance to enter idle
            if not self._idle_done:
                for callback in self.__idle_map.values():
                    callback()
                self._idle_done = True

            # then complete the actual request (adjusting timeout)
            timeout = max(0, min(timeout, timeout + start - time.time()))
            events = self.__poll_obj.poll(timeout)
            if events:
                self._idle_done = False
            return events

    @classmethod
    def _patch_poll_impl(cls, ioloop):
        """ Wraps original poll object in the IOLoop's poll object
        """
        if ioloop in cls._ioloop_registry:
            return  # we already patched this instance

        cls._ioloop_registry[ioloop] = idle_map = {}
        ioloop._impl = cls.PollProxy(ioloop._impl, idle_map)

    def __init__(self, ioloop=None):
        if not ioloop:
            from tornado.ioloop import IOLoop
            ioloop = IOLoop.instance()
        self._ioloop = ioloop
        self._patch_poll_impl(ioloop)
        self._pending_alarms = {}
        self._watch_handles    = {}  # {<watch_handle> : <file_descriptor>}
        self._max_watch_handle = 0
        self._exception        = None

    def alarm(self, secs, callback):
        ioloop  = self._ioloop
        def wrapped():
            try:
                del self._pending_alarms[handle]
            except KeyError:
                pass
            self.handle_exit(callback)()
        handle = ioloop.add_timeout(ioloop.time() + secs, wrapped)
        self._pending_alarms[handle] = 1
        return handle

    def remove_alarm(self, handle):
        self._ioloop.remove_timeout(handle)
        try:
            del self._pending_alarms[handle]
        except KeyError:
            return False
        else:
            return True

    def watch_file(self, fd, callback):
        from tornado.ioloop import IOLoop
        handler = lambda fd,events: self.handle_exit(callback)()
        self._ioloop.add_handler(fd, handler, IOLoop.READ)
        self._max_watch_handle += 1
        handle = self._max_watch_handle
        self._watch_handles[handle] = fd
        return handle

    def remove_watch_file(self, handle):
        fd = self._watch_handles.pop(handle, None)
        if fd is None:
            return False
        else:
            self._ioloop.remove_handler(fd)
            return True

    def enter_idle(self, callback):
        self._max_idle_handle += 1
        handle   = self._max_idle_handle
        idle_map = self._ioloop_registry[self._ioloop]
        idle_map[handle] = callback
        return handle

    def remove_enter_idle(self, handle):
        idle_map = self._ioloop_registry[self._ioloop]
        cb = idle_map.pop(handle, None)
        return cb is not None

    def handle_exit(self, func):
        @wraps(func)
        def wrapper(*args, **kw):
            try:
                return func(*args, **kw)
            except ExitMainLoop:
                self._ioloop.stop()
            except Exception as exc:
                self._exception = exc
                self._ioloop.stop()
            return False
        return wrapper

    def run(self):
        self._ioloop.start()
        if self._exception:
            exc, self._exception = self._exception, None
            raise exc


try:
    from twisted.internet.abstract import FileDescriptor
except ImportError:
    FileDescriptor = object

class TwistedInputDescriptor(FileDescriptor):
    def __init__(self, reactor, fd, cb):
        self._fileno = fd
        self.cb = cb
        FileDescriptor.__init__(self, reactor)

    def fileno(self):
        return self._fileno

    def doRead(self):
        return self.cb()


class TwistedEventLoop(EventLoop):
    """
    Event loop based on Twisted_
    """
    _idle_emulation_delay = 1.0/256 # a short time (in seconds)

    def __init__(self, reactor=None, manage_reactor=True):
        """
        :param reactor: reactor to use
        :type reactor: :class:`twisted.internet.reactor`.
        :param: manage_reactor: `True` if you want this event loop to run
                                and stop the reactor.
        :type manage_reactor: boolean

        .. WARNING::
           Twisted's reactor doesn't like to be stopped and run again.  If you
           need to stop and run your :class:`MainLoop`, consider setting
           ``manage_reactor=False`` and take care of running/stopping the reactor
           at the beginning/ending of your program yourself.

           You can also forego using :class:`MainLoop`'s run() entirely, and
           instead call start() and stop() before and after starting the
           reactor.

        .. _Twisted: http://twistedmatrix.com/trac/
        """
        if reactor is None:
            import twisted.internet.reactor
            reactor = twisted.internet.reactor
        self.reactor = reactor
        self._alarms = []
        self._watch_files = {}
        self._idle_handle = 0
        self._twisted_idle_enabled = False
        self._idle_callbacks = {}
        self._exc_info = None
        self.manage_reactor = manage_reactor
        self._enable_twisted_idle()

    def alarm(self, seconds, callback):
        """
        Call callback() a given time from now.  No parameters are
        passed to callback.

        Returns a handle that may be passed to remove_alarm()

        seconds -- floating point time to wait before calling callback
        callback -- function to call from event loop
        """
        handle = self.reactor.callLater(seconds, self.handle_exit(callback))
        return handle

    def remove_alarm(self, handle):
        """
        Remove an alarm.

        Returns True if the alarm exists, False otherwise
        """
        from twisted.internet.error import AlreadyCancelled, AlreadyCalled
        try:
            handle.cancel()
            return True
        except AlreadyCancelled:
            return False
        except AlreadyCalled:
            return False

    def watch_file(self, fd, callback):
        """
        Call callback() when fd has some data to read.  No parameters
        are passed to callback.

        Returns a handle that may be passed to remove_watch_file()

        fd -- file descriptor to watch for input
        callback -- function to call when input is available
        """
        ind = TwistedInputDescriptor(self.reactor, fd,
            self.handle_exit(callback))
        self._watch_files[fd] = ind
        self.reactor.addReader(ind)
        return fd

    def remove_watch_file(self, handle):
        """
        Remove an input file.

        Returns True if the input file exists, False otherwise
        """
        if handle in self._watch_files:
            self.reactor.removeReader(self._watch_files[handle])
            del self._watch_files[handle]
            return True
        return False

    def enter_idle(self, callback):
        """
        Add a callback for entering idle.

        Returns a handle that may be passed to remove_enter_idle()
        """
        self._idle_handle += 1
        self._idle_callbacks[self._idle_handle] = callback
        return self._idle_handle

    def _enable_twisted_idle(self):
        """
        Twisted's reactors don't have an idle or enter-idle callback
        so the best we can do for now is to set a timer event in a very
        short time to approximate an enter-idle callback.

        .. WARNING::
           This will perform worse than the other event loops until we can find a
           fix or workaround
        """
        if self._twisted_idle_enabled:
            return
        self.reactor.callLater(self._idle_emulation_delay,
            self.handle_exit(self._twisted_idle_callback, enable_idle=False))
        self._twisted_idle_enabled = True

    def _twisted_idle_callback(self):
        for callback in self._idle_callbacks.values():
            callback()
        self._twisted_idle_enabled = False

    def remove_enter_idle(self, handle):
        """
        Remove an idle callback.

        Returns True if the handle was removed.
        """
        try:
            del self._idle_callbacks[handle]
        except KeyError:
            return False
        return True

    def run(self):
        """
        Start the event loop.  Exit the loop when any callback raises
        an exception.  If ExitMainLoop is raised, exit cleanly.
        """
        if not self.manage_reactor:
            return
        self.reactor.run()
        if self._exc_info:
            # An exception caused us to exit, raise it now
            exc_info = self._exc_info
            self._exc_info = None
            reraise(*exc_info)

    def handle_exit(self, f, enable_idle=True):
        """
        Decorator that cleanly exits the :class:`TwistedEventLoop` if
        :class:`ExitMainLoop` is thrown inside of the wrapped function. Store the
        exception info if some other exception occurs, it will be reraised after
        the loop quits.

        *f* -- function to be wrapped
        """
        def wrapper(*args,**kargs):
            rval = None
            try:
                rval = f(*args,**kargs)
            except ExitMainLoop:
                if self.manage_reactor:
                    self.reactor.stop()
            except:
                import sys
                print(sys.exc_info())
                self._exc_info = sys.exc_info()
                if self.manage_reactor:
                    self.reactor.crash()
            if enable_idle:
                self._enable_twisted_idle()
            return rval
        return wrapper


class AsyncioEventLoop(EventLoop):
    """
    Event loop based on the standard library ``asyncio`` module.

    ``asyncio`` is new in Python 3.4, but also exists as a backport on PyPI for
    Python 3.3.  The ``trollius`` package is available for older Pythons with
    slightly different syntax, but also works with this loop.
    """
    _we_started_event_loop = False

    _idle_emulation_delay = 1.0/256  # a short time (in seconds)

    def __init__(self, **kwargs):
        if 'loop' in kwargs:
            self._loop = kwargs.pop('loop')
        else:
            import asyncio
            self._loop = asyncio.get_event_loop()

    def alarm(self, seconds, callback):
        """
        Call callback() a given time from now.  No parameters are
        passed to callback.

        Returns a handle that may be passed to remove_alarm()

        seconds -- time in seconds to wait before calling callback
        callback -- function to call from event loop
        """
        return self._loop.call_later(seconds, callback)

    def remove_alarm(self, handle):
        """
        Remove an alarm.

        Returns True if the alarm exists, False otherwise
        """
        existed = not handle._cancelled
        handle.cancel()
        return existed

    def watch_file(self, fd, callback):
        """
        Call callback() when fd has some data to read.  No parameters
        are passed to callback.

        Returns a handle that may be passed to remove_watch_file()

        fd -- file descriptor to watch for input
        callback -- function to call when input is available
        """
        self._loop.add_reader(fd, callback)
        return fd

    def remove_watch_file(self, handle):
        """
        Remove an input file.

        Returns True if the input file exists, False otherwise
        """
        return self._loop.remove_reader(handle)

    def enter_idle(self, callback):
        """
        Add a callback for entering idle.

        Returns a handle that may be passed to remove_idle()
        """
        # XXX there's no such thing as "idle" in most event loops; this fakes
        # it the same way as Twisted, by scheduling the callback to be called
        # repeatedly
        mutable_handle = [None]
        def faux_idle_callback():
            callback()
            mutable_handle[0] = self._loop.call_later(
                self._idle_emulation_delay, faux_idle_callback)

        mutable_handle[0] = self._loop.call_later(
            self._idle_emulation_delay, faux_idle_callback)

        return mutable_handle

    def remove_enter_idle(self, handle):
        """
        Remove an idle callback.

        Returns True if the handle was removed.
        """
        # `handle` is just a list containing the current actual handle
        return self.remove_alarm(handle[0])

    _exc_info = None

    def _exception_handler(self, loop, context):
        exc = context.get('exception')
        if exc:
            loop.stop()
            if not isinstance(exc, ExitMainLoop):
                # Store the exc_info so we can re-raise after the loop stops
                import sys
                self._exc_info = sys.exc_info()
        else:
            loop.default_exception_handler(context)

    def run(self):
        """
        Start the event loop.  Exit the loop when any callback raises
        an exception.  If ExitMainLoop is raised, exit cleanly.
        """
        self._loop.set_exception_handler(self._exception_handler)
        self._loop.run_forever()
        if self._exc_info:
            exc_info = self._exc_info
            self._exc_info = None
            reraise(*exc_info)


def _refl(name, rval=None, exit=False):
    """
    This function is used to test the main loop classes.

    >>> scr = _refl("screen")
    >>> scr.function("argument")
    screen.function('argument')
    >>> scr.callme(when="now")
    screen.callme(when='now')
    >>> scr.want_something_rval = 42
    >>> x = scr.want_something()
    screen.want_something()
    >>> x
    42

    """
    class Reflect(object):
        def __init__(self, name, rval=None):
            self._name = name
            self._rval = rval
        def __call__(self, *argl, **argd):
            args = ", ".join([repr(a) for a in argl])
            if args and argd:
                args = args + ", "
            args = args + ", ".join([k+"="+repr(v) for k,v in argd.items()])
            print(self._name+"("+args+")")
            if exit:
                raise ExitMainLoop()
            return self._rval
        def __getattr__(self, attr):
            if attr.endswith("_rval"):
                raise AttributeError()
            #print self._name+"."+attr
            if hasattr(self, attr+"_rval"):
                return Reflect(self._name+"."+attr, getattr(self, attr+"_rval"))
            return Reflect(self._name+"."+attr)
    return Reflect(name)

def _test():
    import doctest
    doctest.testmod()

if __name__=='__main__':
    _test()
