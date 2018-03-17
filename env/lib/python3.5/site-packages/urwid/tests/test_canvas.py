import unittest

from urwid import canvas
from urwid.compat import B
import urwid


class CanvasCacheTest(unittest.TestCase):
    def setUp(self):
        # purge the cache
        urwid.CanvasCache._widgets.clear()

    def cct(self, widget, size, focus, expected):
        got = urwid.CanvasCache.fetch(widget, urwid.Widget, size, focus)
        assert expected==got, "got: %s expected: %s"%(got, expected)

    def test1(self):
        a = urwid.Text("")
        b = urwid.Text("")
        blah = urwid.TextCanvas()
        blah.finalize(a, (10,1), False)
        blah2 = urwid.TextCanvas()
        blah2.finalize(a, (15,1), False)
        bloo = urwid.TextCanvas()
        bloo.finalize(b, (20,2), True)

        urwid.CanvasCache.store(urwid.Widget, blah)
        urwid.CanvasCache.store(urwid.Widget, blah2)
        urwid.CanvasCache.store(urwid.Widget, bloo)

        self.cct(a, (10,1), False, blah)
        self.cct(a, (15,1), False, blah2)
        self.cct(a, (15,1), True, None)
        self.cct(a, (10,2), False, None)
        self.cct(b, (20,2), True, bloo)
        self.cct(b, (21,2), True, None)
        urwid.CanvasCache.invalidate(a)
        self.cct(a, (10,1), False, None)
        self.cct(a, (15,1), False, None)
        self.cct(b, (20,2), True, bloo)


class CanvasTest(unittest.TestCase):
    def ct(self, text, attr, exp_content):
        c = urwid.TextCanvas([B(t) for t in text], attr)
        content = list(c.content())
        assert content == exp_content, "got: %r expected: %r" % (content,
                                                                 exp_content)

    def ct2(self, text, attr, left, top, cols, rows, def_attr, exp_content):
        c = urwid.TextCanvas([B(t) for t in text], attr)
        content = list(c.content(left, top, cols, rows, def_attr))
        assert content == exp_content, "got: %r expected: %r" % (content,
                                                                 exp_content)

    def test1(self):
        self.ct(["Hello world"], None, [[(None, None, B("Hello world"))]])
        self.ct(["Hello world"], [[("a",5)]],
            [[("a", None, B("Hello")), (None, None, B(" world"))]])
        self.ct(["Hi","There"], None,
            [[(None, None, B("Hi   "))], [(None, None, B("There"))]])

    def test2(self):
        self.ct2(["Hello"], None, 0, 0, 5, 1, None,
            [[(None, None, B("Hello"))]])
        self.ct2(["Hello"], None, 1, 0, 4, 1, None,
            [[(None, None, B("ello"))]])
        self.ct2(["Hello"], None, 0, 0, 4, 1, None,
            [[(None, None, B("Hell"))]])
        self.ct2(["Hi","There"], None, 1, 0, 3, 2, None,
            [[(None, None, B("i  "))], [(None, None, B("her"))]])
        self.ct2(["Hi","There"], None, 0, 0, 5, 1, None,
            [[(None, None, B("Hi   "))]])
        self.ct2(["Hi","There"], None, 0, 1, 5, 1, None,
            [[(None, None, B("There"))]])


class ShardBodyTest(unittest.TestCase):
    def sbt(self, shards, shard_tail, expected):
        result = canvas.shard_body(shards, shard_tail, False)
        assert result == expected, "got: %r expected: %r" % (result, expected)

    def sbttail(self, num_rows, sbody, expected):
        result = canvas.shard_body_tail(num_rows, sbody)
        assert result == expected, "got: %r expected: %r" % (result, expected)

    def sbtrow(self, sbody, expected):
        result = list(canvas.shard_body_row(sbody))
        assert result == expected, "got: %r expected: %r" % (result, expected)


    def test1(self):
        cviews = [(0,0,10,5,None,"foo"),(0,0,5,5,None,"bar")]
        self.sbt(cviews, [],
            [(0, None, (0,0,10,5,None,"foo")),
            (0, None, (0,0,5,5,None,"bar"))])
        self.sbt(cviews, [(0, 3, None, (0,0,5,8,None,"baz"))],
            [(3, None, (0,0,5,8,None,"baz")),
            (0, None, (0,0,10,5,None,"foo")),
            (0, None, (0,0,5,5,None,"bar"))])
        self.sbt(cviews, [(10, 3, None, (0,0,5,8,None,"baz"))],
            [(0, None, (0,0,10,5,None,"foo")),
            (3, None, (0,0,5,8,None,"baz")),
            (0, None, (0,0,5,5,None,"bar"))])
        self.sbt(cviews, [(15, 3, None, (0,0,5,8,None,"baz"))],
            [(0, None, (0,0,10,5,None,"foo")),
            (0, None, (0,0,5,5,None,"bar")),
            (3, None, (0,0,5,8,None,"baz"))])

    def test2(self):
        sbody = [(0, None, (0,0,10,5,None,"foo")),
            (0, None, (0,0,5,5,None,"bar")),
            (3, None, (0,0,5,8,None,"baz"))]
        self.sbttail(5, sbody, [])
        self.sbttail(3, sbody,
            [(0, 3, None, (0,0,10,5,None,"foo")),
                    (0, 3, None, (0,0,5,5,None,"bar")),
            (0, 6, None, (0,0,5,8,None,"baz"))])

        sbody = [(0, None, (0,0,10,3,None,"foo")),
                        (0, None, (0,0,5,5,None,"bar")),
                        (3, None, (0,0,5,9,None,"baz"))]
        self.sbttail(3, sbody,
            [(10, 3, None, (0,0,5,5,None,"bar")),
            (0, 6, None, (0,0,5,9,None,"baz"))])

    def test3(self):
        self.sbtrow([(0, None, (0,0,10,5,None,"foo")),
            (0, None, (0,0,5,5,None,"bar")),
            (3, None, (0,0,5,8,None,"baz"))],
            [20])
        self.sbtrow([(0, iter("foo"), (0,0,10,5,None,"foo")),
            (0, iter("bar"), (0,0,5,5,None,"bar")),
            (3, iter("zzz"), (0,0,5,8,None,"baz"))],
            ["f","b","z"])


class ShardsTrimTest(unittest.TestCase):
    def sttop(self, shards, top, expected):
        result = canvas.shards_trim_top(shards, top)
        assert result == expected, "got: %r expected: %r" (result, expected)

    def strows(self, shards, rows, expected):
        result = canvas.shards_trim_rows(shards, rows)
        assert result == expected, "got: %r expected: %r" (result, expected)

    def stsides(self, shards, left, cols, expected):
        result = canvas.shards_trim_sides(shards, left, cols)
        assert result == expected, "got: %r expected: %r" (result, expected)


    def test1(self):
        shards = [(5, [(0,0,10,5,None,"foo"),(0,0,5,5,None,"bar")])]
        self.sttop(shards, 2,
            [(3, [(0,2,10,3,None,"foo"),(0,2,5,3,None,"bar")])])
        self.strows(shards, 2,
            [(2, [(0,0,10,2,None,"foo"),(0,0,5,2,None,"bar")])])

        shards = [(5, [(0,0,10,5,None,"foo")]),(3,[(0,0,10,3,None,"bar")])]
        self.sttop(shards, 2,
            [(3, [(0,2,10,3,None,"foo")]),(3,[(0,0,10,3,None,"bar")])])
        self.sttop(shards, 5,
            [(3, [(0,0,10,3,None,"bar")])])
        self.sttop(shards, 7,
            [(1, [(0,2,10,1,None,"bar")])])
        self.strows(shards, 7,
            [(5, [(0,0,10,5,None,"foo")]),(2, [(0,0,10,2,None,"bar")])])
        self.strows(shards, 5,
            [(5, [(0,0,10,5,None,"foo")])])
        self.strows(shards, 4,
            [(4, [(0,0,10,4,None,"foo")])])

        shards = [(5, [(0,0,10,5,None,"foo"), (0,0,5,8,None,"baz")]),
            (3,[(0,0,10,3,None,"bar")])]
        self.sttop(shards, 2,
            [(3, [(0,2,10,3,None,"foo"), (0,2,5,6,None,"baz")]),
            (3,[(0,0,10,3,None,"bar")])])
        self.sttop(shards, 5,
            [(3, [(0,0,10,3,None,"bar"), (0,5,5,3,None,"baz")])])
        self.sttop(shards, 7,
            [(1, [(0,2,10,1,None,"bar"), (0,7,5,1,None,"baz")])])
        self.strows(shards, 7,
            [(5, [(0,0,10,5,None,"foo"), (0,0,5,7,None,"baz")]),
            (2, [(0,0,10,2,None,"bar")])])
        self.strows(shards, 5,
            [(5, [(0,0,10,5,None,"foo"), (0,0,5,5,None,"baz")])])
        self.strows(shards, 4,
            [(4, [(0,0,10,4,None,"foo"), (0,0,5,4,None,"baz")])])


    def test2(self):
        shards = [(5, [(0,0,10,5,None,"foo"),(0,0,5,5,None,"bar")])]
        self.stsides(shards, 0, 15,
            [(5, [(0,0,10,5,None,"foo"),(0,0,5,5,None,"bar")])])
        self.stsides(shards, 6, 9,
            [(5, [(6,0,4,5,None,"foo"),(0,0,5,5,None,"bar")])])
        self.stsides(shards, 6, 6,
            [(5, [(6,0,4,5,None,"foo"),(0,0,2,5,None,"bar")])])
        self.stsides(shards, 0, 10,
            [(5, [(0,0,10,5,None,"foo")])])
        self.stsides(shards, 10, 5,
            [(5, [(0,0,5,5,None,"bar")])])
        self.stsides(shards, 1, 7,
            [(5, [(1,0,7,5,None,"foo")])])

        shards = [(5, [(0,0,10,5,None,"foo"), (0,0,5,8,None,"baz")]),
            (3,[(0,0,10,3,None,"bar")])]
        self.stsides(shards, 0, 15,
            [(5, [(0,0,10,5,None,"foo"), (0,0,5,8,None,"baz")]),
            (3,[(0,0,10,3,None,"bar")])])
        self.stsides(shards, 2, 13,
            [(5, [(2,0,8,5,None,"foo"), (0,0,5,8,None,"baz")]),
            (3,[(2,0,8,3,None,"bar")])])
        self.stsides(shards, 2, 10,
            [(5, [(2,0,8,5,None,"foo"), (0,0,2,8,None,"baz")]),
            (3,[(2,0,8,3,None,"bar")])])
        self.stsides(shards, 2, 8,
            [(5, [(2,0,8,5,None,"foo")]),
            (3,[(2,0,8,3,None,"bar")])])
        self.stsides(shards, 2, 6,
            [(5, [(2,0,6,5,None,"foo")]),
            (3,[(2,0,6,3,None,"bar")])])
        self.stsides(shards, 10, 5,
            [(8, [(0,0,5,8,None,"baz")])])
        self.stsides(shards, 11, 3,
            [(8, [(1,0,3,8,None,"baz")])])


class ShardsJoinTest(unittest.TestCase):
    def sjt(self, shard_lists, expected):
        result = canvas.shards_join(shard_lists)
        assert result == expected, "got: %r expected: %r" (result, expected)

    def test(self):
        shards1 = [(5, [(0,0,10,5,None,"foo"), (0,0,5,8,None,"baz")]),
            (3,[(0,0,10,3,None,"bar")])]
        shards2 = [(3, [(0,0,10,3,None,"aaa")]),
            (5,[(0,0,10,5,None,"bbb")])]
        shards3 = [(3, [(0,0,10,3,None,"111")]),
            (2,[(0,0,10,3,None,"222")]),
            (3,[(0,0,10,3,None,"333")])]

        self.sjt([shards1], shards1)
        self.sjt([shards1, shards2],
            [(3, [(0,0,10,5,None,"foo"), (0,0,5,8,None,"baz"),
                (0,0,10,3,None,"aaa")]),
            (2, [(0,0,10,5,None,"bbb")]),
            (3, [(0,0,10,3,None,"bar")])])
        self.sjt([shards1, shards3],
            [(3, [(0,0,10,5,None,"foo"), (0,0,5,8,None,"baz"),
                (0,0,10,3,None,"111")]),
            (2, [(0,0,10,3,None,"222")]),
            (3, [(0,0,10,3,None,"bar"), (0,0,10,3,None,"333")])])
        self.sjt([shards1, shards2, shards3],
            [(3, [(0,0,10,5,None,"foo"), (0,0,5,8,None,"baz"),
                (0,0,10,3,None,"aaa"), (0,0,10,3,None,"111")]),
            (2, [(0,0,10,5,None,"bbb"), (0,0,10,3,None,"222")]),
            (3, [(0,0,10,3,None,"bar"), (0,0,10,3,None,"333")])])


class CanvasJoinTest(unittest.TestCase):
    def cjtest(self, desc, l, expected):
        l = [(c, None, False, n) for c, n in l]
        result = list(urwid.CanvasJoin(l).content())

        assert result == expected, "%s expected %r, got %r"%(
            desc, expected, result)

    def test(self):
        C = urwid.TextCanvas
        hello = C([B("hello")])
        there = C([B("there")], [[("a",5)]])
        a = C([B("a")])
        hi = C([B("hi")])
        how = C([B("how")], [[("a",1)]])
        dy = C([B("dy")])
        how_you = C([B("how"), B("you")])

        self.cjtest("one", [(hello, 5)],
            [[(None, None, B("hello"))]])
        self.cjtest("two", [(hello, 5), (there, 5)],
            [[(None, None, B("hello")), ("a", None, B("there"))]])
        self.cjtest("two space", [(hello, 7), (there, 5)],
            [[(None, None, B("hello")),(None,None,B("  ")),
            ("a", None, B("there"))]])
        self.cjtest("three space", [(hi, 4), (how, 3), (dy, 2)],
            [[(None, None, B("hi")),(None,None,B("  ")),("a",None, B("h")),
            (None,None,B("ow")),(None,None,B("dy"))]])
        self.cjtest("four space", [(a, 2), (hi, 3), (dy, 3), (a, 1)],
            [[(None, None, B("a")),(None,None,B(" ")),
            (None, None, B("hi")),(None,None,B(" ")),
            (None, None, B("dy")),(None,None,B(" ")),
            (None, None, B("a"))]])
        self.cjtest("pile 2", [(how_you, 4), (hi, 2)],
            [[(None, None, B('how')), (None, None, B(' ')),
            (None, None, B('hi'))],
            [(None, None, B('you')), (None, None, B(' ')),
            (None, None, B('  '))]])
        self.cjtest("pile 2r", [(hi, 4), (how_you, 3)],
            [[(None, None, B('hi')), (None, None, B('  ')),
            (None, None, B('how'))],
            [(None, None, B('    ')),
            (None, None, B('you'))]])


class CanvasOverlayTest(unittest.TestCase):
    def cotest(self, desc, bgt, bga, fgt, fga, l, r, et):
        bgt = B(bgt)
        fgt = B(fgt)
        bg = urwid.CompositeCanvas(
            urwid.TextCanvas([bgt],[bga]))
        fg = urwid.CompositeCanvas(
            urwid.TextCanvas([fgt],[fga]))
        bg.overlay(fg, l, 0)
        result = list(bg.content())
        assert result == et, "%s expected %r, got %r"%(
            desc, et, result)

    def test1(self):
        self.cotest("left", "qxqxqxqx", [], "HI", [], 0, 6,
            [[(None, None, B("HI")),(None,None,B("qxqxqx"))]])
        self.cotest("right", "qxqxqxqx", [], "HI", [], 6, 0,
            [[(None, None, B("qxqxqx")),(None,None,B("HI"))]])
        self.cotest("center", "qxqxqxqx", [], "HI", [], 3, 3,
            [[(None, None, B("qxq")),(None,None,B("HI")),
            (None,None,B("xqx"))]])
        self.cotest("center2", "qxqxqxqx", [], "HI  ", [], 2, 2,
            [[(None, None, B("qx")),(None,None,B("HI  ")),
            (None,None,B("qx"))]])
        self.cotest("full", "rz", [], "HI", [], 0, 0,
            [[(None, None, B("HI"))]])

    def test2(self):
        self.cotest("same","asdfghjkl",[('a',9)],"HI",[('a',2)],4,3,
            [[('a',None,B("asdf")),('a',None,B("HI")),('a',None,B("jkl"))]])
        self.cotest("diff","asdfghjkl",[('a',9)],"HI",[('b',2)],4,3,
            [[('a',None,B("asdf")),('b',None,B("HI")),('a',None,B("jkl"))]])
        self.cotest("None end","asdfghjkl",[('a',9)],"HI  ",[('a',2)],
            2,3,
            [[('a',None,B("as")),('a',None,B("HI")),
            (None,None,B("  ")),('a',None,B("jkl"))]])
        self.cotest("float end","asdfghjkl",[('a',3)],"HI",[('a',2)],
            4,3,
            [[('a',None,B("asd")),(None,None,B("f")),
            ('a',None,B("HI")),(None,None,B("jkl"))]])
        self.cotest("cover 2","asdfghjkl",[('a',5),('c',4)],"HI",
            [('b',2)],4,3,
            [[('a',None,B("asdf")),('b',None,B("HI")),('c',None,B("jkl"))]])
        self.cotest("cover 2-2","asdfghjkl",
            [('a',4),('d',1),('e',1),('c',3)],
            "HI",[('b',2)], 4, 3,
            [[('a',None,B("asdf")),('b',None,B("HI")),('c',None,B("jkl"))]])

    def test3(self):
        urwid.set_encoding("euc-jp")
        self.cotest("db0","\xA1\xA1\xA1\xA1\xA1\xA1",[],"HI",[],2,2,
            [[(None,None,B("\xA1\xA1")),(None,None,B("HI")),
            (None,None,B("\xA1\xA1"))]])
        self.cotest("db1","\xA1\xA1\xA1\xA1\xA1\xA1",[],"OHI",[],1,2,
            [[(None,None,B(" ")),(None,None,B("OHI")),
            (None,None,B("\xA1\xA1"))]])
        self.cotest("db2","\xA1\xA1\xA1\xA1\xA1\xA1",[],"OHI",[],2,1,
            [[(None,None,B("\xA1\xA1")),(None,None,B("OHI")),
            (None,None,B(" "))]])
        self.cotest("db3","\xA1\xA1\xA1\xA1\xA1\xA1",[],"OHIO",[],1,1,
            [[(None,None,B(" ")),(None,None,B("OHIO")),(None,None,B(" "))]])


class CanvasPadTrimTest(unittest.TestCase):
    def cptest(self, desc, ct, ca, l, r, et):
        ct = B(ct)
        c = urwid.CompositeCanvas(
            urwid.TextCanvas([ct], [ca]))
        c.pad_trim_left_right(l, r)
        result = list(c.content())
        assert result == et, "%s expected %r, got %r"%(
            desc, et, result)

    def test1(self):
        self.cptest("none", "asdf", [], 0, 0,
            [[(None,None,B("asdf"))]])
        self.cptest("left pad", "asdf", [], 2, 0,
            [[(None,None,B("  ")),(None,None,B("asdf"))]])
        self.cptest("right pad", "asdf", [], 0, 2,
            [[(None,None,B("asdf")),(None,None,B("  "))]])

    def test2(self):
        self.cptest("left trim", "asdf", [], -2, 0,
            [[(None,None,B("df"))]])
        self.cptest("right trim", "asdf", [], 0, -2,
            [[(None,None,B("as"))]])
