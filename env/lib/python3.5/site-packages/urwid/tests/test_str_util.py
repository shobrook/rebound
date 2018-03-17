import unittest

from urwid.compat import B
from urwid.escape import str_util


class DecodeOneTest(unittest.TestCase):
    def gwt(self, ch, exp_ord, exp_pos):
        ch = B(ch)
        o, pos = str_util.decode_one(ch,0)
        assert o==exp_ord, " got:%r expected:%r" % (o, exp_ord)
        assert pos==exp_pos, " got:%r expected:%r" % (pos, exp_pos)

    def test1byte(self):
        self.gwt("ab", ord("a"), 1)
        self.gwt("\xc0a", ord("?"), 1) # error

    def test2byte(self):
        self.gwt("\xc2", ord("?"), 1) # error
        self.gwt("\xc0\x80", ord("?"), 1) # error
        self.gwt("\xc2\x80", 0x80, 2)
        self.gwt("\xdf\xbf", 0x7ff, 2)

    def test3byte(self):
        self.gwt("\xe0", ord("?"), 1) # error
        self.gwt("\xe0\xa0", ord("?"), 1) # error
        self.gwt("\xe0\x90\x80", ord("?"), 1) # error
        self.gwt("\xe0\xa0\x80", 0x800, 3)
        self.gwt("\xef\xbf\xbf", 0xffff, 3)

    def test4byte(self):
        self.gwt("\xf0", ord("?"), 1) # error
        self.gwt("\xf0\x90", ord("?"), 1) # error
        self.gwt("\xf0\x90\x80", ord("?"), 1) # error
        self.gwt("\xf0\x80\x80\x80", ord("?"), 1) # error
        self.gwt("\xf0\x90\x80\x80", 0x10000, 4)
        self.gwt("\xf3\xbf\xbf\xbf", 0xfffff, 4)
