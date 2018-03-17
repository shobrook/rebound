import unittest

from urwid.compat import B
from urwid.tests.util import SelectableText
import urwid


class ListBoxCalculateVisibleTest(unittest.TestCase):
    def cvtest(self, desc, body, focus, offset_rows, inset_fraction,
        exp_offset_inset, exp_cur ):

        lbox = urwid.ListBox(body)
        lbox.body.set_focus( focus )
        lbox.offset_rows = offset_rows
        lbox.inset_fraction = inset_fraction

        middle, top, bottom = lbox.calculate_visible((4,5),focus=1)
        offset_inset, focus_widget, focus_pos, _ign, cursor = middle

        if cursor is not None:
            x, y = cursor
            y += offset_inset
            cursor = x, y

        assert offset_inset == exp_offset_inset, "%s got: %r expected: %r" %(desc,offset_inset,exp_offset_inset)
        assert cursor == exp_cur, "%s (cursor) got: %r expected: %r" %(desc,cursor,exp_cur)

    def test1_simple(self):
        T = urwid.Text

        l = [T(""),T(""),T("\n"),T("\n\n"),T("\n"),T(""),T("")]

        self.cvtest( "simple top position",
            l, 3, 0, (0,1), 0, None )

        self.cvtest( "simple middle position",
            l, 3, 1, (0,1), 1, None )

        self.cvtest( "simple bottom position",
            l, 3, 2, (0,1), 2, None )

        self.cvtest( "straddle top edge",
            l, 3, 0, (1,2), -1, None )

        self.cvtest( "straddle bottom edge",
            l, 3, 4, (0,1), 4, None )

        self.cvtest( "off bottom edge",
            l, 3, 5, (0,1), 4, None )

        self.cvtest( "way off bottom edge",
            l, 3, 100, (0,1), 4, None )

        self.cvtest( "gap at top",
            l, 0, 2, (0,1), 0, None )

        self.cvtest( "gap at top and off bottom edge",
            l, 2, 5, (0,1), 2, None )

        self.cvtest( "gap at bottom",
            l, 6, 1, (0,1), 4, None )

        self.cvtest( "gap at bottom and straddling top edge",
            l, 4, 0, (1,2), 1, None )

        self.cvtest( "gap at bottom cannot completely fill",
            [T(""),T(""),T("")], 1, 0, (0,1), 1, None )

        self.cvtest( "gap at top and bottom",
            [T(""),T(""),T("")], 1, 2, (0,1), 1, None )


    def test2_cursor(self):
        T, E = urwid.Text, urwid.Edit

        l1 = [T(""),T(""),T("\n"),E("","\n\nX"),T("\n"),T(""),T("")]
        l2 = [T(""),T(""),T("\n"),E("","YY\n\n"),T("\n"),T(""),T("")]

        l2[3].set_edit_pos(2)

        self.cvtest( "plain cursor in view",
            l1, 3, 1, (0,1), 1, (1,3) )

        self.cvtest( "cursor off top",
            l2, 3, 0, (1,3), 0, (2, 0) )

        self.cvtest( "cursor further off top",
            l2, 3, 0, (2,3), 0, (2, 0) )

        self.cvtest( "cursor off bottom",
            l1, 3, 3, (0,1), 2, (1, 4) )

        self.cvtest( "cursor way off bottom",
            l1, 3, 100, (0,1), 2, (1, 4) )


class ListBoxChangeFocusTest(unittest.TestCase):
    def cftest(self, desc, body, pos, offset_inset,
            coming_from, cursor, snap_rows,
            exp_offset_rows, exp_inset_fraction, exp_cur ):

        lbox = urwid.ListBox(body)

        lbox.change_focus( (4,5), pos, offset_inset, coming_from,
            cursor, snap_rows )

        exp = exp_offset_rows, exp_inset_fraction
        act = lbox.offset_rows, lbox.inset_fraction

        cursor = None
        focus_widget, focus_pos = lbox.body.get_focus()
        if focus_widget.selectable():
            if hasattr(focus_widget,'get_cursor_coords'):
                cursor=focus_widget.get_cursor_coords((4,))

        assert act == exp, "%s got: %s expected: %s" %(desc, act, exp)
        assert cursor == exp_cur, "%s (cursor) got: %r expected: %r" %(desc,cursor,exp_cur)


    def test1unselectable(self):
        T = urwid.Text
        l = [T("\n"),T("\n\n"),T("\n\n"),T("\n\n"),T("\n")]

        self.cftest( "simple unselectable",
            l, 2, 0, None, None, None, 0, (0,1), None )

        self.cftest( "unselectable",
            l, 2, 1, None, None, None, 1, (0,1), None )

        self.cftest( "unselectable off top",
            l, 2, -2, None, None, None, 0, (2,3), None )

        self.cftest( "unselectable off bottom",
            l, 3, 2, None, None, None, 2, (0,1), None )

    def test2selectable(self):
        T, S = urwid.Text, SelectableText
        l = [T("\n"),T("\n\n"),S("\n\n"),T("\n\n"),T("\n")]

        self.cftest( "simple selectable",
            l, 2, 0, None, None, None, 0, (0,1), None )

        self.cftest( "selectable",
            l, 2, 1, None, None, None, 1, (0,1), None )

        self.cftest( "selectable at top",
            l, 2, 0, 'below', None, None, 0, (0,1), None )

        self.cftest( "selectable at bottom",
            l, 2, 2, 'above', None, None, 2, (0,1), None )

        self.cftest( "selectable off top snap",
            l, 2, -1, 'below', None, None, 0, (0,1), None )

        self.cftest( "selectable off bottom snap",
            l, 2, 3, 'above', None, None, 2, (0,1), None )

        self.cftest( "selectable off top no snap",
            l, 2, -1, 'above', None, None, 0, (1,3), None )

        self.cftest( "selectable off bottom no snap",
            l, 2, 3, 'below', None, None, 3, (0,1), None )

    def test3large_selectable(self):
        T, S = urwid.Text, SelectableText
        l = [T("\n"),S("\n\n\n\n\n\n"),T("\n")]
        self.cftest( "large selectable no snap",
            l, 1, -1, None, None, None, 0, (1,7), None )

        self.cftest( "large selectable snap up",
            l, 1, -2, 'below', None, None, 0, (0,1), None )

        self.cftest( "large selectable snap up2",
            l, 1, -2, 'below', None, 2, 0, (0,1), None )

        self.cftest( "large selectable almost snap up",
            l, 1, -2, 'below', None, 1, 0, (2,7), None )

        self.cftest( "large selectable snap down",
            l, 1, 0, 'above', None, None, 0, (2,7), None )

        self.cftest( "large selectable snap down2",
            l, 1, 0, 'above', None, 2, 0, (2,7), None )

        self.cftest( "large selectable almost snap down",
            l, 1, 0, 'above', None, 1, 0, (0,1), None )

        m = [T("\n\n\n\n"), S("\n\n\n\n\n"), T("\n\n\n\n")]
        self.cftest( "large selectable outside view down",
            m, 1, 4, 'above', None, None, 0, (0,1), None )

        self.cftest( "large selectable outside view up",
            m, 1, -5, 'below', None, None, 0, (1,6), None )

    def test4cursor(self):
        T,E = urwid.Text, urwid.Edit
        #...

    def test5set_focus_valign(self):
        T,E = urwid.Text, urwid.Edit
        lbox = urwid.ListBox(urwid.SimpleFocusListWalker([
            T(''), T('')]))
        lbox.set_focus_valign('middle')
        # TODO: actually test the result


class ListBoxRenderTest(unittest.TestCase):
    def ltest(self,desc,body,focus,offset_inset_rows,exp_text,exp_cur):
        exp_text = [B(t) for t in exp_text]
        lbox = urwid.ListBox(body)
        lbox.body.set_focus( focus )
        lbox.shift_focus((4,10), offset_inset_rows )
        canvas = lbox.render( (4,5), focus=1 )

        text = [bytes().join([t for at, cs, t in ln]) for ln in canvas.content()]

        cursor = canvas.cursor

        assert text == exp_text, "%s (text) got: %r expected: %r" %(desc,text,exp_text)
        assert cursor == exp_cur, "%s (cursor) got: %r expected: %r" %(desc,cursor,exp_cur)


    def test1_simple(self):
        T = urwid.Text

        self.ltest( "simple one text item render",
            [T("1\n2")], 0, 0,
            ["1   ","2   ","    ","    ","    "],None)

        self.ltest( "simple multi text item render off bottom",
            [T("1"),T("2"),T("3\n4"),T("5"),T("6")], 2, 2,
            ["1   ","2   ","3   ","4   ","5   "],None)

        self.ltest( "simple multi text item render off top",
            [T("1"),T("2"),T("3\n4"),T("5"),T("6")], 2, 1,
            ["2   ","3   ","4   ","5   ","6   "],None)

    def test2_trim(self):
        T = urwid.Text

        self.ltest( "trim unfocused bottom",
            [T("1\n2"),T("3\n4"),T("5\n6")], 1, 2,
            ["1   ","2   ","3   ","4   ","5   "],None)

        self.ltest( "trim unfocused top",
            [T("1\n2"),T("3\n4"),T("5\n6")], 1, 1,
            ["2   ","3   ","4   ","5   ","6   "],None)

        self.ltest( "trim none full focus",
            [T("1\n2\n3\n4\n5")], 0, 0,
            ["1   ","2   ","3   ","4   ","5   "],None)

        self.ltest( "trim focus bottom",
            [T("1\n2\n3\n4\n5\n6")], 0, 0,
            ["1   ","2   ","3   ","4   ","5   "],None)

        self.ltest( "trim focus top",
            [T("1\n2\n3\n4\n5\n6")], 0, -1,
            ["2   ","3   ","4   ","5   ","6   "],None)

        self.ltest( "trim focus top and bottom",
            [T("1\n2\n3\n4\n5\n6\n7")], 0, -1,
            ["2   ","3   ","4   ","5   ","6   "],None)

    def test3_shift(self):
        T,E = urwid.Text, urwid.Edit

        self.ltest( "shift up one fit",
            [T("1\n2"),T("3"),T("4"),T("5"),T("6")], 4, 5,
            ["2   ","3   ","4   ","5   ","6   "],None)

        e = E("","ab\nc",1)
        e.set_edit_pos( 2 )
        self.ltest( "shift down one cursor over edge",
            [e,T("3"),T("4"),T("5\n6")], 0, -1,
            ["ab  ","c   ","3   ","4   ","5   "], (2,0))

        self.ltest( "shift up one cursor over edge",
            [T("1\n2"),T("3"),T("4"),E("","d\ne")], 3, 4,
            ["2   ","3   ","4   ","d   ","e   "], (1,4))

        self.ltest( "shift none cursor top focus over edge",
            [E("","ab\n"),T("3"),T("4"),T("5\n6")], 0, -1,
            ["    ","3   ","4   ","5   ","6   "], (0,0))

        e = E("","abc\nd")
        e.set_edit_pos( 3 )
        self.ltest( "shift none cursor bottom focus over edge",
            [T("1\n2"),T("3"),T("4"),e], 3, 4,
            ["1   ","2   ","3   ","4   ","abc "], (3,4))

    def test4_really_large_contents(self):
        T,E = urwid.Text, urwid.Edit
        self.ltest("really large edit",
            [T(u"hello"*100)], 0, 0,
            ["hell","ohel","lohe","lloh","ello"], None)

        self.ltest("really large edit",
            [E(u"", u"hello"*100)], 0, 0,
            ["hell","ohel","lohe","lloh","llo "], (3,4))


class ListBoxKeypressTest(unittest.TestCase):
    def ktest(self, desc, key, body, focus, offset_inset,
        exp_focus, exp_offset_inset, exp_cur, lbox = None):

        if lbox is None:
            lbox = urwid.ListBox(body)
            lbox.body.set_focus( focus )
            lbox.shift_focus((4,10), offset_inset )

        ret_key = lbox.keypress((4,5),key)
        middle, top, bottom = lbox.calculate_visible((4,5),focus=1)
        offset_inset, focus_widget, focus_pos, _ign, cursor = middle

        if cursor is not None:
            x, y = cursor
            y += offset_inset
            cursor = x, y

        exp = exp_focus, exp_offset_inset
        act = focus_pos, offset_inset
        assert act == exp, "%s got: %r expected: %r" %(desc,act,exp)
        assert cursor == exp_cur, "%s (cursor) got: %r expected: %r" %(desc,cursor,exp_cur)
        return ret_key,lbox


    def test1_up(self):
        T,S,E = urwid.Text, SelectableText, urwid.Edit

        self.ktest( "direct selectable both visible", 'up',
            [S(""),S("")], 1, 1,
            0, 0, None )

        self.ktest( "selectable skip one all visible", 'up',
            [S(""),T(""),S("")], 2, 2,
            0, 0, None )

        key,lbox = self.ktest( "nothing above no scroll", 'up',
            [S("")], 0, 0,
            0, 0, None )
        assert key == 'up'

        key, lbox = self.ktest( "unselectable above no scroll", 'up',
            [T(""),T(""),S("")], 2, 2,
            2, 2, None )
        assert key == 'up'

        self.ktest( "unselectable above scroll 1", 'up',
            [T(""),S(""),T("\n\n\n")], 1, 0,
            1, 1, None )

        self.ktest( "selectable above scroll 1", 'up',
            [S(""),S(""),T("\n\n\n")], 1, 0,
            0, 0, None )

        self.ktest( "selectable above too far", 'up',
            [S(""),T(""),S(""),T("\n\n\n")], 2, 0,
            2, 1, None )

        self.ktest( "selectable above skip 1 scroll 1", 'up',
            [S(""),T(""),S(""),T("\n\n\n")], 2, 1,
            0, 0, None )

        self.ktest( "tall selectable above scroll 2", 'up',
            [S(""),S("\n"),S(""),T("\n\n\n")], 2, 0,
            1, 0, None )

        self.ktest( "very tall selectable above scroll 5", 'up',
            [S(""),S("\n\n\n\n"),S(""),T("\n\n\n\n")], 2, 0,
            1, 0, None )

        self.ktest( "very tall selected scroll within 1", 'up',
            [S(""),S("\n\n\n\n\n")], 1, -1,
            1, 0, None )

        self.ktest( "edit above pass cursor", 'up',
            [E("","abc"),E("","de")], 1, 1,
            0, 0, (2, 0) )

        key,lbox = self.ktest( "edit too far above pass cursor A", 'up',
            [E("","abc"),T("\n\n\n\n"),E("","de")], 2, 4,
            1, 0, None )

        self.ktest( "edit too far above pass cursor B", 'up',
            None, None, None,
            0, 0, (2,0), lbox )

        self.ktest( "within focus cursor made not visible", 'up',
            [T("\n\n\n"),E("hi\n","ab")], 1, 3,
            0, 0, None )

        self.ktest( "within focus cursor made not visible (2)", 'up',
            [T("\n\n\n\n"),E("hi\n","ab")], 1, 3,
            0, -1, None )

        self.ktest( "force focus unselectable" , 'up',
            [T("\n\n\n\n"),S("")], 1, 4,
            0, 0, None )

        self.ktest( "pathological cursor widget", 'up',
            [T("\n"),E("\n\n\n\n\n","a")], 1, 4,
            0, -1, None )

        self.ktest( "unselectable to unselectable", 'up',
            [T(""),T(""),T(""),T(""),T(""),T(""),T("")], 2, 0,
            1, 0, None )

        self.ktest( "unselectable over edge to same", 'up',
            [T(""),T("12\n34"),T(""),T(""),T(""),T("")],1,-1,
            1, 0, None )

        key,lbox = self.ktest( "edit short between pass cursor A", 'up',
            [E("","abcd"),E("","a"),E("","def")], 2, 2,
            1, 1, (1,1) )

        self.ktest( "edit short between pass cursor B", 'up',
            None, None, None,
            0, 0, (3,0), lbox )

        e = E("","\n\n\n\n\n")
        e.set_edit_pos(1)
        key,lbox = self.ktest( "edit cursor force scroll", 'up',
            [e], 0, -1,
            0, 0, (0,0) )
        assert lbox.inset_fraction[0] == 0

    def test2_down(self):
        T,S,E = urwid.Text, SelectableText, urwid.Edit

        self.ktest( "direct selectable both visible", 'down',
            [S(""),S("")], 0, 0,
            1, 1, None )

        self.ktest( "selectable skip one all visible", 'down',
            [S(""),T(""),S("")], 0, 0,
            2, 2, None )

        key,lbox = self.ktest( "nothing below no scroll", 'down',
            [S("")], 0, 0,
            0, 0, None )
        assert key == 'down'

        key, lbox = self.ktest( "unselectable below no scroll", 'down',
            [S(""),T(""),T("")], 0, 0,
            0, 0, None )
        assert key == 'down'

        self.ktest( "unselectable below scroll 1", 'down',
            [T("\n\n\n"),S(""),T("")], 1, 4,
            1, 3, None )

        self.ktest( "selectable below scroll 1", 'down',
            [T("\n\n\n"),S(""),S("")], 1, 4,
            2, 4, None )

        self.ktest( "selectable below too far", 'down',
            [T("\n\n\n"),S(""),T(""),S("")], 1, 4,
            1, 3, None )

        self.ktest( "selectable below skip 1 scroll 1", 'down',
            [T("\n\n\n"),S(""),T(""),S("")], 1, 3,
            3, 4, None )

        self.ktest( "tall selectable below scroll 2", 'down',
            [T("\n\n\n"),S(""),S("\n"),S("")], 1, 4,
            2, 3, None )

        self.ktest( "very tall selectable below scroll 5", 'down',
            [T("\n\n\n\n"),S(""),S("\n\n\n\n"),S("")], 1, 4,
            2, 0, None )

        self.ktest( "very tall selected scroll within 1", 'down',
            [S("\n\n\n\n\n"),S("")], 0, 0,
            0, -1, None )

        self.ktest( "edit below pass cursor", 'down',
            [E("","de"),E("","abc")], 0, 0,
            1, 1, (2, 1) )

        key,lbox=self.ktest( "edit too far below pass cursor A", 'down',
            [E("","de"),T("\n\n\n\n"),E("","abc")], 0, 0,
            1, 0, None )

        self.ktest( "edit too far below pass cursor B", 'down',
            None, None, None,
            2, 4, (2,4), lbox )

        odd_e = E("","hi\nab")
        odd_e.set_edit_pos( 2 )
        # disble cursor movement in odd_e object
        odd_e.move_cursor_to_coords = lambda s,c,xy: 0
        self.ktest( "within focus cursor made not visible", 'down',
            [odd_e,T("\n\n\n\n")], 0, 0,
            1, 1, None )

        self.ktest( "within focus cursor made not visible (2)", 'down',
            [odd_e,T("\n\n\n\n"),], 0, 0,
            1, 1, None )

        self.ktest( "force focus unselectable" , 'down',
            [S(""),T("\n\n\n\n")], 0, 0,
            1, 0, None )

        odd_e.set_edit_text( "hi\n\n\n\n\n" )
        self.ktest( "pathological cursor widget", 'down',
            [odd_e,T("\n")], 0, 0,
            1, 4, None )

        self.ktest( "unselectable to unselectable", 'down',
            [T(""),T(""),T(""),T(""),T(""),T(""),T("")], 4, 4,
            5, 4, None )

        self.ktest( "unselectable over edge to same", 'down',
            [T(""),T(""),T(""),T(""),T("12\n34"),T("")],4,4,
            4, 3, None )

        key,lbox=self.ktest( "edit short between pass cursor A", 'down',
            [E("","abc"),E("","a"),E("","defg")], 0, 0,
            1, 1, (1,1) )

        self.ktest( "edit short between pass cursor B", 'down',
            None, None, None,
            2, 2, (3,2), lbox )

        e = E("","\n\n\n\n\n")
        e.set_edit_pos(4)
        key,lbox = self.ktest( "edit cursor force scroll", 'down',
            [e], 0, 0,
            0, -1, (0,4) )
        assert lbox.inset_fraction[0] == 1

    def test3_page_up(self):
        T,S,E = urwid.Text, SelectableText, urwid.Edit

        self.ktest( "unselectable aligned to aligned", 'page up',
            [T(""),T("\n"),T("\n\n"),T(""),T("\n"),T("\n\n")], 3, 0,
            1, 0, None )

        self.ktest( "unselectable unaligned to aligned", 'page up',
            [T(""),T("\n"),T("\n"),T("\n"),T("\n"),T("\n\n")], 3,-1,
            1, 0, None )

        self.ktest( "selectable to unselectable", 'page up',
            [T(""),T("\n"),T("\n"),T("\n"),S("\n"),T("\n\n")], 4, 1,
            1, -1, None )

        self.ktest( "selectable to cut off selectable", 'page up',
            [S("\n\n"),T("\n"),T("\n"),S("\n"),T("\n\n")], 3, 1,
            0, -1, None )

        self.ktest( "seletable to selectable", 'page up',
            [T("\n\n"),S("\n"),T("\n"),S("\n"),T("\n\n")], 3, 1,
            1, 1, None )

        self.ktest( "within very long selectable", 'page up',
            [S(""),S("\n\n\n\n\n\n\n\n"),T("\n")], 1, -6,
            1, -1, None )

        e = E("","\n\nab\n\n\n\n\ncd\n")
        e.set_edit_pos(11)
        self.ktest( "within very long cursor widget", 'page up',
            [S(""),e,T("\n")], 1, -6,
            1, -2, (2, 0) )

        self.ktest( "pathological cursor widget", 'page up',
            [T(""),E("\n\n\n\n\n\n\n\n","ab"),T("")], 1, -5,
            0, 0, None )

        e = E("","\nab\n\n\n\n\ncd\n")
        e.set_edit_pos(10)
        self.ktest( "very long cursor widget snap", 'page up',
            [T(""),e,T("\n")], 1, -5,
            1, 0, (2, 1) )

        self.ktest( "slight scroll selectable", 'page up',
            [T("\n"),S("\n"),T(""),S(""),T("\n\n\n"),S("")], 5, 4,
            3, 0, None )

        self.ktest( "scroll into snap region", 'page up',
            [T("\n"),S("\n"),T(""),T(""),T("\n\n\n"),S("")], 5, 4,
            1, 0, None )

        self.ktest( "mid scroll short", 'page up',
            [T("\n"),T(""),T(""),S(""),T(""),T("\n"),S(""),T("\n")],
            6, 2,    3, 1, None )

        self.ktest( "mid scroll long", 'page up',
            [T("\n"),S(""),T(""),S(""),T(""),T("\n"),S(""),T("\n")],
            6, 2,    1, 0, None )

        self.ktest( "mid scroll perfect", 'page up',
            [T("\n"),S(""),S(""),S(""),T(""),T("\n"),S(""),T("\n")],
            6, 2,    2, 0, None )

        self.ktest( "cursor move up fail short", 'page up',
            [T("\n"),T("\n"),E("","\nab"),T(""),T("")], 2, 1,
            2, 4, (0, 4) )

        self.ktest( "cursor force fail short", 'page up',
            [T("\n"),T("\n"),E("\n","ab"),T(""),T("")], 2, 1,
            0, 0, None )

        odd_e = E("","hi\nab")
        odd_e.set_edit_pos( 2 )
        # disble cursor movement in odd_e object
        odd_e.move_cursor_to_coords = lambda s,c,xy: 0
        self.ktest( "cursor force fail long", 'page up',
            [odd_e,T("\n"),T("\n"),T("\n"),S(""),T("\n")], 4, 2,
            1, -1, None )

        self.ktest( "prefer not cut off", 'page up',
            [S("\n"),T("\n"),S(""),T("\n\n"),S(""),T("\n")], 4, 2,
            2, 1, None )

        self.ktest( "allow cut off", 'page up',
            [S("\n"),T("\n"),T(""),T("\n\n"),S(""),T("\n")], 4, 2,
            0, -1, None )

        self.ktest( "at top fail", 'page up',
            [T("\n\n"),T("\n"),T("\n\n\n")], 0, 0,
            0, 0, None )

        self.ktest( "all visible fail", 'page up',
            [T("a"),T("\n")], 0, 0,
            0, 0, None )

        self.ktest( "current ok fail", 'page up',
            [T("\n\n"),S("hi")], 1, 3,
            1, 3, None )

        self.ktest( "all visible choose top selectable", 'page up',
            [T(""),S("a"),S("b"),S("c")], 3, 3,
            1, 1, None )

        self.ktest( "bring in edge choose top", 'page up',
            [S("b"),T("-"),S("-"),T("c"),S("d"),T("-")],4,3,
            0, 0, None )

        self.ktest( "bring in edge choose top selectable", 'page up',
            [T("b"),S("-"),S("-"),T("c"),S("d"),T("-")],4,3,
            1, 1, None )

    def test4_page_down(self):
        T,S,E = urwid.Text, SelectableText, urwid.Edit

        self.ktest( "unselectable aligned to aligned", 'page down',
            [T("\n\n"),T("\n"),T(""),T("\n\n"),T("\n"),T("")], 2, 4,
            4, 3, None )

        self.ktest( "unselectable unaligned to aligned", 'page down',
            [T("\n\n"),T("\n"),T("\n"),T("\n"),T("\n"),T("")], 2, 4,
            4, 3, None )

        self.ktest( "selectable to unselectable", 'page down',
            [T("\n\n"),S("\n"),T("\n"),T("\n"),T("\n"),T("")], 1, 2,
            4, 4, None )

        self.ktest( "selectable to cut off selectable", 'page down',
            [T("\n\n"),S("\n"),T("\n"),T("\n"),S("\n\n")], 1, 2,
            4, 3, None )

        self.ktest( "seletable to selectable", 'page down',
            [T("\n\n"),S("\n"),T("\n"),S("\n"),T("\n\n")], 1, 1,
            3, 2, None )

        self.ktest( "within very long selectable", 'page down',
            [T("\n"),S("\n\n\n\n\n\n\n\n"),S("")], 1, 2,
            1, -3, None )

        e = E("","\nab\n\n\n\n\ncd\n\n")
        e.set_edit_pos(2)
        self.ktest( "within very long cursor widget", 'page down',
            [T("\n"),e,S("")], 1, 2,
            1, -2, (1, 4) )

        odd_e = E("","ab\n\n\n\n\n\n\n\n\n")
        odd_e.set_edit_pos( 1 )
        # disble cursor movement in odd_e object
        odd_e.move_cursor_to_coords = lambda s,c,xy: 0
        self.ktest( "pathological cursor widget", 'page down',
            [T(""),odd_e,T("")], 1, 1,
            2, 4, None )

        e = E("","\nab\n\n\n\n\ncd\n")
        e.set_edit_pos(2)
        self.ktest( "very long cursor widget snap", 'page down',
            [T("\n"),e,T("")], 1, 2,
            1, -3, (1, 3) )

        self.ktest( "slight scroll selectable", 'page down',
            [S(""),T("\n\n\n"),S(""),T(""),S("\n"),T("\n")], 0, 0,
            2, 4, None )

        self.ktest( "scroll into snap region", 'page down',
            [S(""),T("\n\n\n"),T(""),T(""),S("\n"),T("\n")], 0, 0,
            4, 3, None )

        self.ktest( "mid scroll short", 'page down',
            [T("\n"),S(""),T("\n"),T(""),S(""),T(""),T(""),T("\n")],
            1, 2,    4, 3, None )

        self.ktest( "mid scroll long", 'page down',
            [T("\n"),S(""),T("\n"),T(""),S(""),T(""),S(""),T("\n")],
            1, 2,    6, 4, None )

        self.ktest( "mid scroll perfect", 'page down',
            [T("\n"),S(""),T("\n"),T(""),S(""),S(""),S(""),T("\n")],
            1, 2,    5, 4, None )

        e = E("","hi\nab")
        e.set_edit_pos( 1 )
        self.ktest( "cursor move up fail short", 'page down',
            [T(""),T(""),e,T("\n"),T("\n")], 2, 1,
            2, -1, (1, 0) )


        odd_e = E("","hi\nab")
        odd_e.set_edit_pos( 1 )
        # disble cursor movement in odd_e object
        odd_e.move_cursor_to_coords = lambda s,c,xy: 0
        self.ktest( "cursor force fail short", 'page down',
            [T(""),T(""),odd_e,T("\n"),T("\n")], 2, 2,
            4, 3, None )

        self.ktest( "cursor force fail long", 'page down',
            [T("\n"),S(""),T("\n"),T("\n"),T("\n"),E("hi\n","ab")],
            1, 2,    4, 4, None )

        self.ktest( "prefer not cut off", 'page down',
            [T("\n"),S(""),T("\n\n"),S(""),T("\n"),S("\n")], 1, 2,
            3, 3, None )

        self.ktest( "allow cut off", 'page down',
            [T("\n"),S(""),T("\n\n"),T(""),T("\n"),S("\n")], 1, 2,
            5, 4, None )

        self.ktest( "at bottom fail", 'page down',
            [T("\n\n"),T("\n"),T("\n\n\n")], 2, 1,
            2, 1, None )

        self.ktest( "all visible fail", 'page down',
            [T("a"),T("\n")], 1, 1,
            1, 1, None )

        self.ktest( "current ok fail", 'page down',
            [S("hi"),T("\n\n")], 0, 0,
            0, 0, None )

        self.ktest( "all visible choose last selectable", 'page down',
            [S("a"),S("b"),S("c"),T("")], 0, 0,
            2, 2, None )

        self.ktest( "bring in edge choose last", 'page down',
            [T("-"),S("d"),T("c"),S("-"),T("-"),S("b")],1,1,
            5,4, None )

        self.ktest( "bring in edge choose last selectable", 'page down',
            [T("-"),S("d"),T("c"),S("-"),S("-"),T("b")],1,1,
            4,3, None )


class ZeroHeightContentsTest(unittest.TestCase):
    def test_listbox_pile(self):
        lb = urwid.ListBox(urwid.SimpleListWalker(
            [urwid.Pile([])]))
        lb.render((40,10), focus=True)

    def test_listbox_text_pile_page_down(self):
        lb = urwid.ListBox(urwid.SimpleListWalker(
            [urwid.Text(u'above'), urwid.Pile([])]))
        lb.keypress((40,10), 'page down')
        self.assertEqual(lb.get_focus()[1], 0)
        lb.keypress((40,10), 'page down') # second one caused ListBox failure
        self.assertEqual(lb.get_focus()[1], 0)

    def test_listbox_text_pile_page_up(self):
        lb = urwid.ListBox(urwid.SimpleListWalker(
            [urwid.Pile([]), urwid.Text(u'below')]))
        lb.set_focus(1)
        lb.keypress((40,10), 'page up')
        self.assertEqual(lb.get_focus()[1], 1)
        lb.keypress((40,10), 'page up') # second one caused pile failure
        self.assertEqual(lb.get_focus()[1], 1)

    def test_listbox_text_pile_down(self):
        sp = urwid.Pile([])
        sp.selectable = lambda: True # abuse our Pile
        lb = urwid.ListBox(urwid.SimpleListWalker([urwid.Text(u'above'), sp]))
        lb.keypress((40,10), 'down')
        self.assertEqual(lb.get_focus()[1], 0)
        lb.keypress((40,10), 'down')
        self.assertEqual(lb.get_focus()[1], 0)

    def test_listbox_text_pile_up(self):
        sp = urwid.Pile([])
        sp.selectable = lambda: True # abuse our Pile
        lb = urwid.ListBox(urwid.SimpleListWalker([sp, urwid.Text(u'below')]))
        lb.set_focus(1)
        lb.keypress((40,10), 'up')
        self.assertEqual(lb.get_focus()[1], 1)
        lb.keypress((40,10), 'up')
        self.assertEqual(lb.get_focus()[1], 1)

