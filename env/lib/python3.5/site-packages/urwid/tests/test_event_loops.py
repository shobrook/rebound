import os
import unittest
import platform

import urwid
from urwid.compat import PYTHON3


class EventLoopTestMixin(object):
    def test_event_loop(self):
        rd, wr = os.pipe()
        evl = self.evl
        out = []
        def step1():
            out.append("writing")
            os.write(wr, "hi".encode('ascii'))
        def step2():
            out.append(os.read(rd, 2).decode('ascii'))
            raise urwid.ExitMainLoop
        handle = evl.alarm(0, step1)
        handle = evl.watch_file(rd, step2)
        evl.run()
        self.assertEqual(out, ["writing", "hi"])

    def test_remove_alarm(self):
        evl = self.evl
        handle = evl.alarm(50, lambda: None)
        self.assertTrue(evl.remove_alarm(handle))
        self.assertFalse(evl.remove_alarm(handle))

    def test_remove_watch_file(self):
        evl = self.evl
        fd_r, fd_w = os.pipe()
        try:
            handle = evl.watch_file(fd_r, lambda: None)
            self.assertTrue(evl.remove_watch_file(handle))
            self.assertFalse(evl.remove_watch_file(handle))
        finally:
            os.close(fd_r)
            os.close(fd_w)

    _expected_idle_handle = 1

    def test_run(self):
        evl = self.evl
        out = []
        rd, wr = os.pipe()
        self.assertEqual(os.write(wr, "data".encode('ascii')), 4)
        def say_hello():
            out.append("hello")
        def say_waiting():
            out.append("waiting")
        def exit_clean():
            out.append("clean exit")
            raise urwid.ExitMainLoop
        def exit_error():
            1/0
        handle = evl.alarm(0.01, exit_clean)
        handle = evl.alarm(0.005, say_hello)
        idle_handle = evl.enter_idle(say_waiting)
        if self._expected_idle_handle is not None:
            self.assertEqual(idle_handle, 1)
        evl.run()
        self.assertTrue("hello" in out, out)
        self.assertTrue("clean exit"in out, out)
        handle = evl.watch_file(rd, exit_clean)
        del out[:]
        evl.run()
        self.assertEqual(out, ["clean exit"])
        self.assertTrue(evl.remove_watch_file(handle))
        handle = evl.alarm(0, exit_error)
        self.assertRaises(ZeroDivisionError, evl.run)
        handle = evl.watch_file(rd, exit_error)
        self.assertRaises(ZeroDivisionError, evl.run)


class SelectEventLoopTest(unittest.TestCase, EventLoopTestMixin):
    def setUp(self):
        self.evl = urwid.SelectEventLoop()


try:
    import gi.repository
except ImportError:
    pass
else:
    class GLibEventLoopTest(unittest.TestCase, EventLoopTestMixin):
        def setUp(self):
            self.evl = urwid.GLibEventLoop()

        def test_error(self):
            evl = self.evl
            evl.alarm(0.5, lambda: 1 / 0)  # Simulate error in event loop
            self.assertRaises(ZeroDivisionError, evl.run)


try:
    import tornado
except ImportError:
    pass
else:
    class TornadoEventLoopTest(unittest.TestCase, EventLoopTestMixin):
        def setUp(self):
            from tornado.ioloop import IOLoop
            self.evl = urwid.TornadoEventLoop(IOLoop())


try:
    import twisted
except ImportError:
    pass
else:
    class TwistedEventLoopTest(unittest.TestCase, EventLoopTestMixin):
        def setUp(self):
            self.evl = urwid.TwistedEventLoop()

        # can't restart twisted reactor, so use shortened tests
        def test_event_loop(self):
            pass

        def test_run(self):
            evl = self.evl
            out = []
            rd, wr = os.pipe()
            self.assertEqual(os.write(wr, "data".encode('ascii')), 4)
            def step2():
                out.append(os.read(rd, 2).decode('ascii'))
            def say_hello():
                out.append("hello")
            def say_waiting():
                out.append("waiting")
            def exit_clean():
                out.append("clean exit")
                raise urwid.ExitMainLoop
            def exit_error():
                1/0
            handle = evl.watch_file(rd, step2)
            handle = evl.alarm(0.1, exit_clean)
            handle = evl.alarm(0.05, say_hello)
            self.assertEqual(evl.enter_idle(say_waiting), 1)
            evl.run()
            self.assertTrue("da" in out, out)
            self.assertTrue("ta" in out, out)
            self.assertTrue("hello" in out, out)
            self.assertTrue("clean exit" in out, out)

        def test_error(self):
            evl = self.evl
            evl.alarm(0.5, lambda: 1 / 0)  # Simulate error in event loop
            self.assertRaises(ZeroDivisionError, evl.run)

try:
    import asyncio
except ImportError:
    pass
else:
    class AsyncioEventLoopTest(unittest.TestCase, EventLoopTestMixin):
        def setUp(self):
            self.evl = urwid.AsyncioEventLoop()

        _expected_idle_handle = None

        def test_error(self):
            evl = self.evl
            evl.alarm(0.5, lambda: 1 / 0)  # Simulate error in event loop
            self.assertRaises(ZeroDivisionError, evl.run)
