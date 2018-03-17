import unittest

from urwid import text_layout
from urwid.compat import B
import urwid


class CalcBreaksTest(object):
    def cbtest(self, width, exp):
        result = text_layout.default_layout.calculate_text_segments(
            B(self.text), width, self.mode )
        assert len(result) == len(exp), repr((result, exp))
        for l,e in zip(result, exp):
            end = l[-1][-1]
            assert end == e, repr((result,exp))

    def test(self):
        for width, exp in self.do:
            self.cbtest( width, exp )


class CalcBreaksCharTest(CalcBreaksTest, unittest.TestCase):
    mode = 'any'
    text = "abfghsdjf askhtrvs\naltjhgsdf ljahtshgf"
    # tests
    do = [
        ( 100, [18,38] ),
        ( 6, [6, 12, 18, 25, 31, 37, 38] ),
        ( 10, [10, 18, 29, 38] ),
    ]


class CalcBreaksDBCharTest(CalcBreaksTest, unittest.TestCase):
    def setUp(self):
        urwid.set_encoding("euc-jp")

    mode = 'any'
    text = "abfgh\xA1\xA1j\xA1\xA1xskhtrvs\naltjhgsdf\xA1\xA1jahtshgf"
    # tests
    do = [
        ( 10, [10, 18, 28, 38] ),
        ( 6, [5, 11, 17, 18, 25, 31, 37, 38] ),
        ( 100, [18, 38]),
    ]


class CalcBreaksWordTest(CalcBreaksTest, unittest.TestCase):
    mode = 'space'
    text = "hello world\nout there. blah"
    # tests
    do = [
        ( 10, [5, 11, 22, 27] ),
        ( 5, [5, 11, 17, 22, 27] ),
        ( 100, [11, 27] ),
    ]


class CalcBreaksWordTest2(CalcBreaksTest, unittest.TestCase):
    mode = 'space'
    text = "A simple set of words, really...."
    do = [
        ( 10, [8, 15, 22, 33]),
        ( 17, [15, 33]),
        ( 13, [12, 22, 33]),
    ]


class CalcBreaksDBWordTest(CalcBreaksTest, unittest.TestCase):
    def setUp(self):
        urwid.set_encoding("euc-jp")

    mode = 'space'
    text = "hel\xA1\xA1 world\nout-\xA1\xA1tre blah"
    # tests
    do = [
        ( 10, [5, 11, 21, 26] ),
        ( 5, [5, 11, 16, 21, 26] ),
        ( 100, [11, 26] ),
    ]


class CalcBreaksUTF8Test(CalcBreaksTest, unittest.TestCase):
    def setUp(self):
        urwid.set_encoding("utf-8")

    mode = 'space'
    text = '\xe6\x9b\xbf\xe6\xb4\xbc\xe6\xb8\x8e\xe6\xba\x8f\xe6\xbd\xba'
    do = [
        (4, [6, 12, 15] ),
        (10, [15] ),
        (5, [6, 12, 15] ),
    ]


class CalcBreaksCantDisplayTest(unittest.TestCase):
    def test(self):
        urwid.set_encoding("euc-jp")
        self.assertRaises(text_layout.CanNotDisplayText,
            text_layout.default_layout.calculate_text_segments,
            B('\xA1\xA1'), 1, 'space' )
        urwid.set_encoding("utf-8")
        self.assertRaises(text_layout.CanNotDisplayText,
            text_layout.default_layout.calculate_text_segments,
            B('\xe9\xa2\x96'), 1, 'space' )


class SubsegTest(unittest.TestCase):
    def setUp(self):
        urwid.set_encoding("euc-jp")

    def st(self, seg, text, start, end, exp):
        text = B(text)
        s = urwid.LayoutSegment(seg)
        result = s.subseg( text, start, end )
        assert result == exp, "Expected %r, got %r"%(exp,result)

    def test1_padding(self):
        self.st( (10, None), "", 0, 8,    [(8, None)] )
        self.st( (10, None), "", 2, 10, [(8, None)] )
        self.st( (10, 0), "", 3, 7,     [(4, 0)] )
        self.st( (10, 0), "", 0, 20,     [(10, 0)] )

    def test2_text(self):
        self.st( (10, 0, B("1234567890")), "", 0, 8,  [(8,0,B("12345678"))] )
        self.st( (10, 0, B("1234567890")), "", 2, 10, [(8,0,B("34567890"))] )
        self.st( (10, 0, B("12\xA1\xA156\xA1\xA190")), "", 2, 8,
            [(6, 0, B("\xA1\xA156\xA1\xA1"))] )
        self.st( (10, 0, B("12\xA1\xA156\xA1\xA190")), "", 3, 8,
            [(5, 0, B(" 56\xA1\xA1"))] )
        self.st( (10, 0, B("12\xA1\xA156\xA1\xA190")), "", 2, 7,
            [(5, 0, B("\xA1\xA156 "))] )
        self.st( (10, 0, B("12\xA1\xA156\xA1\xA190")), "", 3, 7,
            [(4, 0, B(" 56 "))] )
        self.st( (10, 0, B("12\xA1\xA156\xA1\xA190")), "", 0, 20,
            [(10, 0, B("12\xA1\xA156\xA1\xA190"))] )

    def test3_range(self):
        t = "1234567890"
        self.st( (10, 0, 10), t, 0, 8,    [(8, 0, 8)] )
        self.st( (10, 0, 10), t, 2, 10, [(8, 2, 10)] )
        self.st( (6, 2, 8), t, 1, 6,     [(5, 3, 8)] )
        self.st( (6, 2, 8), t, 0, 5,     [(5, 2, 7)] )
        self.st( (6, 2, 8), t, 1, 5,     [(4, 3, 7)] )
        t = "12\xA1\xA156\xA1\xA190"
        self.st( (10, 0, 10), t, 0, 8,    [(8, 0, 8)] )
        self.st( (10, 0, 10), t, 2, 10, [(8, 2, 10)] )
        self.st( (6, 2, 8), t, 1, 6,     [(1, 3), (4, 4, 8)] )
        self.st( (6, 2, 8), t, 0, 5,     [(4, 2, 6), (1, 6)] )
        self.st( (6, 2, 8), t, 1, 5,     [(1, 3), (2, 4, 6), (1, 6)] )


class CalcTranslateTest(object):
    def setUp(self):
        urwid.set_encoding("utf-8")

    def test1_left(self):
        result = urwid.default_layout.layout( self.text,
            self.width, 'left', self.mode)
        assert result == self.result_left, result

    def test2_right(self):
        result = urwid.default_layout.layout( self.text,
            self.width, 'right', self.mode)
        assert result == self.result_right, result

    def test3_center(self):
        result = urwid.default_layout.layout( self.text,
            self.width, 'center', self.mode)
        assert result == self.result_center, result


class CalcTranslateCharTest(CalcTranslateTest, unittest.TestCase):
    text = "It's out of control!\nYou've got to"
    mode = 'any'
    width = 15
    result_left = [
        [(15, 0, 15)],
        [(5, 15, 20), (0, 20)],
        [(13, 21, 34), (0, 34)]]
    result_right = [
        [(15, 0, 15)],
        [(10, None), (5, 15, 20), (0,20)],
        [(2, None), (13, 21, 34), (0,34)]]
    result_center = [
        [(15, 0, 15)],
        [(5, None), (5, 15, 20), (0,20)],
        [(1, None), (13, 21, 34), (0,34)]]


class CalcTranslateWordTest(CalcTranslateTest, unittest.TestCase):
    text = "It's out of control!\nYou've got to"
    mode = 'space'
    width = 14
    result_left = [
        [(11, 0, 11), (0, 11)],
        [(8, 12, 20), (0, 20)],
        [(13, 21, 34), (0, 34)]]
    result_right = [
        [(3, None), (11, 0, 11), (0, 11)],
        [(6, None), (8, 12, 20), (0, 20)],
        [(1, None), (13, 21, 34), (0, 34)]]
    result_center = [
        [(2, None), (11, 0, 11), (0, 11)],
        [(3, None), (8, 12, 20), (0, 20)],
        [(1, None), (13, 21, 34), (0, 34)]]


class CalcTranslateWordTest2(CalcTranslateTest, unittest.TestCase):
    text = "It's out of control!\nYou've got to "
    mode = 'space'
    width = 14
    result_left = [
        [(11, 0, 11), (0, 11)],
        [(8, 12, 20), (0, 20)],
        [(14, 21, 35), (0, 35)]]
    result_right = [
        [(3, None), (11, 0, 11), (0, 11)],
        [(6, None), (8, 12, 20), (0, 20)],
        [(14, 21, 35), (0, 35)]]
    result_center = [
        [(2, None), (11, 0, 11), (0, 11)],
        [(3, None), (8, 12, 20), (0, 20)],
        [(14, 21, 35), (0, 35)]]


class CalcTranslateWordTest3(CalcTranslateTest, unittest.TestCase):
    def setUp(self):
        urwid.set_encoding('utf-8')

    text = B('\xe6\x9b\xbf\xe6\xb4\xbc\n\xe6\xb8\x8e\xe6\xba\x8f\xe6\xbd\xba')
    width = 10
    mode = 'space'
    result_left = [
        [(4, 0, 6), (0, 6)],
        [(6, 7, 16), (0, 16)]]
    result_right = [
        [(6, None), (4, 0, 6), (0, 6)],
        [(4, None), (6, 7, 16), (0, 16)]]
    result_center = [
        [(3, None), (4, 0, 6), (0, 6)],
        [(2, None), (6, 7, 16), (0, 16)]]


class CalcTranslateWordTest4(CalcTranslateTest, unittest.TestCase):
    text = ' Die Gedank'
    width = 3
    mode = 'space'
    result_left = [
        [(0, 0)],
        [(3, 1, 4), (0, 4)],
        [(3, 5, 8)],
        [(3, 8, 11), (0, 11)]]
    result_right = [
        [(3, None), (0, 0)],
        [(3, 1, 4), (0, 4)],
        [(3, 5, 8)],
        [(3, 8, 11), (0, 11)]]
    result_center = [
        [(2, None), (0, 0)],
        [(3, 1, 4), (0, 4)],
        [(3, 5, 8)],
        [(3, 8, 11), (0, 11)]]


class CalcTranslateWordTest5(CalcTranslateTest, unittest.TestCase):
    text = ' Word.'
    width = 3
    mode = 'space'
    result_left = [[(3, 0, 3)], [(3, 3, 6), (0, 6)]]
    result_right = [[(3, 0, 3)], [(3, 3, 6), (0, 6)]]
    result_center = [[(3, 0, 3)], [(3, 3, 6), (0, 6)]]


class CalcTranslateClipTest(CalcTranslateTest, unittest.TestCase):
    text = "It's out of control!\nYou've got to\n\nturn it off!!!"
    mode = 'clip'
    width = 14
    result_left = [
        [(20, 0, 20), (0, 20)],
        [(13, 21, 34), (0, 34)],
        [(0, 35)],
        [(14, 36, 50), (0, 50)]]
    result_right = [
        [(-6, None), (20, 0, 20), (0, 20)],
        [(1, None), (13, 21, 34), (0, 34)],
        [(14, None), (0, 35)],
        [(14, 36, 50), (0, 50)]]
    result_center = [
        [(-3, None), (20, 0, 20), (0, 20)],
        [(1, None), (13, 21, 34), (0, 34)],
        [(7, None), (0, 35)],
        [(14, 36, 50), (0, 50)]]

class CalcTranslateCantDisplayTest(CalcTranslateTest, unittest.TestCase):
    text = B('Hello\xe9\xa2\x96')
    mode = 'space'
    width = 1
    result_left = [[]]
    result_right = [[]]
    result_center = [[]]


class CalcPosTest(unittest.TestCase):
    def setUp(self):
        self.text = "A" * 27
        self.trans = [
            [(2,None),(7,0,7),(0,7)],
            [(13,8,21),(0,21)],
            [(3,None),(5,22,27),(0,27)]]
        self.mytests = [(1,0, 0), (2,0, 0), (11,0, 7),
            (-3,1, 8), (-2,1, 8), (1,1, 9), (31,1, 21),
            (1,2, 22), (11,2, 27) ]

    def tests(self):
        for x,y, expected in self.mytests:
            got = text_layout.calc_pos( self.text, self.trans, x, y )
            assert got == expected, "%r got:%r expected:%r" % ((x, y), got,
                                                               expected)


class Pos2CoordsTest(unittest.TestCase):
    pos_list = [5, 9, 20, 26]
    text = "1234567890" * 3
    mytests = [
        ( [[(15,0,15)], [(15,15,30),(0,30)]],
            [(5,0),(9,0),(5,1),(11,1)] ),
        ( [[(9,0,9)], [(12,9,21)], [(9,21,30),(0,30)]],
            [(5,0),(0,1),(11,1),(5,2)] ),
        ( [[(2,None), (15,0,15)], [(2,None), (15,15,30),(0,30)]],
            [(7,0),(11,0),(7,1),(13,1)] ),
        ( [[(3, 6, 9),(0,9)], [(5, 20, 25),(0,25)]],
            [(0,0),(3,0),(0,1),(5,1)] ),
        ( [[(10, 0, 10),(0,10)]],
            [(5,0),(9,0),(10,0),(10,0)] ),

        ]

    def test(self):
        for t, answer in self.mytests:
            for pos,a in zip(self.pos_list,answer) :
                r = text_layout.calc_coords( self.text, t, pos)
                assert r==a, "%r got: %r expected: %r"%(t,r,a)
