"""
Name: Rebound
Version: 1.1.5
Author: @shobrook
Description: Command-line tool that automatically searches Stack Overflow and
displays results in your terminal when you get a compiler error.
"""


##########
## GLOBALS
##########


import urwid
import re
import sys
import os
from bs4 import BeautifulSoup
import requests
from queue import Queue
from subprocess import PIPE, Popen
from threading import Thread
import webbrowser
import time
from urwid.widget import (BOX, FLOW, FIXED)

SO_URL = "https://stackoverflow.com"

# ASCII color codes
GREEN = '\033[92m'
GRAY = '\033[90m'
CYAN = '\033[36m'
RED = '\033[31m'
YELLOW = '\033[33m'
END = '\033[0m'
UNDERLINE = '\033[4m'
BOLD = '\033[1m'

# Scroll actions
SCROLL_LINE_UP = "line up"
SCROLL_LINE_DOWN = "line down"
SCROLL_PAGE_UP = "page up"
SCROLL_PAGE_DOWN = "page down"
SCROLL_TO_TOP = "to top"
SCROLL_TO_END = "to end"

# Scrollbar positions
SCROLLBAR_LEFT = "left"
SCROLLBAR_RIGHT = "right"


##################
## FILE ATTRIBUTES
##################


def get_language(file_path):
    """Returns the language a file is written in."""
    if file_path.endswith(".py"):
        return "python"
    elif file_path.endswith(".js"):
        return "node"
    elif file_path.endswith(".rb"):
        return "ruby"
    elif file_path.endswith(".java"):
        return "javac"
    else:
        return '' # Unknown language


def get_error_message(error, language):
    """Filters the stack trace from stderr and returns only the error message."""
    if error == '':
        return None
    elif language == "python":
        if any(e in error for e in ["KeyboardInterrupt", "SystemExit", "GeneratorExit"]): # Non-compiler errors
            return None
        else:
            return error.split('\n')[-2][1:]
    elif language == "node":
        return error.split('\n')[4][1:]
    elif language == "ruby":
        return # TODO
    elif language == "java":
        return # TODO


#################
## FILE EXECUTION
#################


## Helper Functions ##


def read(pipe, funcs):
    """Reads and pushes piped output to a shared queue and appropriate lists."""
    for line in iter(pipe.readline, b''):
        for func in funcs:
            func(line.decode("utf-8"))
    pipe.close()


def write(get):
    """Pulls output from shared queue and prints to terminal."""
    for line in iter(get, None):
        sys.stdout.write(line)


## Main ##


def execute(command):
    """Executes a given command and clones stdout/err to both variables and the
    terminal (in real-time)."""
    process = Popen(
        command,
        cwd=None,
        shell=False,
        close_fds=True,
        stdout=PIPE,
        stderr=PIPE,
        bufsize=1
    )

    output, errors = [], []
    pipe_queue = Queue() # Wowee, thanks CS 225

    # Threads for reading stdout and stderr pipes and pushing to a shared queue
    stdout_thread = Thread(target=read, args=(process.stdout, [pipe_queue.put, output.append]))
    stderr_thread = Thread(target=read, args=(process.stderr, [pipe_queue.put, errors.append]))

    writer_thread = Thread(target=write, args=(pipe_queue.get,)) # Thread for printing items in the queue

    # Spawns each thread
    for thread in (stdout_thread, stderr_thread, writer_thread):
        thread.daemon = True
        thread.start()

    process.wait()

    for thread in (stdout_thread, stderr_thread):
        thread.join()

    pipe_queue.put(None)

    output = ' '.join(output)
    errors = ' '.join(errors)

    if not os.path.isfile(command[1]): # File doesn't exist
        return (None, None)
    else:
        return (output, errors)


###############
## WEB SCRAPING
###############


## Helper Functions ##


def stylize_code(soup):
    """Identifies and stylizes code in a question or answer."""
    # TODO: Handle blockquotes and markdown
    stylized_text = []
    code_blocks = [block.get_text() for block in soup.find_all("code")]
    blockquotes = [block.get_text() for block in soup.find_all("blockquote")]
    newline = False

    for child in soup.recursiveChildGenerator():
        name = getattr(child, "name", None)

        if name is None: # Leaf (terminal) node
            if child in code_blocks:
                if newline: # Code block
                    #if code_blocks.index(child) == len(code_blocks) - 1: # Last code block
                        #child = child[:-1]
                    stylized_text.append(("code", u"\n%s" % str(child)))
                    newline = False
                else: # In-line code
                    stylized_text.append(("code", u"%s" % str(child)))
            else: # Plaintext
                newline = child.endswith('\n')
                stylized_text.append(u"%s" % str(child))

    if type(stylized_text[-2]) == tuple:
        # Remove newline from questions/answers that end with a code block
        if stylized_text[-2][1].endswith('\n'):
            stylized_text[-2] = ("code", stylized_text[-2][1][:-1])

    return urwid.Text(stylized_text)


def get_search_results(soup):
    """Returns a list of dictionaries containing each search result."""
    search_results = []

    for result in soup.find_all("div", class_="question-summary search-result"):
        title_container = result.find_all("div", class_="result-link")[0].find_all("span")[0].find_all("a")[0]

        if result.find_all("div", class_="status answered") != []: # Has answers
            answer_count = int(result.find_all("div", class_="status answered")[0].find_all("strong")[0].text)
        elif result.find_all("div", class_="status answered-accepted") != []: # Has an accepted answer (closed)
            answer_count = int(result.find_all("div", class_="status answered-accepted")[0].find_all("strong")[0].text)
        else: # No answers
            answer_count = 0

        search_results.append({
            "Title": title_container["title"],
            #"Body": result.find_all("div", class_="excerpt")[0].text,
            #"Votes": int(result.find_all("span", class_="vote-count-post ")[0].find_all("strong")[0].text),
            "Answers": answer_count,
            "URL": SO_URL + title_container["href"]
        })

    return search_results


def souper(url):
    """Turns a given URL into a BeautifulSoup object."""
    html = requests.get(url)

    if re.search("\.com/nocaptcha", html.url): # URL is a captcha page
        return None
    else:
        return BeautifulSoup(html.text, "html.parser")


## Main ##


def search_stackoverflow(query):
    """Wrapper function for get_search_results."""
    soup = souper(SO_URL + "/search?pagesize=50&q=%s" % query.replace(' ', '+'))

    # TODO: Randomize the user agent

    if soup == None:
        return (None, True)
    else:
        return (get_search_results(soup), False)


def get_question_and_answers(url):
    """Returns details about a given question and list of its answers."""
    soup = souper(url)

    if soup == None: # Captcha page
        return "Sorry, Stack Overflow blocked our request. Try again in a couple seconds.", "", "", ""
    else:
        question_title = soup.find_all('a', class_="question-hyperlink")[0].get_text()
        question_stats = soup.find_all("span", class_="vote-count-post")[0].get_text() # Vote count

        try:
            question_stats = question_stats + " Votes | " + '|'.join((((soup.find_all("div", class_="module question-stats")[0].get_text())
                .replace('\n', ' ')).replace("     ", " | ")).split('|')[:2]) # Vote count, submission date, view count
        except IndexError:
            question_stats = "Could not load statistics."

        question_desc = stylize_code(soup.find_all("div", class_="post-text")[0]) # TODO: Handle duplicates
        question_stats = ' '.join(question_stats.split())

        answers = [stylize_code(answer) for answer in soup.find_all("div", class_="post-text")][1:]
        if len(answers) == 0:
            answers.append(urwid.Text(("no answers", u"\nNo answers for this question.")))

        return question_title, question_desc, question_stats, answers


############
## INTERFACE
############


## Helper Classes ##


class Scrollable(urwid.WidgetDecoration):
    # TODO: Fix scrolling behavior (works with up/down keys, not with cursor)

    def sizing(self):
        return frozenset([BOX,])


    def selectable(self):
        return True


    def __init__(self, widget):
        """Box widget (wrapper) that makes a fixed or flow widget vertically scrollable."""
        self._trim_top = 0
        self._scroll_action = None
        self._forward_keypress = None
        self._old_cursor_coords = None
        self._rows_max_cached = 0
        self.__super.__init__(widget)


    def render(self, size, focus=False):
        maxcol, maxrow = size

        # Render complete original widget
        ow = self._original_widget
        ow_size = self._get_original_widget_size(size)
        canv = urwid.CompositeCanvas(ow.render(ow_size, focus))
        canv_cols, canv_rows = canv.cols(), canv.rows()

        if canv_cols <= maxcol:
            pad_width = maxcol - canv_cols
            if pad_width > 0: # Canvas is narrower than available horizontal space
                canv.pad_trim_left_right(0, pad_width)

        if canv_rows <= maxrow:
            fill_height = maxrow - canv_rows
            if fill_height > 0: # Canvas is lower than available vertical space
                canv.pad_trim_top_bottom(0, fill_height)

        if canv_cols <= maxcol and canv_rows <= maxrow: # Canvas is small enough to fit without trimming
            return canv

        self._adjust_trim_top(canv, size)

        # Trim canvas if necessary
        trim_top = self._trim_top
        trim_end = canv_rows - maxrow - trim_top
        trim_right = canv_cols - maxcol
        if trim_top > 0:
            canv.trim(trim_top)
        if trim_end > 0:
            canv.trim_end(trim_end)
        if trim_right > 0:
            canv.pad_trim_left_right(0, -trim_right)

        # Disable cursor display if cursor is outside of visible canvas parts
        if canv.cursor is not None:
            curscol, cursrow = canv.cursor
            if cursrow >= maxrow or cursrow < 0:
                canv.cursor = None

        # Let keypress() know if original_widget should get keys
        self._forward_keypress = bool(canv.cursor)

        return canv


    def keypress(self, size, key):
        if self._forward_keypress:
            ow = self._original_widget
            ow_size = self._get_original_widget_size(size)

            # Remember previous cursor position if possible
            if hasattr(ow, "get_cursor_coords"):
                self._old_cursor_coords = ow.get_cursor_coords(ow_size)

            key = ow.keypress(ow_size, key)
            if key is None:
                return None

        # Handle up/down, page up/down, etc
        command_map = self._command_map
        if command_map[key] == urwid.CURSOR_UP:
            self._scroll_action = SCROLL_LINE_UP
        elif command_map[key] == urwid.CURSOR_DOWN:
            self._scroll_action = SCROLL_LINE_DOWN
        elif command_map[key] == urwid.CURSOR_PAGE_UP:
            self._scroll_action = SCROLL_PAGE_UP
        elif command_map[key] == urwid.CURSOR_PAGE_DOWN:
            self._scroll_action = SCROLL_PAGE_DOWN
        elif command_map[key] == urwid.CURSOR_MAX_LEFT: # "home"
            self._scroll_action = SCROLL_TO_TOP
        elif command_map[key] == urwid.CURSOR_MAX_RIGHT: # "end"
            self._scroll_action = SCROLL_TO_END
        else:
            return key

        self._invalidate()


    def mouse_event(self, size, event, button, col, row, focus):
        ow = self._original_widget
        if hasattr(ow, "mouse_event"):
            ow_size = self._get_original_widget_size(size)
            row += self._trim_top
            return ow.mouse_event(ow_size, event, button, col, row, focus)
        else:
            return False


    def _adjust_trim_top(self, canv, size):
        """Adjust self._trim_top according to self._scroll_action"""
        action = self._scroll_action
        self._scroll_action = None

        maxcol, maxrow = size
        trim_top = self._trim_top
        canv_rows = canv.rows()

        if trim_top < 0:
            # Negative trim_top values use bottom of canvas as reference
            trim_top = canv_rows - maxrow + trim_top + 1

        if canv_rows <= maxrow:
            self._trim_top = 0  # Reset scroll position
            return

        def ensure_bounds(new_trim_top):
            return max(0, min(canv_rows - maxrow, new_trim_top))

        if action == SCROLL_LINE_UP:
            self._trim_top = ensure_bounds(trim_top - 1)
        elif action == SCROLL_LINE_DOWN:
            self._trim_top = ensure_bounds(trim_top + 1)
        elif action == SCROLL_PAGE_UP:
            self._trim_top = ensure_bounds(trim_top - maxrow+1)
        elif action == SCROLL_PAGE_DOWN:
            self._trim_top = ensure_bounds(trim_top + maxrow-1)
        elif action == SCROLL_TO_TOP:
            self._trim_top = 0
        elif action == SCROLL_TO_END:
            self._trim_top = canv_rows - maxrow
        else:
            self._trim_top = ensure_bounds(trim_top)

        if self._old_cursor_coords is not None and self._old_cursor_coords != canv.cursor:
            self._old_cursor_coords = None
            curscol, cursrow = canv.cursor
            if cursrow < self._trim_top:
                self._trim_top = cursrow
            elif cursrow >= self._trim_top + maxrow:
                self._trim_top = max(0, cursrow - maxrow + 1)


    def _get_original_widget_size(self, size):
        ow = self._original_widget
        sizing = ow.sizing()
        if FIXED in sizing:
            return ()
        elif FLOW in sizing:
            return (size[0],)


    def get_scrollpos(self, size=None, focus=False):
        return self._trim_top


    def set_scrollpos(self, position):
        self._trim_top = int(position)
        self._invalidate()


    def rows_max(self, size=None, focus=False):
        if size is not None:
            ow = self._original_widget
            ow_size = self._get_original_widget_size(size)
            sizing = ow.sizing()
            if FIXED in sizing:
                self._rows_max_cached = ow.pack(ow_size, focus)[1]
            elif FLOW in sizing:
                self._rows_max_cached = ow.rows(ow_size, focus)
            else:
                raise RuntimeError("Not a flow/box widget: %r" % self._original_widget)
        return self._rows_max_cached


class ScrollBar(urwid.WidgetDecoration):
    # TODO: Change scrollbar size and color(?)

    def sizing(self):
        return frozenset((BOX,))


    def selectable(self):
        return True


    def __init__(self, widget, thumb_char=u'\u2588', trough_char=' ',
                 side=SCROLLBAR_RIGHT, width=1):
        """Box widget that adds a scrollbar to `widget`."""
        self.__super.__init__(widget)
        self._thumb_char = thumb_char
        self._trough_char = trough_char
        self.scrollbar_side = side
        self.scrollbar_width = max(1, width)
        self._original_widget_size = (0, 0)


    def render(self, size, focus=False):
        maxcol, maxrow = size

        ow = self._original_widget
        ow_base = self.scrolling_base_widget
        ow_rows_max = ow_base.rows_max(size, focus)
        if ow_rows_max <= maxrow: # Canvas fits without scrolling - no scrollbar needed
            self._original_widget_size = size
            return ow.render(size, focus)

        sb_width = self._scrollbar_width
        self._original_widget_size = ow_size = (maxcol-sb_width, maxrow)
        ow_canv = ow.render(ow_size, focus)

        pos = ow_base.get_scrollpos(ow_size, focus)
        posmax = ow_rows_max - maxrow

        # Thumb shrinks/grows according to the ratio of
        # <number of visible lines> / <number of total lines>
        thumb_weight = min(1, maxrow / max(1, ow_rows_max))
        thumb_height = max(1, round(thumb_weight * maxrow))

        # Thumb may only touch top/bottom if the first/last row is visible
        top_weight = float(pos) / max(1, posmax)
        top_height = int((maxrow-thumb_height) * top_weight)
        if top_height == 0 and top_weight > 0:
            top_height = 1

        # Bottom part is remaining space
        bottom_height = maxrow - thumb_height - top_height
        assert thumb_height + top_height + bottom_height == maxrow

        # Create scrollbar canvas
        top = urwid.SolidCanvas(self._trough_char, sb_width, top_height)
        thumb = urwid.SolidCanvas(self._thumb_char, sb_width, thumb_height)
        bottom = urwid.SolidCanvas(self._trough_char, sb_width, bottom_height)
        sb_canv = urwid.CanvasCombine([
            (top, None, False),
            (thumb, None, False),
            (bottom, None, False),
        ])

        combinelist = [(ow_canv, None, True, ow_size[0]), (sb_canv, None, False, sb_width)]
        if self._scrollbar_side != SCROLLBAR_LEFT:
            return urwid.CanvasJoin(combinelist)
        else:
            return urwid.CanvasJoin(reversed(combinelist))


    @property
    def scrollbar_width(self):
        return max(1, self._scrollbar_width)


    @scrollbar_width.setter
    def scrollbar_width(self, width):
        self._scrollbar_width = max(1, int(width))
        self._invalidate()


    @property
    def scrollbar_side(self):
        return self._scrollbar_side


    @scrollbar_side.setter
    def scrollbar_side(self, side):
        if side not in (SCROLLBAR_LEFT, SCROLLBAR_RIGHT):
            raise ValueError("scrollbar_side must be 'left' or 'right', not %r" % side)
        self._scrollbar_side = side
        self._invalidate()


    @property
    def scrolling_base_widget(self):
        """Nearest `base_widget` that is compatible with the scrolling API."""
        def orig_iter(w):
            while hasattr(w, "original_widget"):
                w = w.original_widget
                yield w
            yield w

        def is_scrolling_widget(w):
            return hasattr(w, "get_scrollpos") and hasattr(w, "rows_max")

        for w in orig_iter(self):
            if is_scrolling_widget(w):
                return w


    def keypress(self, size, key):
        return self._original_widget.keypress(self._original_widget_size, key)


    def mouse_event(self, size, event, button, col, row, focus):
        ow = self._original_widget
        ow_size = self._original_widget_size
        handled = False
        if hasattr(ow, "mouse_event"):
            handled = ow.mouse_event(ow_size, event, button, col, row, focus)

        if not handled and hasattr(ow, "set_scrollpos"):
            if button == 4: # Scroll wheel up
                pos = ow.get_scrollpos(ow_size)
                ow.set_scrollpos(pos - 1)
                return True
            elif button == 5: # Scroll wheel down
                pos = ow.get_scrollpos(ow_size)
                ow.set_scrollpos(pos + 1)
                return True

        return False


class SelectableText(urwid.Text):
    def selectable(self):
        return True


    def keypress(self, size, key):
        return key


## Helper Functions ##


def interleave(a, b):
    result = []
    while a and b:
        result.append(a.pop(0))
        result.append(b.pop(0))

    result.extend(a)
    result.extend(b)

    return result


## Main ##


class App(object):
    def __init__(self, search_results):
        self.search_results, self.viewing_answers = search_results, False
        self.palette = [
            ("title", "light cyan,bold", "default", "standout"),
            ("stats", "light green", "default", "standout"),
            ("menu", "black", "light cyan", "standout"),
            ("reveal focus", "black", "light cyan", "standout"),
            ("no answers", "light red", "default", "standout"),
            ("code", "brown", "default", "standout")
        ]
        self.menu = urwid.Text([
            u'\n',
            ("menu", u" ENTER "), ("light gray", u" View answers "),
            ("menu", u" B "), ("light gray", u" Open browser "),
            ("menu", u" Q "), ("light gray", u" Quit"),
        ])

        results = list(map(lambda result: urwid.AttrMap(SelectableText(self._stylize_title(result)), None, "reveal focus"), self.search_results)) # TODO: Add a wrap='clip' attribute
        content = urwid.SimpleListWalker(results)
        self.content_container = urwid.ListBox(content)
        layout = urwid.Frame(body=self.content_container, footer=self.menu)

        self.main_loop = urwid.MainLoop(layout, self.palette, unhandled_input=self._handle_input)
        self.original_widget = self.main_loop.widget

        self.main_loop.run()


    def _handle_input(self, input):
        if input == "enter": # View answers
            url = self._get_selected_link()

            if url != None:
                self.viewing_answers = True
                question_title, question_desc, question_stats, answers = get_question_and_answers(url)

                pile = urwid.Pile(self._stylize_question(question_title, question_desc, question_stats) + [urwid.Divider('*')] +
                interleave(answers, [urwid.Divider('-')] * (len(answers) - 1)))
                padding = urwid.Padding(ScrollBar(Scrollable(pile)), left=2, right=2)
                #filler = urwid.Filler(padding, valign="top")
                linebox = urwid.LineBox(padding)

                menu = urwid.Text([
                    u'\n',
                    ("menu", u" ESC "), ("light gray", u" Go back "),
                    ("menu", u" B "), ("light gray", u" Open browser "),
                    ("menu", u" Q "), ("light gray", u" Quit"),
                ])

                self.main_loop.widget = urwid.Frame(body=urwid.Overlay(linebox, self.content_container, "center", 85, "middle", 23), footer=menu)
        elif input in ('b', 'B'): # Open link
            url = self._get_selected_link()

            if url != None:
                webbrowser.open(url)
        elif input == "esc": # Close window
            if self.viewing_answers:
                self.main_loop.widget = self.original_widget
                self.viewing_answers = False
            else:
                raise urwid.ExitMainLoop()
        elif input in ('q', 'Q'): # Quit
            raise urwid.ExitMainLoop()


    def _get_selected_link(self):
        focus_widget, idx = self.content_container.get_focus() # Gets selected item
        title = focus_widget.base_widget.text

        for result in self.search_results:
            if title == self._stylize_title(result): # Found selected title's search_result dict
                return result["URL"]


    def _stylize_title(self, search_result):
        if search_result["Answers"] == 1:
            return "%s (1 Answer)" % search_result["Title"]
        else:
            return "%s (%s Answers)" % (search_result["Title"], search_result["Answers"])


    def _stylize_question(self, title, desc, stats):
        new_title = urwid.Text(("title", u"%s" % title))
        new_stats = urwid.Text(("stats", u"%s\n" % stats))

        return [new_title, desc, new_stats]


#######
## MAIN
#######


## Helper Functions ##


def confirm(question):
    """Prompts a given question and handles user input."""
    valid = {"yes": True, 'y': True, "ye": True,
             "no": False, 'n': False, '': True}
    prompt = " [Y/n] "

    while True:
        sys.stdout.write(BOLD + CYAN + question + prompt + END)
        choice = input().lower()
        if choice in valid:
            return valid[choice]

        sys.stdout.write("Please respond with 'yes' or 'no' (or 'y' or 'n').\n")


def print_help():
    """Prints usage instructions."""
    sys.stdout.write("%sRebound, V1.1.5a1 - Made by @shobrook%s\n" % (BOLD, END))
    sys.stdout.write("Command-line tool that automatically searches Stack Overflow and displays results in your terminal when you get a compiler error.")
    sys.stdout.write("\n\n%sUsage:%s $ rebound %s[file_name]%s\n" % (UNDERLINE, END, YELLOW, END))
    sys.stdout.write("\n$ python %stest.py%s   =>   $ rebound %stest.py%s" % (YELLOW, END, YELLOW, END))
    sys.stdout.write("\n$ node %stest.js%s     =>   $ rebound %stest.js%s\n\n" % (YELLOW, END, YELLOW, END))


## Main ##


def main():
    if len(sys.argv) == 1:
        print_help()
    elif sys.argv[1].lower() == "-h" or sys.argv[1].lower() == "--help":
        print_help()
    else:
        language = get_language(sys.argv[1].lower()) # Gets the language name
        if language == '': # Unknown language
            sys.stdout.write("\n%s%s%s" % (RED, "Sorry, Rebound doesn't support this file type.\n", END))
            return

        output, error = execute([language] + sys.argv[1:]) # Compiles the file and pipes stdout
        if (output, error) == (None, None): # Invalid file
            return

        error_msg = get_error_message(error, language) # Prepares error message for search
        if error_msg != None:
            query = "%s %s" % (language, error_msg)
            search_results, captcha = search_stackoverflow(query)

            if search_results != []:
                if captcha:
                    sys.stdout.write("\n%s%s%s" % (RED, "Sorry, Stack Overflow blocked our request. Try again in a minute.\n", END))
                    return
                elif confirm("\nDisplay Stack Overflow results?"):
                    App(search_results) # Opens interface
            else:
                sys.stdout.write("\n%s%s%s" % (RED, "No Stack Overflow results found.\n", END))
        else:
            sys.stdout.write("\n%s%s%s" % (CYAN, "No error detected :)\n", END))

    return


if __name__ == "__main__":
    main()
