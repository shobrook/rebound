# -*- coding: utf-8 -*-
import unittest

from urwid.compat import B
import urwid


class TextTest(unittest.TestCase):
    def setUp(self):
        self.t = urwid.Text("I walk the\ncity in the night")

    def test1_wrap(self):
        expected = [B(t) for t in ("I walk the","city in   ","the night ")]
        got = self.t.render((10,))._text
        assert got == expected, "got: %r expected: %r" % (got, expected)

    def test2_left(self):
        self.t.set_align_mode('left')
        expected = [B(t) for t in ("I walk the        ","city in the night ")]
        got = self.t.render((18,))._text
        assert got == expected, "got: %r expected: %r" % (got, expected)

    def test3_right(self):
        self.t.set_align_mode('right')
        expected = [B(t) for t in ("        I walk the"," city in the night")]
        got = self.t.render((18,))._text
        assert got == expected, "got: %r expected: %r" % (got, expected)

    def test4_center(self):
        self.t.set_align_mode('center')
        expected = [B(t) for t in ("    I walk the    "," city in the night")]
        got = self.t.render((18,))._text
        assert got == expected, "got: %r expected: %r" % (got, expected)

    def test5_encode_error(self):
        urwid.set_encoding("ascii")
        expected = [B("?  ")]
        got = urwid.Text(u'û').render((3,))._text
        assert got == expected, "got: %r expected: %r" % (got, expected)


class EditTest(unittest.TestCase):
    def setUp(self):
        self.t1 = urwid.Edit(B(""),"blah blah")
        self.t2 = urwid.Edit(B("stuff:"), "blah blah")
        self.t3 = urwid.Edit(B("junk:\n"),"blah blah\n\nbloo",1)
        self.t4 = urwid.Edit(u"better:")

    def ktest(self, e, key, expected, pos, desc):
        got= e.keypress((12,),key)
        assert got == expected, "%s.  got: %r expected:%r" % (desc, got,
                                                              expected)
        assert e.edit_pos == pos, "%s. pos: %r expected pos: %r" % (
            desc, e.edit_pos, pos)

    def test1_left(self):
        self.t1.set_edit_pos(0)
        self.ktest(self.t1,'left','left',0,"left at left edge")

        self.ktest(self.t2,'left',None,8,"left within text")

        self.t3.set_edit_pos(10)
        self.ktest(self.t3,'left',None,9,"left after newline")

    def test2_right(self):
        self.ktest(self.t1,'right','right',9,"right at right edge")

        self.t2.set_edit_pos(8)
        self.ktest(self.t2,'right',None,9,"right at right edge-1")
        self.t3.set_edit_pos(0)
        self.t3.keypress((12,),'right')
        assert self.t3.get_pref_col((12,)) == 1

    def test3_up(self):
        self.ktest(self.t1,'up','up',9,"up at top")
        self.t2.set_edit_pos(2)
        self.t2.keypress((12,),"left")
        assert self.t2.get_pref_col((12,)) == 7
        self.ktest(self.t2,'up','up',1,"up at top again")
        assert self.t2.get_pref_col((12,)) == 7
        self.t3.set_edit_pos(10)
        self.ktest(self.t3,'up',None,0,"up at top+1")

    def test4_down(self):
        self.ktest(self.t1,'down','down',9,"down single line")
        self.t3.set_edit_pos(5)
        self.ktest(self.t3,'down',None,10,"down line 1 to 2")
        self.ktest(self.t3,'down',None,15,"down line 2 to 3")
        self.ktest(self.t3,'down','down',15,"down at bottom")

    def test_utf8_input(self):
        urwid.set_encoding("utf-8")
        self.t1.set_edit_text('')
        self.t1.keypress((12,), u'û')
        self.assertEqual(self.t1.edit_text, u'û'.encode('utf-8'))
        self.t4.keypress((12,), u'û')
        self.assertEqual(self.t4.edit_text, u'û')


class EditRenderTest(unittest.TestCase):
    def rtest(self, w, expected_text, expected_cursor):
        expected_text = [B(t) for t in expected_text]
        get_cursor = w.get_cursor_coords((4,))
        assert get_cursor == expected_cursor, "got: %r expected: %r" % (
            get_cursor, expected_cursor)
        r = w.render((4,), focus = 1)
        text = [t for a, cs, t in [ln[0] for ln in r.content()]]
        assert text == expected_text, "got: %r expected: %r" % (text,
                                                                expected_text)
        assert r.cursor == expected_cursor, "got: %r expected: %r" % (
            r.cursor, expected_cursor)

    def test1_SpaceWrap(self):
        w = urwid.Edit("","blah blah")
        w.set_edit_pos(0)
        self.rtest(w,["blah","blah"],(0,0))

        w.set_edit_pos(4)
        self.rtest(w,["lah ","blah"],(3,0))

        w.set_edit_pos(5)
        self.rtest(w,["blah","blah"],(0,1))

        w.set_edit_pos(9)
        self.rtest(w,["blah","lah "],(3,1))

    def test2_ClipWrap(self):
        w = urwid.Edit("","blah\nblargh",1)
        w.set_wrap_mode('clip')
        w.set_edit_pos(0)
        self.rtest(w,["blah","blar"],(0,0))

        w.set_edit_pos(10)
        self.rtest(w,["blah","argh"],(3,1))

        w.set_align_mode('right')
        w.set_edit_pos(6)
        self.rtest(w,["blah","larg"],(0,1))

    def test3_AnyWrap(self):
        w = urwid.Edit("","blah blah")
        w.set_wrap_mode('any')

        self.rtest(w,["blah"," bla","h   "],(1,2))

    def test4_CursorNudge(self):
        w = urwid.Edit("","hi",align='right')
        w.keypress((4,),'end')

        self.rtest(w,[" hi "],(3,0))

        w.keypress((4,),'left')
        self.rtest(w,["  hi"],(3,0))
