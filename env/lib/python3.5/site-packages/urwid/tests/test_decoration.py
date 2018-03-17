import unittest

import urwid


class PaddingTest(unittest.TestCase):
    def ptest(self, desc, align, width, maxcol, left, right,min_width=None):
        p = urwid.Padding(None, align, width, min_width)
        l, r = p.padding_values((maxcol,),False)
        assert (l,r)==(left,right), "%s expected %s but got %s"%(
            desc, (left,right), (l,r))

    def petest(self, desc, align, width):
        self.assertRaises(urwid.PaddingError, lambda:
            urwid.Padding(None, align, width))

    def test_create(self):
        self.petest("invalid pad",6,5)
        self.petest("invalid pad type",('bad',2),5)
        self.petest("invalid width",'center','42')
        self.petest("invalid width type",'center',('gouranga',4))

    def test_values(self):
        self.ptest("left align 5 7",'left',5,7,0,2)
        self.ptest("left align 7 7",'left',7,7,0,0)
        self.ptest("left align 9 7",'left',9,7,0,0)
        self.ptest("right align 5 7",'right',5,7,2,0)
        self.ptest("center align 5 7",'center',5,7,1,1)
        self.ptest("fixed left",('fixed left',3),5,10,3,2)
        self.ptest("fixed left reduce",('fixed left',3),8,10,2,0)
        self.ptest("fixed left shrink",('fixed left',3),18,10,0,0)
        self.ptest("fixed left, right",
            ('fixed left',3),('fixed right',4),17,3,4)
        self.ptest("fixed left, right, min_width",
            ('fixed left',3),('fixed right',4),10,3,2,5)
        self.ptest("fixed left, right, min_width 2",
            ('fixed left',3),('fixed right',4),10,2,0,8)
        self.ptest("fixed right",('fixed right',3),5,10,2,3)
        self.ptest("fixed right reduce",('fixed right',3),8,10,0,2)
        self.ptest("fixed right shrink",('fixed right',3),18,10,0,0)
        self.ptest("fixed right, left",
            ('fixed right',3),('fixed left',4),17,4,3)
        self.ptest("fixed right, left, min_width",
            ('fixed right',3),('fixed left',4),10,2,3,5)
        self.ptest("fixed right, left, min_width 2",
            ('fixed right',3),('fixed left',4),10,0,2,8)
        self.ptest("relative 30",('relative',30),5,10,1,4)
        self.ptest("relative 50",('relative',50),5,10,2,3)
        self.ptest("relative 130 edge",('relative',130),5,10,5,0)
        self.ptest("relative -10 edge",('relative',-10),4,10,0,6)
        self.ptest("center relative 70",'center',('relative',70),
            10,1,2)
        self.ptest("center relative 70 grow 8",'center',('relative',70),
            10,1,1,8)

    def mctest(self, desc, left, right, size, cx, innercx):
        class Inner:
            def __init__(self, desc, innercx):
                self.desc = desc
                self.innercx = innercx
            def move_cursor_to_coords(self,size,cx,cy):
                assert cx==self.innercx, desc
        i = Inner(desc,innercx)
        p = urwid.Padding(i, ('fixed left',left),
            ('fixed right',right))
        p.move_cursor_to_coords(size, cx, 0)

    def test_cursor(self):
        self.mctest("cursor left edge",2,2,(10,2),2,0)
        self.mctest("cursor left edge-1",2,2,(10,2),1,0)
        self.mctest("cursor right edge",2,2,(10,2),7,5)
        self.mctest("cursor right edge+1",2,2,(10,2),8,5)

    def test_reduced_padding_cursor(self):
        # FIXME: This is at least consistent now, but I don't like it.
        # pack() on an Edit should leave room for the cursor
        # fixing this gets deep into things like Edit._shift_view_to_cursor
        # though, so this might not get fixed for a while

        p = urwid.Padding(urwid.Edit(u'',u''), width='pack', left=4)
        self.assertEqual(p.render((10,), True).cursor, None)
        self.assertEqual(p.get_cursor_coords((10,)), None)
        self.assertEqual(p.render((4,), True).cursor, None)
        self.assertEqual(p.get_cursor_coords((4,)), None)

        p = urwid.Padding(urwid.Edit(u'',u''), width=('relative', 100), left=4)
        self.assertEqual(p.render((10,), True).cursor, (4, 0))
        self.assertEqual(p.get_cursor_coords((10,)), (4, 0))
        self.assertEqual(p.render((4,), True).cursor, None)
        self.assertEqual(p.get_cursor_coords((4,)), None)


class FillerTest(unittest.TestCase):
    def ftest(self, desc, valign, height, maxrow, top, bottom,
            min_height=None):
        f = urwid.Filler(None, valign, height, min_height)
        t, b = f.filler_values((20,maxrow), False)
        assert (t,b)==(top,bottom), "%s expected %s but got %s"%(
            desc, (top,bottom), (t,b))

    def fetest(self, desc, valign, height):
        self.assertRaises(urwid.FillerError, lambda:
            urwid.Filler(None, valign, height))

    def test_create(self):
        self.fetest("invalid pad",6,5)
        self.fetest("invalid pad type",('bad',2),5)
        self.fetest("invalid width",'middle','42')
        self.fetest("invalid width type",'middle',('gouranga',4))
        self.fetest("invalid combination",('relative',20),
            ('fixed bottom',4))
        self.fetest("invalid combination 2",('relative',20),
            ('fixed top',4))

    def test_values(self):
        self.ftest("top align 5 7",'top',5,7,0,2)
        self.ftest("top align 7 7",'top',7,7,0,0)
        self.ftest("top align 9 7",'top',9,7,0,0)
        self.ftest("bottom align 5 7",'bottom',5,7,2,0)
        self.ftest("middle align 5 7",'middle',5,7,1,1)
        self.ftest("fixed top",('fixed top',3),5,10,3,2)
        self.ftest("fixed top reduce",('fixed top',3),8,10,2,0)
        self.ftest("fixed top shrink",('fixed top',3),18,10,0,0)
        self.ftest("fixed top, bottom",
            ('fixed top',3),('fixed bottom',4),17,3,4)
        self.ftest("fixed top, bottom, min_width",
            ('fixed top',3),('fixed bottom',4),10,3,2,5)
        self.ftest("fixed top, bottom, min_width 2",
            ('fixed top',3),('fixed bottom',4),10,2,0,8)
        self.ftest("fixed bottom",('fixed bottom',3),5,10,2,3)
        self.ftest("fixed bottom reduce",('fixed bottom',3),8,10,0,2)
        self.ftest("fixed bottom shrink",('fixed bottom',3),18,10,0,0)
        self.ftest("fixed bottom, top",
            ('fixed bottom',3),('fixed top',4),17,4,3)
        self.ftest("fixed bottom, top, min_height",
            ('fixed bottom',3),('fixed top',4),10,2,3,5)
        self.ftest("fixed bottom, top, min_height 2",
            ('fixed bottom',3),('fixed top',4),10,0,2,8)
        self.ftest("relative 30",('relative',30),5,10,1,4)
        self.ftest("relative 50",('relative',50),5,10,2,3)
        self.ftest("relative 130 edge",('relative',130),5,10,5,0)
        self.ftest("relative -10 edge",('relative',-10),4,10,0,6)
        self.ftest("middle relative 70",'middle',('relative',70),
            10,1,2)
        self.ftest("middle relative 70 grow 8",'middle',('relative',70),
            10,1,1,8)

    def test_repr(self):
        repr(urwid.Filler(urwid.Text(u'hai')))
