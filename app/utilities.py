## Globals ##


import urwid
import re
import sys
from bs4 import BeautifulSoup
import requests
from queue import Queue
from subprocess import PIPE, Popen
from threading import Thread
import webbrowser
import time

SO_URL = "https://stackoverflow.com" # QUESTION: Use Stack Overflow or Stack Exchange?

GREEN = '\033[92m'
GRAY = '\033[90m'
CYAN = '\033[36m'
RED = '\033[31m'
END = '\033[0m'
UNDERLINE = '\033[4m'
BOLD = '\033[1m'


## File Execution ##


# Helper Functions #


def read(pipe, funcs):
    """Reads piped output to a queue and list."""
    for line in iter(pipe.readline, b''):
        for func in funcs:
            func(line.decode("utf-8"))
    pipe.close()


def write(get):
    """Prints output to terminal."""
    for line in iter(get, None):
        sys.stdout.write(line)


# Main #


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
    pipe_queue = Queue()

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

    return (output, errors)


## File Attributes ##


def get_language(file_path):
    """Returns the language a file is written in."""
    if ".py" in file_path:
        return "python"
    elif ".js" in file_path:
        return "node"
    elif ".rb" in file_path:
        return "ruby"
    elif ".java" in file_path:
        return "java"
    else:
        return "" # Unknown language


def get_error_message(error, language):
    """Filters the traceback from stderr and returns only the error message."""
    if error == "" or language == "":
        return None
    elif language == "python":
        if any(e in error for e in ["KeyboardInterrupt", "SystemExit", "GeneratorExit"]): # Non-compiler errors
            return None
        else:
            return error.split("\n")[-2][1:]
    elif language == "node":
        return error.split("\n")[4][1:]
    elif language == "ruby":
        return # TODO
    elif language == "java":
        return # TODO


## Stack Overflow Scraper ##


# Helper Functions #


def get_search_results(soup):
    """Returns a list of dictionaries containing each search result."""
    search_results = []

    search_results_container = soup.find_all("div", class_="search-results js-search-results")[0]
    for result in search_results_container.find_all("div", class_="question-summary search-result"):
        title_container = result.find_all("div", class_="result-link")[0].find_all("span")[0].find_all("a")[0]

        title = title_container["title"]
        body = result.find_all("div", class_="excerpt")[0].text
        votes = int(result.find_all("span", class_="vote-count-post ")[0].find_all("strong")[0].text)

        # Handles cases for answered, unanswered, and closed questions
        if result.find_all("div", class_="status answered") != []:
            answers = int(result.find_all("div", class_="status answered")[0].find_all("strong")[0].text)
        elif result.find_all("div", class_="status unanswered") != []:
            answers = int(result.find_all("div", class_="status unanswered")[0].find_all("strong")[0].text)
        elif result.find_all("div", class_="status answered-accepted") != []:
            answers = int(result.find_all("div", class_="status answered-accepted")[0].find_all("strong")[0].text)
        else:
            answers = 0

        search_results.append({"Title": title, "Body": body, "Votes": votes, "Answers": answers, "URL": SO_URL + title_container["href"]})

    return search_results


def souper(url):
    """Turns a given URL into a BeautifulSoup object."""
    html = requests.get(url)

    if re.search("\.com/nocaptcha", html.url): # Return None if the URL is a captcha page
        # IDEA: Solve the captcha with Selenium. The checkbox is in an iframe, so (theoretically) we could target the captcha container, switch into the iframe, target the checkbox and call .click(), and then switch back to SO
        return None
    else:
        return BeautifulSoup(html.text, "html.parser")


# Main #


def search_stackoverflow(query):
    """Wrapper function for get_search_results."""
    soup = souper(SO_URL + "/search?pagesize=50&q=%s" % query.replace(" ", "+"))

    # TODO: Randomize the user agent

    if soup == None:
        return (None, True)
    else:
        return (get_search_results(soup), False)


def get_question_and_answers(url):
    """Returns details about a given question and list of its answers."""
    soup = souper(url)

    question_title = soup.find_all("a", class_="question-hyperlink")[0].get_text()
    question_stats = soup.find_all("span", class_="vote-count-post")[0].get_text() # No. of votes

    try:
        # Votes, submission date, view count, date of last activity
        question_stats = question_stats + " Votes | " + (((soup.find_all("div", class_="module question-stats")[0].get_text()).replace("\n", " ")).replace("     "," | "))
    except IndexError:
        question_stats = "Could not load statistics."

    question_desc = (soup.find_all("div", class_="post-text")[0]).get_text()
    question_stats = ' '.join(question_stats.split())

    answers = [answer.get_text() for answer in soup.find_all("div", class_="post-text")][1:]
    if len(answers) == 0:
        answers.append(urwid.Text("No answers for this question."))

    return question_title, question_desc, question_stats, answers


## Interface ##


# Helper Classes #


class SelectableText(urwid.Text):
    def selectable(self):
        return True


    def keypress(self, size, key):
        return key


# Helper Functions #


def stylize(search_result):
    if search_result["Answers"] == 1:
        return "%s Answer | %s" % (search_result["Answers"], search_result["Title"])
    else:
        return "%s Answers | %s" % (search_result["Answers"], search_result["Title"])


def handle_input(input):
    if input == "enter": # Open question
        focus_widget, idx = content_container.get_focus()
        title = focus_widget.base_widget.text

        for result in glob_search_results:
            if title == stylize(result):
                question_title, question_desc, question_stats, answers = get_question_and_answers(result["URL"])

                question = urwid.Text(question_desc)
                answer_pile = urwid.Pile([urwid.Text("test"), urwid.Text("anothertest")])
                menu = urwid.Text([
                    u'\n',
                    (("black", "dark cyan", "standout"), u' O '), ("light gray", u" Open link "),
                    (("black", "dark cyan", "standout"), u' B '), ("light gray", u" Back"),
                ])

                frame = urwid.Frame(body=answer_pile, header=question, footer=menu)

                #text = urwid.Text(answers[0])
                #filler = urwid.Filler(text, valign="top")
                #padding = urwid.Padding(filler, left=5, right=5)
                #linebox = urwid.LineBox(padding)

                main_loop.widget = urwid.Overlay(frame, layout, "center", 100, "middle", 50)
    elif input == ' ': # Open link
        focus_widget, idx = content_container.get_focus()
        title = focus_widget.base_widget.text

        for result in glob_search_results:
            if title == stylize(result):
                webbrowser.open(result["URL"])
                break

        raise urwid.ExitMainLoop()
    elif input in ('q', 'Q') or "esc": # Quit
        raise urwid.ExitMainLoop()


# Main #


def display_all_results(search_results, query):
    # TODO: Turn this all into a class with only local variables instead of globals; Python more efficiently accesses local variables than globals
    # TODO: Truncate ListBox items

    global glob_search_results
    global content_container
    global palette
    global layout
    global main_loop

    palette = [
      ('menu', 'black', 'light cyan', 'standout'),
      ('reveal focus', 'black', 'light cyan', 'standout')]
    menu = urwid.Text([
        u'\n',
        ('menu', u' ENTER '), ('light gray', u" View answers "),
        ('menu', u' SPACE '), ('light gray', u" Open link "),
        ('menu', u' Q '), ('light gray', u" Quit"),
    ])

    glob_search_results = search_results.copy()

    results = list(map(lambda result: urwid.AttrMap(SelectableText(stylize(result)), None, "reveal focus"), search_results))
    content = urwid.SimpleListWalker(results)
    #content_container = urwid.Filler(urwid.ListBox(content), valign="top", top=1, bottom=1)
    content_container = urwid.ListBox(content)

    layout = urwid.Frame(body=content_container, footer=menu)

    main_loop = urwid.MainLoop(layout, palette, unhandled_input=handle_input)
    main_loop.run()


## Miscellaneous ##


def confirm(question):
    valid = {"yes": True, "y": True, "ye": True,
             "no": False, "n": False, "": True}
    prompt = " [Y/n] "

    while True:
        sys.stdout.write(BOLD + CYAN + question + prompt + END)
        choice = input().lower()
        if choice in valid:
            return valid[choice]

        sys.stdout.write("Please respond with 'yes' or 'no' (or 'y' or 'n').\n")
