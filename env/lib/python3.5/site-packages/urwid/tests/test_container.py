import unittest

from urwid.tests.util import SelectableText
import urwid


class FrameTest(unittest.TestCase):
    def ftbtest(self, desc, focus_part, header_rows, footer_rows, size,
            focus, top, bottom):
        class FakeWidget:
            def __init__(self, rows, want_focus):
                self.ret_rows = rows
                self.want_focus = want_focus
            def rows(self, size, focus=False):
                assert self.want_focus == focus
                return self.ret_rows
        header = footer = None
        if header_rows:
            header = FakeWidget(header_rows,
                focus and focus_part == 'header')
        if footer_rows:
            footer = FakeWidget(footer_rows,
                focus and focus_part == 'footer')

        f = urwid.Frame(None, header, footer, focus_part)

        rval = f.frame_top_bottom(size, focus)
        exp = (top, bottom), (header_rows, footer_rows)
        assert exp == rval, "%s expected %r but got %r"%(
            desc,exp,rval)

    def test(self):
        self.ftbtest("simple", 'body', 0, 0, (9, 10), True, 0, 0)
        self.ftbtest("simple h", 'body', 3, 0, (9, 10), True, 3, 0)
        self.ftbtest("simple f", 'body', 0, 3, (9, 10), True, 0, 3)
        self.ftbtest("simple hf", 'body', 3, 3, (9, 10), True, 3, 3)
        self.ftbtest("almost full hf", 'body', 4, 5, (9, 10),
            True, 4, 5)
        self.ftbtest("full hf", 'body', 5, 5, (9, 10),
            True, 4, 5)
        self.ftbtest("x full h+1f", 'body', 6, 5, (9, 10),
            False, 4, 5)
        self.ftbtest("full h+1f", 'body', 6, 5, (9, 10),
            True, 4, 5)
        self.ftbtest("full hf+1", 'body', 5, 6, (9, 10),
            True, 3, 6)
        self.ftbtest("F full h+1f", 'footer', 6, 5, (9, 10),
            True, 5, 5)
        self.ftbtest("F full hf+1", 'footer', 5, 6, (9, 10),
            True, 4, 6)
        self.ftbtest("F full hf+5", 'footer', 5, 11, (9, 10),
            True, 0, 10)
        self.ftbtest("full hf+5", 'body', 5, 11, (9, 10),
            True, 0, 9)
        self.ftbtest("H full hf+1", 'header', 5, 6, (9, 10),
            True, 5, 5)
        self.ftbtest("H full h+1f", 'header', 6, 5, (9, 10),
            True, 6, 4)
        self.ftbtest("H full h+5f", 'header', 11, 5, (9, 10),
            True, 10, 0)


class PileTest(unittest.TestCase):
    def ktest(self, desc, l, focus_item, key,
            rkey, rfocus, rpref_col):
        p = urwid.Pile( l, focus_item )
        rval = p.keypress( (20,), key )
        assert rkey == rval, "%s key expected %r but got %r" %(
            desc, rkey, rval)
        new_focus = l.index(p.get_focus())
        assert new_focus == rfocus, "%s focus expected %r but got %r" %(
            desc, rfocus, new_focus)
        new_pref = p.get_pref_col((20,))
        assert new_pref == rpref_col, (
            "%s pref_col expected %r but got %r" % (
            desc, rpref_col, new_pref))

    def test_select_change(self):
        T,S,E = urwid.Text, SelectableText, urwid.Edit

        self.ktest("simple up", [S("")], 0, "up", "up", 0, 0)
        self.ktest("simple down", [S("")], 0, "down", "down", 0, 0)
        self.ktest("ignore up", [T(""),S("")], 1, "up", "up", 1, 0)
        self.ktest("ignore down", [S(""),T("")], 0, "down",
            "down", 0, 0)
        self.ktest("step up", [S(""),S("")], 1, "up", None, 0, 0)
        self.ktest("step down", [S(""),S("")], 0, "down",
            None, 1, 0)
        self.ktest("skip step up", [S(""),T(""),S("")], 2, "up",
            None, 0, 0)
        self.ktest("skip step down", [S(""),T(""),S("")], 0, "down",
            None, 2, 0)
        self.ktest("pad skip step up", [T(""),S(""),T(""),S("")], 3,
            "up", None, 1, 0)
        self.ktest("pad skip step down", [S(""),T(""),S(""),T("")], 0,
            "down", None, 2, 0)
        self.ktest("padi skip step up", [S(""),T(""),S(""),T(""),S("")],
            4, "up", None, 2, 0)
        self.ktest("padi skip step down", [S(""),T(""),S(""),T(""),
            S("")], 0, "down", None, 2, 0)
        e = E("","abcd", edit_pos=1)
        e.keypress((20,),"right") # set a pref_col
        self.ktest("pref step up", [S(""),T(""),e], 2, "up",
            None, 0, 2)
        self.ktest("pref step down", [e,T(""),S("")], 0, "down",
            None, 2, 2)
        z = E("","1234")
        self.ktest("prefx step up", [z,T(""),e], 2, "up",
            None, 0, 2)
        assert z.get_pref_col((20,)) == 2
        z = E("","1234")
        self.ktest("prefx step down", [e,T(""),z], 0, "down",
            None, 2, 2)
        assert z.get_pref_col((20,)) == 2

    def test_init_with_a_generator(self):
        urwid.Pile(urwid.Text(c) for c in "ABC")

    def test_change_focus_with_mouse(self):
        p = urwid.Pile([urwid.Edit(), urwid.Edit()])
        self.assertEqual(p.focus_position, 0)
        p.mouse_event((10,), 'button press', 1, 1, 1, True)
        self.assertEqual(p.focus_position, 1)

    def test_zero_weight(self):
        p = urwid.Pile([
            urwid.SolidFill('a'),
            ('weight', 0, urwid.SolidFill('d')),
            ])
        p.render((5, 4))

    def test_mouse_event_in_empty_pile(self):
        p = urwid.Pile([])
        p.mouse_event((5,), 'button press', 1, 1, 1, False)
        p.mouse_event((5,), 'button press', 1, 1, 1, True)


class ColumnsTest(unittest.TestCase):
    def cwtest(self, desc, l, divide, size, exp, focus_column=0):
        c = urwid.Columns(l, divide, focus_column)
        rval = c.column_widths( size )
        assert rval == exp, "%s expected %s, got %s"%(desc,exp,rval)

    def test_widths(self):
        x = urwid.Text("") # sample "column"
        self.cwtest( "simple 1", [x], 0, (20,), [20] )
        self.cwtest( "simple 2", [x,x], 0, (20,), [10,10] )
        self.cwtest( "simple 2+1", [x,x], 1, (20,), [10,9] )
        self.cwtest( "simple 3+1", [x,x,x], 1, (20,), [6,6,6] )
        self.cwtest( "simple 3+2", [x,x,x], 2, (20,), [5,6,5] )
        self.cwtest( "simple 3+2", [x,x,x], 2, (21,), [6,6,5] )
        self.cwtest( "simple 4+1", [x,x,x,x], 1, (25,), [6,5,6,5] )
        self.cwtest( "squish 4+1", [x,x,x,x], 1, (7,), [1,1,1,1] )
        self.cwtest( "squish 4+1", [x,x,x,x], 1, (6,), [1,2,1] )
        self.cwtest( "squish 4+1", [x,x,x,x], 1, (4,), [2,1] )

        self.cwtest( "fixed 3", [('fixed',4,x),('fixed',6,x),
            ('fixed',2,x)], 1, (25,), [4,6,2] )
        self.cwtest( "fixed 3 cut", [('fixed',4,x),('fixed',6,x),
            ('fixed',2,x)], 1, (13,), [4,6] )
        self.cwtest( "fixed 3 cut2", [('fixed',4,x),('fixed',6,x),
            ('fixed',2,x)], 1, (10,), [4] )

        self.cwtest( "mixed 4", [('weight',2,x),('fixed',5,x),
            x, ('weight',3,x)], 1, (14,), [2,5,1,3] )
        self.cwtest( "mixed 4 a", [('weight',2,x),('fixed',5,x),
            x, ('weight',3,x)], 1, (12,), [1,5,1,2] )
        self.cwtest( "mixed 4 b", [('weight',2,x),('fixed',5,x),
            x, ('weight',3,x)], 1, (10,), [2,5,1] )
        self.cwtest( "mixed 4 c", [('weight',2,x),('fixed',5,x),
            x, ('weight',3,x)], 1, (20,), [4,5,2,6] )

    def test_widths_focus_end(self):
        x = urwid.Text("") # sample "column"
        self.cwtest("end simple 2", [x,x], 0, (20,), [10,10], 1)
        self.cwtest("end simple 2+1", [x,x], 1, (20,), [10,9], 1)
        self.cwtest("end simple 3+1", [x,x,x], 1, (20,), [6,6,6], 2)
        self.cwtest("end simple 3+2", [x,x,x], 2, (20,), [5,6,5], 2)
        self.cwtest("end simple 3+2", [x,x,x], 2, (21,), [6,6,5], 2)
        self.cwtest("end simple 4+1", [x,x,x,x], 1, (25,), [6,5,6,5], 3)
        self.cwtest("end squish 4+1", [x,x,x,x], 1, (7,), [1,1,1,1], 3)
        self.cwtest("end squish 4+1", [x,x,x,x], 1, (6,), [0,1,2,1], 3)
        self.cwtest("end squish 4+1", [x,x,x,x], 1, (4,), [0,0,2,1], 3)

        self.cwtest("end fixed 3", [('fixed',4,x),('fixed',6,x),
            ('fixed',2,x)], 1, (25,), [4,6,2], 2)
        self.cwtest("end fixed 3 cut", [('fixed',4,x),('fixed',6,x),
            ('fixed',2,x)], 1, (13,), [0,6,2], 2)
        self.cwtest("end fixed 3 cut2", [('fixed',4,x),('fixed',6,x),
            ('fixed',2,x)], 1, (8,), [0,0,2], 2)

        self.cwtest("end mixed 4", [('weight',2,x),('fixed',5,x),
            x, ('weight',3,x)], 1, (14,), [2,5,1,3], 3)
        self.cwtest("end mixed 4 a", [('weight',2,x),('fixed',5,x),
            x, ('weight',3,x)], 1, (12,), [1,5,1,2], 3)
        self.cwtest("end mixed 4 b", [('weight',2,x),('fixed',5,x),
            x, ('weight',3,x)], 1, (10,), [0,5,1,2], 3)
        self.cwtest("end mixed 4 c", [('weight',2,x),('fixed',5,x),
            x, ('weight',3,x)], 1, (20,), [4,5,2,6], 3)

    def mctest(self, desc, l, divide, size, col, row, exp, f_col, pref_col):
        c = urwid.Columns( l, divide )
        rval = c.move_cursor_to_coords( size, col, row )
        assert rval == exp, "%s expected %r, got %r"%(desc,exp,rval)
        assert c.focus_col == f_col, "%s expected focus_col %s got %s"%(
            desc, f_col, c.focus_col)
        pc = c.get_pref_col( size )
        assert pc == pref_col, "%s expected pref_col %s, got %s"%(
            desc, pref_col, pc)

    def test_move_cursor(self):
        e, s, x = urwid.Edit("",""),SelectableText(""), urwid.Text("")
        self.mctest("nothing selectbl",[x,x,x],1,(20,),9,0,False,0,None)
        self.mctest("dead on",[x,s,x],1,(20,),9,0,True,1,9)
        self.mctest("l edge",[x,s,x],1,(20,),6,0,True,1,6)
        self.mctest("r edge",[x,s,x],1,(20,),13,0,True,1,13)
        self.mctest("l off",[x,s,x],1,(20,),2,0,True,1,2)
        self.mctest("r off",[x,s,x],1,(20,),17,0,True,1,17)
        self.mctest("l off 2",[x,x,s],1,(20,),2,0,True,2,2)
        self.mctest("r off 2",[s,x,x],1,(20,),17,0,True,0,17)

        self.mctest("l between",[s,s,x],1,(20,),6,0,True,0,6)
        self.mctest("r between",[x,s,s],1,(20,),13,0,True,1,13)
        self.mctest("l between 2l",[s,s,x],2,(22,),6,0,True,0,6)
        self.mctest("r between 2l",[x,s,s],2,(22,),14,0,True,1,14)
        self.mctest("l between 2r",[s,s,x],2,(22,),7,0,True,1,7)
        self.mctest("r between 2r",[x,s,s],2,(22,),15,0,True,2,15)

        # unfortunate pref_col shifting
        self.mctest("l e edge",[x,e,x],1,(20,),6,0,True,1,7)
        self.mctest("r e edge",[x,e,x],1,(20,),13,0,True,1,12)

        # 'left'/'right' special cases
        self.mctest("right", [e, e, e], 0, (12,), 'right', 0, True, 2, 'right')
        self.mctest("left", [e, e, e], 0, (12,), 'left', 0, True, 0, 'left')

    def test_init_with_a_generator(self):
        urwid.Columns(urwid.Text(c) for c in "ABC")

    def test_old_attributes(self):
        c = urwid.Columns([urwid.Text(u'a'), urwid.SolidFill(u'x')],
            box_columns=[1])
        self.assertEqual(c.box_columns, [1])
        c.box_columns=[]
        self.assertEqual(c.box_columns, [])

    def test_box_column(self):
        c = urwid.Columns([urwid.Filler(urwid.Edit()),urwid.Text('')],
            box_columns=[0])
        c.keypress((10,), 'x')
        c.get_cursor_coords((10,))
        c.move_cursor_to_coords((10,), 0, 0)
        c.mouse_event((10,), 'foo', 1, 0, 0, True)
        c.get_pref_col((10,))



class OverlayTest(unittest.TestCase):
    def test_old_params(self):
        o1 = urwid.Overlay(urwid.SolidFill(u'X'), urwid.SolidFill(u'O'),
            ('fixed left', 5), ('fixed right', 4),
            ('fixed top', 3), ('fixed bottom', 2),)
        self.assertEqual(o1.contents[1][1], (
            'left', None, 'relative', 100, None, 5, 4,
            'top', None, 'relative', 100, None, 3, 2))
        o2 = urwid.Overlay(urwid.SolidFill(u'X'), urwid.SolidFill(u'O'),
            ('fixed right', 5), ('fixed left', 4),
            ('fixed bottom', 3), ('fixed top', 2),)
        self.assertEqual(o2.contents[1][1], (
            'right', None, 'relative', 100, None, 4, 5,
            'bottom', None, 'relative', 100, None, 2, 3))

    def test_get_cursor_coords(self):
        self.assertEqual(urwid.Overlay(urwid.Filler(urwid.Edit()),
            urwid.SolidFill(u'B'),
            'right', 1, 'bottom', 1).get_cursor_coords((2,2)), (1,1))


class GridFlowTest(unittest.TestCase):
    def test_cell_width(self):
        gf = urwid.GridFlow([], 5, 0, 0, 'left')
        self.assertEqual(gf.cell_width, 5)

    def test_basics(self):
        repr(urwid.GridFlow([], 5, 0, 0, 'left')) # should not fail

    def test_v_sep(self):
        gf = urwid.GridFlow([urwid.Text("test")], 10, 3, 1, "center")
        self.assertEqual(gf.rows((40,), False), 1)


class WidgetSquishTest(unittest.TestCase):
    def wstest(self, w):
        c = w.render((80,0), focus=False)
        assert c.rows() == 0
        c = w.render((80,0), focus=True)
        assert c.rows() == 0
        c = w.render((80,1), focus=False)
        assert c.rows() == 1
        c = w.render((0, 25), focus=False)
        c = w.render((1, 25), focus=False)

    def fwstest(self, w):
        def t(cols, focus):
            wrows = w.rows((cols,), focus)
            c = w.render((cols,), focus)
            assert c.rows() == wrows, (c.rows(), wrows)
            if focus and hasattr(w, 'get_cursor_coords'):
                gcc = w.get_cursor_coords((cols,))
                assert c.cursor == gcc, (c.cursor, gcc)
        t(0, False)
        t(1, False)
        t(0, True)
        t(1, True)

    def test_listbox(self):
        self.wstest(urwid.ListBox([]))
        self.wstest(urwid.ListBox([urwid.Text("hello")]))

    def test_bargraph(self):
        self.wstest(urwid.BarGraph(['foo','bar']))

    def test_graphvscale(self):
        self.wstest(urwid.GraphVScale([(0,"hello")], 1))
        self.wstest(urwid.GraphVScale([(5,"hello")], 1))

    def test_solidfill(self):
        self.wstest(urwid.SolidFill())

    def test_filler(self):
        self.wstest(urwid.Filler(urwid.Text("hello")))

    def test_overlay(self):
        self.wstest(urwid.Overlay(
            urwid.BigText("hello",urwid.Thin6x6Font()),
            urwid.SolidFill(),
            'center', None, 'middle', None))
        self.wstest(urwid.Overlay(
            urwid.Text("hello"), urwid.SolidFill(),
            'center',  ('relative', 100), 'middle', None))

    def test_frame(self):
        self.wstest(urwid.Frame(urwid.SolidFill()))
        self.wstest(urwid.Frame(urwid.SolidFill(),
            header=urwid.Text("hello")))
        self.wstest(urwid.Frame(urwid.SolidFill(),
            header=urwid.Text("hello"),
            footer=urwid.Text("hello")))

    def test_pile(self):
        self.wstest(urwid.Pile([urwid.SolidFill()]))
        self.wstest(urwid.Pile([('flow', urwid.Text("hello"))]))
        self.wstest(urwid.Pile([]))

    def test_columns(self):
        self.wstest(urwid.Columns([urwid.SolidFill()]))
        self.wstest(urwid.Columns([(4, urwid.SolidFill())]))

    def test_buttons(self):
        self.fwstest(urwid.Button(u"hello"))
        self.fwstest(urwid.RadioButton([], u"hello"))


class CommonContainerTest(unittest.TestCase):
    def test_pile(self):
        t1 = urwid.Text(u'one')
        t2 = urwid.Text(u'two')
        t3 = urwid.Text(u'three')
        sf = urwid.SolidFill('x')
        p = urwid.Pile([])
        self.assertEqual(p.focus, None)
        self.assertRaises(IndexError, lambda: getattr(p, 'focus_position'))
        self.assertRaises(IndexError, lambda: setattr(p, 'focus_position',
            None))
        self.assertRaises(IndexError, lambda: setattr(p, 'focus_position', 0))
        p.contents = [(t1, ('pack', None)), (t2, ('pack', None)),
            (sf, ('given', 3)), (t3, ('pack', None))]
        p.focus_position = 1
        del p.contents[0]
        self.assertEqual(p.focus_position, 0)
        p.contents[0:0] = [(t3, ('pack', None)), (t2, ('pack', None))]
        p.contents.insert(3, (t1, ('pack', None)))
        self.assertEqual(p.focus_position, 2)
        self.assertRaises(urwid.PileError, lambda: p.contents.append(t1))
        self.assertRaises(urwid.PileError, lambda: p.contents.append((t1, None)))
        self.assertRaises(urwid.PileError, lambda: p.contents.append((t1, 'given')))

        p = urwid.Pile([t1, t2])
        self.assertEqual(p.focus, t1)
        self.assertEqual(p.focus_position, 0)
        p.focus_position = 1
        self.assertEqual(p.focus, t2)
        self.assertEqual(p.focus_position, 1)
        p.focus_position = 0
        self.assertRaises(IndexError, lambda: setattr(p, 'focus_position', -1))
        self.assertRaises(IndexError, lambda: setattr(p, 'focus_position', 2))
        # old methods:
        p.set_focus(0)
        self.assertRaises(IndexError, lambda: p.set_focus(-1))
        self.assertRaises(IndexError, lambda: p.set_focus(2))
        p.set_focus(t2)
        self.assertEqual(p.focus_position, 1)
        self.assertRaises(ValueError, lambda: p.set_focus('nonexistant'))
        self.assertEqual(p.widget_list, [t1, t2])
        self.assertEqual(p.item_types, [('weight', 1), ('weight', 1)])
        p.widget_list = [t2, t1]
        self.assertEqual(p.widget_list, [t2, t1])
        self.assertEqual(p.contents, [(t2, ('weight', 1)), (t1, ('weight', 1))])
        self.assertEqual(p.focus_position, 1) # focus unchanged
        p.item_types = [('flow', None), ('weight', 2)]
        self.assertEqual(p.item_types, [('flow', None), ('weight', 2)])
        self.assertEqual(p.contents, [(t2, ('pack', None)), (t1, ('weight', 2))])
        self.assertEqual(p.focus_position, 1) # focus unchanged
        p.widget_list = [t1]
        self.assertEqual(len(p.contents), 1)
        self.assertEqual(p.focus_position, 0)
        p.widget_list.extend([t2, t1])
        self.assertEqual(len(p.contents), 3)
        self.assertEqual(p.item_types, [
            ('flow', None), ('weight', 1), ('weight', 1)])
        p.item_types[:] = [('weight', 2)]
        self.assertEqual(len(p.contents), 1)

    def test_columns(self):
        t1 = urwid.Text(u'one')
        t2 = urwid.Text(u'two')
        t3 = urwid.Text(u'three')
        sf = urwid.SolidFill('x')
        c = urwid.Columns([])
        self.assertEqual(c.focus, None)
        self.assertRaises(IndexError, lambda: getattr(c, 'focus_position'))
        self.assertRaises(IndexError, lambda: setattr(c, 'focus_position',
            None))
        self.assertRaises(IndexError, lambda: setattr(c, 'focus_position', 0))
        c.contents = [
            (t1, ('pack', None, False)),
            (t2, ('weight', 1, False)),
            (sf, ('weight', 2, True)),
            (t3, ('given', 10, False))]
        c.focus_position = 1
        del c.contents[0]
        self.assertEqual(c.focus_position, 0)
        c.contents[0:0] = [
            (t3, ('given', 10, False)),
            (t2, ('weight', 1, False))]
        c.contents.insert(3, (t1, ('pack', None, False)))
        self.assertEqual(c.focus_position, 2)
        self.assertRaises(urwid.ColumnsError, lambda: c.contents.append(t1))
        self.assertRaises(urwid.ColumnsError, lambda: c.contents.append((t1, None)))
        self.assertRaises(urwid.ColumnsError, lambda: c.contents.append((t1, 'given')))

        c = urwid.Columns([t1, t2])
        self.assertEqual(c.focus, t1)
        self.assertEqual(c.focus_position, 0)
        c.focus_position = 1
        self.assertEqual(c.focus, t2)
        self.assertEqual(c.focus_position, 1)
        c.focus_position = 0
        self.assertRaises(IndexError, lambda: setattr(c, 'focus_position', -1))
        self.assertRaises(IndexError, lambda: setattr(c, 'focus_position', 2))
        # old methods:
        c = urwid.Columns([t1, ('weight', 3, t2), sf], box_columns=[2])
        c.set_focus(0)
        self.assertRaises(IndexError, lambda: c.set_focus(-1))
        self.assertRaises(IndexError, lambda: c.set_focus(3))
        c.set_focus(t2)
        self.assertEqual(c.focus_position, 1)
        self.assertRaises(ValueError, lambda: c.set_focus('nonexistant'))
        self.assertEqual(c.widget_list, [t1, t2, sf])
        self.assertEqual(c.column_types, [
            ('weight', 1), ('weight', 3), ('weight', 1)])
        self.assertEqual(c.box_columns, [2])
        c.widget_list = [t2, t1, sf]
        self.assertEqual(c.widget_list, [t2, t1, sf])
        self.assertEqual(c.box_columns, [2])

        self.assertEqual(c.contents, [
            (t2, ('weight', 1, False)),
            (t1, ('weight', 3, False)),
            (sf, ('weight', 1, True))])
        self.assertEqual(c.focus_position, 1) # focus unchanged
        c.column_types = [
            ('flow', None), # use the old name
            ('weight', 2),
            ('fixed', 5)]
        self.assertEqual(c.column_types, [
            ('flow', None),
            ('weight', 2),
            ('fixed', 5)])
        self.assertEqual(c.contents, [
            (t2, ('pack', None, False)),
            (t1, ('weight', 2, False)),
            (sf, ('given', 5, True))])
        self.assertEqual(c.focus_position, 1) # focus unchanged
        c.widget_list = [t1]
        self.assertEqual(len(c.contents), 1)
        self.assertEqual(c.focus_position, 0)
        c.widget_list.extend([t2, t1])
        self.assertEqual(len(c.contents), 3)
        self.assertEqual(c.column_types, [
            ('flow', None), ('weight', 1), ('weight', 1)])
        c.column_types[:] = [('weight', 2)]
        self.assertEqual(len(c.contents), 1)

    def test_list_box(self):
        lb = urwid.ListBox(urwid.SimpleFocusListWalker([]))
        self.assertEqual(lb.focus, None)
        self.assertRaises(IndexError, lambda: getattr(lb, 'focus_position'))
        self.assertRaises(IndexError, lambda: setattr(lb, 'focus_position',
            None))
        self.assertRaises(IndexError, lambda: setattr(lb, 'focus_position', 0))

        t1 = urwid.Text(u'one')
        t2 = urwid.Text(u'two')
        lb = urwid.ListBox(urwid.SimpleListWalker([t1, t2]))
        self.assertEqual(lb.focus, t1)
        self.assertEqual(lb.focus_position, 0)
        lb.focus_position = 1
        self.assertEqual(lb.focus, t2)
        self.assertEqual(lb.focus_position, 1)
        lb.focus_position = 0
        self.assertRaises(IndexError, lambda: setattr(lb, 'focus_position', -1))
        self.assertRaises(IndexError, lambda: setattr(lb, 'focus_position', 2))

    def test_grid_flow(self):
        gf = urwid.GridFlow([], 5, 1, 0, 'left')
        self.assertEqual(gf.focus, None)
        self.assertEqual(gf.contents, [])
        self.assertRaises(IndexError, lambda: getattr(gf, 'focus_position'))
        self.assertRaises(IndexError, lambda: setattr(gf, 'focus_position',
            None))
        self.assertRaises(IndexError, lambda: setattr(gf, 'focus_position', 0))
        self.assertEqual(gf.options(), ('given', 5))
        self.assertEqual(gf.options(width_amount=9), ('given', 9))
        self.assertRaises(urwid.GridFlowError, lambda: gf.options(
            'pack', None))

        t1 = urwid.Text(u'one')
        t2 = urwid.Text(u'two')
        gf = urwid.GridFlow([t1, t2], 5, 1, 0, 'left')
        self.assertEqual(gf.focus, t1)
        self.assertEqual(gf.focus_position, 0)
        self.assertEqual(gf.contents, [(t1, ('given', 5)), (t2, ('given', 5))])
        gf.focus_position = 1
        self.assertEqual(gf.focus, t2)
        self.assertEqual(gf.focus_position, 1)
        gf.contents.insert(0, (t2, ('given', 5)))
        self.assertEqual(gf.focus_position, 2)
        self.assertRaises(urwid.GridFlowError, lambda: gf.contents.append(()))
        self.assertRaises(urwid.GridFlowError, lambda: gf.contents.insert(1,
            (t1, ('pack', None))))
        gf.focus_position = 0
        self.assertRaises(IndexError, lambda: setattr(gf, 'focus_position', -1))
        self.assertRaises(IndexError, lambda: setattr(gf, 'focus_position', 3))
        # old methods:
        gf.set_focus(0)
        self.assertRaises(IndexError, lambda: gf.set_focus(-1))
        self.assertRaises(IndexError, lambda: gf.set_focus(3))
        gf.set_focus(t1)
        self.assertEqual(gf.focus_position, 1)
        self.assertRaises(ValueError, lambda: gf.set_focus('nonexistant'))

    def test_overlay(self):
        s1 = urwid.SolidFill(u'1')
        s2 = urwid.SolidFill(u'2')
        o = urwid.Overlay(s1, s2,
            'center', ('relative', 50), 'middle', ('relative', 50))
        self.assertEqual(o.focus, s1)
        self.assertEqual(o.focus_position, 1)
        self.assertRaises(IndexError, lambda: setattr(o, 'focus_position',
            None))
        self.assertRaises(IndexError, lambda: setattr(o, 'focus_position', 2))

        self.assertEqual(o.contents[0], (s2,
            urwid.Overlay._DEFAULT_BOTTOM_OPTIONS))
        self.assertEqual(o.contents[1], (s1, (
            'center', None, 'relative', 50, None, 0, 0,
            'middle', None, 'relative', 50, None, 0, 0)))

    def test_frame(self):
        s1 = urwid.SolidFill(u'1')

        f = urwid.Frame(s1)
        self.assertEqual(f.focus, s1)
        self.assertEqual(f.focus_position, 'body')
        self.assertRaises(IndexError, lambda: setattr(f, 'focus_position',
            None))
        self.assertRaises(IndexError, lambda: setattr(f, 'focus_position',
            'header'))

        t1 = urwid.Text(u'one')
        t2 = urwid.Text(u'two')
        t3 = urwid.Text(u'three')
        f = urwid.Frame(s1, t1, t2, 'header')
        self.assertEqual(f.focus, t1)
        self.assertEqual(f.focus_position, 'header')
        f.focus_position = 'footer'
        self.assertEqual(f.focus, t2)
        self.assertEqual(f.focus_position, 'footer')
        self.assertRaises(IndexError, lambda: setattr(f, 'focus_position', -1))
        self.assertRaises(IndexError, lambda: setattr(f, 'focus_position', 2))
        del f.contents['footer']
        self.assertEqual(f.footer, None)
        self.assertEqual(f.focus_position, 'body')
        f.contents.update(footer=(t3, None), header=(t2, None))
        self.assertEqual(f.header, t2)
        self.assertEqual(f.footer, t3)
        def set1():
            f.contents['body'] = t1
        self.assertRaises(urwid.FrameError, set1)
        def set2():
            f.contents['body'] = (t1, 'given')
        self.assertRaises(urwid.FrameError, set2)

    def test_focus_path(self):
        # big tree of containers
        t = urwid.Text(u'x')
        e = urwid.Edit(u'?')
        c = urwid.Columns([t, e, t, t])
        p = urwid.Pile([t, t, c, t])
        a = urwid.AttrMap(p, 'gets ignored')
        s = urwid.SolidFill(u'/')
        o = urwid.Overlay(e, s, 'center', 'pack', 'middle', 'pack')
        lb = urwid.ListBox(urwid.SimpleFocusListWalker([t, a, o, t]))
        lb.focus_position = 1
        g = urwid.GridFlow([t, t, t, t, e, t], 10, 0, 0, 'left')
        g.focus_position = 4
        f = urwid.Frame(lb, header=t, footer=g)

        self.assertEqual(f.get_focus_path(), ['body', 1, 2, 1])
        f.set_focus_path(['footer']) # same as f.focus_position = 'footer'
        self.assertEqual(f.get_focus_path(), ['footer', 4])
        f.set_focus_path(['body', 1, 2, 2])
        self.assertEqual(f.get_focus_path(), ['body', 1, 2, 2])
        self.assertRaises(IndexError, lambda: f.set_focus_path([0, 1, 2]))
        self.assertRaises(IndexError, lambda: f.set_focus_path(['body', 2, 2]))
        f.set_focus_path(['body', 2]) # focus the overlay
        self.assertEqual(f.get_focus_path(), ['body', 2, 1])
