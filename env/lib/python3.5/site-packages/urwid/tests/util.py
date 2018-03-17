import urwid

class SelectableText(urwid.Text):
    def selectable(self):
        return 1

    def keypress(self, size, key):
        return key
