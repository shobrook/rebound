#!/usr/bin/python
#
# Urwid signal dispatching
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

import itertools
import weakref


class MetaSignals(type):
    """
    register the list of signals in the class variable signals,
    including signals in superclasses.
    """
    def __init__(cls, name, bases, d):
        signals = d.get("signals", [])
        for superclass in cls.__bases__:
            signals.extend(getattr(superclass, 'signals', []))
        signals = list(dict([(x,None) for x in signals]).keys())
        d["signals"] = signals
        register_signal(cls, signals)
        super(MetaSignals, cls).__init__(name, bases, d)

def setdefaultattr(obj, name, value):
    # like dict.setdefault() for object attributes
    if hasattr(obj, name):
        return getattr(obj, name)
    setattr(obj, name, value)
    return value

class Key(object):
    """
    Minimal class, whose only purpose is to produce objects with a
    unique hash
    """
    __slots__ = []

class Signals(object):
    _signal_attr = '_urwid_signals' # attribute to attach to signal senders

    def __init__(self):
        self._supported = {}

    def register(self, sig_cls, signals):
        """
        :param sig_class: the class of an object that will be sending signals
        :type sig_class: class
        :param signals: a list of signals that may be sent, typically each
                        signal is represented by a string
        :type signals: signal names

        This function must be called for a class before connecting any
        signal callbacks or emitting any signals from that class' objects
        """
        self._supported[sig_cls] = signals

    def connect(self, obj, name, callback, user_arg=None, weak_args=None, user_args=None):
        """
        :param obj: the object sending a signal
        :type obj: object
        :param name: the signal to listen for, typically a string
        :type name: signal name
        :param callback: the function to call when that signal is sent
        :type callback: function
        :param user_arg: deprecated additional argument to callback (appended
                         after the arguments passed when the signal is
                         emitted). If None no arguments will be added.
                         Don't use this argument, use user_args instead.
        :param weak_args: additional arguments passed to the callback
                          (before any arguments passed when the signal
                          is emitted and before any user_args).

                          These arguments are stored as weak references
                          (but converted back into their original value
                          before passing them to callback) to prevent
                          any objects referenced (indirectly) from
                          weak_args from being kept alive just because
                          they are referenced by this signal handler.

                          Use this argument only as a keyword argument,
                          since user_arg might be removed in the future.
        :type weak_args: iterable
        :param user_args: additional arguments to pass to the callback,
                          (before any arguments passed when the signal
                          is emitted but after any weak_args).

                          Use this argument only as a keyword argument,
                          since user_arg might be removed in the future.
        :type user_args: iterable

        When a matching signal is sent, callback will be called. The
        arguments it receives will be the user_args passed at connect
        time (as individual arguments) followed by all the positional
        parameters sent with the signal.

        As an example of using weak_args, consider the following snippet:

        >>> import urwid
        >>> debug = urwid.Text('')
        >>> def handler(widget, newtext):
        ...    debug.set_text("Edit widget changed to %s" % newtext)
        >>> edit = urwid.Edit('')
        >>> key = urwid.connect_signal(edit, 'change', handler)

        If you now build some interface using "edit" and "debug", the
        "debug" widget will show whatever you type in the "edit" widget.
        However, if you remove all references to the "debug" widget, it
        will still be kept alive by the signal handler. This because the
        signal handler is a closure that (implicitly) references the
        "edit" widget. If you want to allow the "debug" widget to be
        garbage collected, you can create a "fake" or "weak" closure
        (it's not really a closure, since it doesn't reference any
        outside variables, so it's just a dynamic function):

        >>> debug = urwid.Text('')
        >>> def handler(weak_debug, widget, newtext):
        ...    weak_debug.set_text("Edit widget changed to %s" % newtext)
        >>> edit = urwid.Edit('')
        >>> key = urwid.connect_signal(edit, 'change', handler, weak_args=[debug])

        Here the weak_debug parameter in print_debug is the value passed
        in the weak_args list to connect_signal. Note that the
        weak_debug value passed is not a weak reference anymore, the
        signals code transparently dereferences the weakref parameter
        before passing it to print_debug.

        Returns a key associated by this signal handler, which can be
        used to disconnect the signal later on using
        urwid.disconnect_signal_by_key. Alternatively, the signal
        handler can also be disconnected by calling
        urwid.disconnect_signal, which doesn't need this key.
        """

        sig_cls = obj.__class__
        if not name in self._supported.get(sig_cls, []):
            raise NameError("No such signal %r for object %r" %
                (name, obj))

        # Just generate an arbitrary (but unique) key
        key = Key()

        signals = setdefaultattr(obj, self._signal_attr, {})
        handlers = signals.setdefault(name, [])

        # Remove the signal handler when any of the weakref'd arguments
        # are garbage collected. Note that this means that the handlers
        # dictionary can be modified _at any time_, so it should never
        # be iterated directly (e.g. iterate only over .keys() and
        # .items(), never over .iterkeys(), .iteritems() or the object
        # itself).
        # We let the callback keep a weakref to the object as well, to
        # prevent a circular reference between the handler and the
        # object (via the weakrefs, which keep strong references to
        # their callbacks) from existing.
        obj_weak = weakref.ref(obj)
        def weakref_callback(weakref):
            o = obj_weak()
            if o:
                try:
                    del getattr(o, self._signal_attr, {})[name][key]
                except KeyError:
                    pass

        user_args = self._prepare_user_args(weak_args, user_args, weakref_callback)
        handlers.append((key, callback, user_arg, user_args))

        return key

    def _prepare_user_args(self, weak_args, user_args, callback = None):
        # Turn weak_args into weakrefs and prepend them to user_args
        return [weakref.ref(a, callback) for a in (weak_args or [])] + (user_args or [])


    def disconnect(self, obj, name, callback, user_arg=None, weak_args=None, user_args=None):
        """
        :param obj: the object to disconnect the signal from
        :type obj: object
        :param name: the signal to disconnect, typically a string
        :type name: signal name
        :param callback: the callback function passed to connect_signal
        :type callback: function
        :param user_arg: the user_arg parameter passed to connect_signal
        :param weak_args: the weak_args parameter passed to connect_signal
        :param user_args: the weak_args parameter passed to connect_signal

        This function will remove a callback from the list connected
        to a signal with connect_signal(). The arguments passed should
        be exactly the same as those passed to connect_signal().

        If the callback is not connected or already disconnected, this
        function will simply do nothing.
        """
        signals = setdefaultattr(obj, self._signal_attr, {})
        if name not in signals:
            return

        handlers = signals[name]

        # Do the same processing as in connect, so we can compare the
        # resulting tuple.
        user_args = self._prepare_user_args(weak_args, user_args)

        # Remove the given handler
        for h in handlers:
            if h[1:] == (callback, user_arg, user_args):
                return self.disconnect_by_key(obj, name, h[0])

    def disconnect_by_key(self, obj, name, key):
        """
        :param obj: the object to disconnect the signal from
        :type obj: object
        :param name: the signal to disconnect, typically a string
        :type name: signal name
        :param key: the key for this signal handler, as returned by
                    connect_signal().
        :type key: Key

        This function will remove a callback from the list connected
        to a signal with connect_signal(). The key passed should be the
        value returned by connect_signal().

        If the callback is not connected or already disconnected, this
        function will simply do nothing.
        """
        signals = setdefaultattr(obj, self._signal_attr, {})
        handlers = signals.get(name, [])
        handlers[:] = [h for h in handlers if h[0] is not key]

    def emit(self, obj, name, *args):
        """
        :param obj: the object sending a signal
        :type obj: object
        :param name: the signal to send, typically a string
        :type name: signal name
        :param \*args: zero or more positional arguments to pass to the signal
                      callback functions

        This function calls each of the callbacks connected to this signal
        with the args arguments as positional parameters.

        This function returns True if any of the callbacks returned True.
        """
        result = False
        signals = getattr(obj, self._signal_attr, {})
        handlers = signals.get(name, [])
        for key, callback, user_arg, user_args in handlers:
            result |= self._call_callback(callback, user_arg, user_args, args)
        return result

    def _call_callback(self, callback, user_arg, user_args, emit_args):
        if user_args:
            args_to_pass = []
            for arg in user_args:
                if isinstance(arg, weakref.ReferenceType):
                    arg = arg()
                    if arg is None:
                        # If the weakref is None, the referenced object
                        # was cleaned up. We just skip the entire
                        # callback in this case. The weakref cleanup
                        # handler will have removed the callback when
                        # this happens, so no need to actually remove
                        # the callback here.
                        return False
                args_to_pass.append(arg)

            args_to_pass.extend(emit_args)
        else:
            # Optimization: Don't create a new list when there are
            # no user_args
            args_to_pass = emit_args

        # The deprecated user_arg argument was added to the end
        # instead of the beginning.
        if user_arg is not None:
            args_to_pass = itertools.chain(args_to_pass, (user_arg,))

        return bool(callback(*args_to_pass))

_signals = Signals()
emit_signal = _signals.emit
register_signal = _signals.register
connect_signal = _signals.connect
disconnect_signal = _signals.disconnect
disconnect_signal_by_key = _signals.disconnect_by_key

