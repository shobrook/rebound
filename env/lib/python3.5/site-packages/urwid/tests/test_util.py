# -*- coding: utf-8 -*-
import unittest

import urwid
from urwid import util
from urwid.compat import B


class CalcWidthTest(unittest.TestCase):
    def wtest(self, desc, s, exp):
        s = B(s)
        result = util.calc_width( s, 0, len(s))
        assert result==exp, "%s got:%r expected:%r" % (desc, result, exp)

    def test1(self):
        util.set_encoding("utf-8")
        self.wtest("narrow", "hello", 5)
        self.wtest("wide char", '\xe6\x9b\xbf', 2)
        self.wtest("invalid", '\xe6', 1)
        self.wtest("zero width", '\xcc\x80', 0)
        self.wtest("mixed", 'hello\xe6\x9b\xbf\xe6\x9b\xbf', 9)

    def test2(self):
        util.set_encoding("euc-jp")
        self.wtest("narrow", "hello", 5)
        self.wtest("wide", "\xA1\xA1\xA1\xA1", 4)
        self.wtest("invalid", "\xA1", 1)


class ConvertDecSpecialTest(unittest.TestCase):
    def ctest(self, desc, s, exp, expcs):
        exp = B(exp)
        util.set_encoding('ascii')
        c = urwid.Text(s).render((5,))
        result = c._text[0]
        assert result==exp, "%s got:%r expected:%r" % (desc, result, exp)
        resultcs = c._cs[0]
        assert resultcs==expcs, "%s got:%r expected:%r" % (desc,
                                                           resultcs, expcs)

    def test1(self):
        self.ctest("no conversion", u"hello", "hello", [(None,5)])
        self.ctest("only special", u"£££££", "}}}}}", [("0",5)])
        self.ctest("mix left", u"££abc", "}}abc", [("0",2),(None,3)])
        self.ctest("mix right", u"abc££", "abc}}", [(None,3),("0",2)])
        self.ctest("mix inner", u"a££bc", "a}}bc",
            [(None,1),("0",2),(None,2)] )
        self.ctest("mix well", u"£a£b£", "}a}b}",
            [("0",1),(None,1),("0",1),(None,1),("0",1)] )


class WithinDoubleByteTest(unittest.TestCase):
    def setUp(self):
        urwid.set_encoding("euc-jp")

    def wtest(self, s, ls, pos, expected, desc):
        result = util.within_double_byte(B(s), ls, pos)
        assert result==expected, "%s got:%r expected: %r" % (desc,
                                                             result, expected)
    def test1(self):
        self.wtest("mnopqr",0,2,0,'simple no high bytes')
        self.wtest("mn\xA1\xA1qr",0,2,1,'simple 1st half')
        self.wtest("mn\xA1\xA1qr",0,3,2,'simple 2nd half')
        self.wtest("m\xA1\xA1\xA1\xA1r",0,3,1,'subsequent 1st half')
        self.wtest("m\xA1\xA1\xA1\xA1r",0,4,2,'subsequent 2nd half')
        self.wtest("mn\xA1@qr",0,3,2,'simple 2nd half lo')
        self.wtest("mn\xA1\xA1@r",0,4,0,'subsequent not 2nd half lo')
        self.wtest("m\xA1\xA1\xA1@r",0,4,2,'subsequent 2nd half lo')

    def test2(self):
        self.wtest("\xA1\xA1qr",0,0,1,'begin 1st half')
        self.wtest("\xA1\xA1qr",0,1,2,'begin 2nd half')
        self.wtest("\xA1@qr",0,1,2,'begin 2nd half lo')
        self.wtest("\xA1\xA1\xA1\xA1r",0,2,1,'begin subs. 1st half')
        self.wtest("\xA1\xA1\xA1\xA1r",0,3,2,'begin subs. 2nd half')
        self.wtest("\xA1\xA1\xA1@r",0,3,2,'begin subs. 2nd half lo')
        self.wtest("\xA1@\xA1@r",0,3,2,'begin subs. 2nd half lo lo')
        self.wtest("@\xA1\xA1@r",0,3,0,'begin subs. not 2nd half lo')

    def test3(self):
        self.wtest("abc \xA1\xA1qr",4,4,1,'newline 1st half')
        self.wtest("abc \xA1\xA1qr",4,5,2,'newline 2nd half')
        self.wtest("abc \xA1@qr",4,5,2,'newline 2nd half lo')
        self.wtest("abc \xA1\xA1\xA1\xA1r",4,6,1,'newl subs. 1st half')
        self.wtest("abc \xA1\xA1\xA1\xA1r",4,7,2,'newl subs. 2nd half')
        self.wtest("abc \xA1\xA1\xA1@r",4,7,2,'newl subs. 2nd half lo')
        self.wtest("abc \xA1@\xA1@r",4,7,2,'newl subs. 2nd half lo lo')
        self.wtest("abc @\xA1\xA1@r",4,7,0,'newl subs. not 2nd half lo')


class CalcTextPosTest(unittest.TestCase):
    def ctptest(self, text, tests):
        text = B(text)
        for s,e,p, expected in tests:
            got = util.calc_text_pos( text, s, e, p )
            assert got == expected, "%r got:%r expected:%r" % ((s,e,p),
                                                               got, expected)

    def test1(self):
        text = "hello world out there"
        tests = [
            (0,21,0, (0,0)),
            (0,21,5, (5,5)),
            (0,21,21, (21,21)),
            (0,21,50, (21,21)),
            (2,15,50, (15,13)),
            (6,21,0, (6,0)),
            (6,21,3, (9,3)),
            ]
        self.ctptest(text, tests)

    def test2_wide(self):
        util.set_encoding("euc-jp")
        text = "hel\xA1\xA1 world out there"
        tests = [
            (0,21,0, (0,0)),
            (0,21,4, (3,3)),
            (2,21,2, (3,1)),
            (2,21,3, (5,3)),
            (6,21,0, (6,0)),
            ]
        self.ctptest(text, tests)

    def test3_utf8(self):
        util.set_encoding("utf-8")
        text = "hel\xc4\x83 world \xe2\x81\x81 there"
        tests = [
            (0,21,0, (0,0)),
            (0,21,4, (5,4)),
            (2,21,1, (3,1)),
            (2,21,2, (5,2)),
            (2,21,3, (6,3)),
            (6,21,7, (15,7)),
            (6,21,8, (16,8)),
            ]
        self.ctptest(text, tests)

    def test4_utf8(self):
        util.set_encoding("utf-8")
        text = "he\xcc\x80llo \xe6\x9b\xbf world"
        tests = [
            (0,15,0, (0,0)),
            (0,15,1, (1,1)),
            (0,15,2, (4,2)),
            (0,15,4, (6,4)),
            (8,15,0, (8,0)),
            (8,15,1, (8,0)),
            (8,15,2, (11,2)),
            (8,15,5, (14,5)),
            ]
        self.ctptest(text, tests)


class TagMarkupTest(unittest.TestCase):
    mytests = [
        ("simple one", "simple one", []),
        (('blue',"john"), "john", [('blue',4)]),
        (["a ","litt","le list"], "a little list", []),
        (["mix",('high',[" it ",('ital',"up a")])," little"],
            "mix it up a little",
            [(None,3),('high',4),('ital',4)]),
        ([u"££", u"x££"], u"££x££", []),
        ([B("\xc2\x80"), B("\xc2\x80")], B("\xc2\x80\xc2\x80"), []),
        ]

    def test(self):
        for input, text, attr in self.mytests:
            restext,resattr = urwid.decompose_tagmarkup( input )
            assert restext == text, "got: %r expected: %r" % (restext, text)
            assert resattr == attr, "got: %r expected: %r" % (resattr, attr)

    def test_bad_tuple(self):
        self.assertRaises(urwid.TagMarkupException, lambda:
            urwid.decompose_tagmarkup((1,2,3)))

    def test_bad_type(self):
        self.assertRaises(urwid.TagMarkupException, lambda:
            urwid.decompose_tagmarkup(5))
