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

SO_URL = "https://stackoverflow.com" # TODO: Change to stackexchange

GREEN = "\033[92m"
GRAY = "\033[90m"
BLUE = "\033[36m"
RED = "\033[31m"
ENDC = "\033[0m"
UNDERLINE = "\033[4m"
BOLD = "\033[1m"


## File Execution ##


# Helper Functions #


def read(pipe, funcs):
    for line in iter(pipe.readline, b""):
        for func in funcs:
            func(line.decode("utf-8"))
    pipe.close()


def write(get):
    for line in iter(get, None):
        sys.stdout.write(line)


# Main #


def execute(command):
    process = Popen(command, cwd=None, shell=False, close_fds=True, stdout=PIPE, stderr=PIPE, bufsize=1)

    output, errors = [], []
    queue = Queue()

    stdout_thread = Thread(target=read, args=(process.stdout, [queue.put, output.append]))
    stderr_thread = Thread(target=read, args=(process.stderr, [queue.put, errors.append]))
    writer_thread = Thread(target=write, args=(queue.get,))

    for thread in (stdout_thread, stderr_thread, writer_thread):
        thread.daemon = True
        thread.start()

    process.wait()

    for thread in (stdout_thread, stderr_thread):
        thread.join()

    queue.put(None)

    output = " ".join(output)
    errors = " ".join(errors)

    return (output, errors)


## File Attributes ##


def get_language(file_path):
    if ".py" in file_path:
        return "python"
    elif ".js" in file_path:
        return "javascript"
    elif ".rb" in file_path:
        return "ruby"
    elif ".java" in file_path:
        return "java"
    else:
        return "" # Unknown language


def get_error_message(error, language):
    if error == "" or language == "":
        return None
    elif language == "python":
        if any(e in error for e in ["KeyboardInterrupt", "SystemExit", "GeneratorExit"]):
            return None
        else:
            return error.split("\n")[-2][1:]
    elif language == "javascript":
        return error.split("\n")[4][1:]
    elif language == "ruby":
        return
    elif language == "java":
        return


## Stack Overflow Scraper ##


# Helper Functions #


def get_search_results(soup):
    search_results = []

    search_results_container = soup.find_all("div", class_="search-results js-search-results")[0]
    for search_result in search_results_container.find_all("div", class_="question-summary search-result"):
        title_container = search_result.find_all("div", class_="result-link")[0].find_all("span")[0].find_all("a")[0]

        title = title_container["title"]
        body = search_result.find_all("div", class_="excerpt")[0].text
        url = SO_URL + title_container["href"]
        votes = int(search_result.find_all("span", class_="vote-count-post ")[0].find_all("strong")[0].text)

        if search_result.find_all("div", class_="status answered") != []:
            answers = int(search_result.find_all("div", class_="status answered")[0].find_all("strong")[0].text)
        elif search_result.find_all("div", class_="status unanswered") != []:
            answers = int(search_result.find_all("div", class_="status unanswered")[0].find_all("strong")[0].text)
        elif search_result.find_all("div", class_="status answered-accepted") != []:
            answers = int(search_result.find_all("div", class_="status answered-accepted")[0].find_all("strong")[0].text)
        else:
            answers = 0

        search_results.append({"Title": title, "Body": body, "URL": url, "Votes": votes, "Answers": answers})

    return search_results


def souper(url):
    html = requests.get(url)

    if re.search("\.com/nocaptcha", html.url):
        # IDEA: We might be able to solve the captcha with Selenium. The checkbox is in an iframe, so theoretically we could target the captcha container, switch into the iframe, target the checkbox and call .click(), and then switch back to SO.
        return None
    else:
        return BeautifulSoup(html.text, "html.parser")


"""
def add_urls(tags):
    images = tags.find_all("a")

    for image in images:
        if hasattr(image, "href"):
            image.string = "{} [{}]".format(image.text, image['href'])
"""


# Main #


def search_stackoverflow(query):
    soup = souper(SO_URL + "/search?page=1&q=%s" % query.replace(" ", "+"))

    # TODO: Randomize the user agent

    if soup == None:
        return (None, True)

    search_results = get_search_results(soup)

    # Checks if we're on the last page
    page_nav_container = soup.find_all("div", class_="pager fl")[0]
    if page_nav_container == []:
        return (search_results, False)
    elif page_nav_container.find_all("span", class_="page-numbers next") == []:
        return (search_results, False)
    else:
        time.sleep(2)
        soup = souper(SO_URL + "/search?page=2&q=%s" % query.replace(" ", "+"))

        if soup == None:
            return (search_results, True)
        else:
            return (search_results + get_search_results(soup), False)


def get_question_and_answers(url):
    soup = souper(url)

    question_title = soup.find_all("a", class_="question-hyperlink")[0].get_text()
    question_stats = soup.find_all("span", class_="vote-count-post")[0].get_text()

    try:
        question_stats = "Votes " + question_stats + " | " + (((soup.find_all("div", class_="module question-stats")[0].get_text()).replace("\n", " ")).replace("     "," | "))
    except IndexError:
        question_stats = "Could not load statistics."

    question_desc = (soup.find_all("div", class_="post-text")[0]).get_text() # TODO: Implement add_urls
    question_stats = ' '.join(question_stats.split())

    answers = [urwid.Text(answer.get_text()) for answer in soup.find_all("div", class_="post-text")][1:]
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
        return "(%s Answer) %s" % (search_result["Answers"], search_result["Title"])
    else:
        return "(%s Answers) %s" % (search_result["Answers"], search_result["Title"])


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
                    (('black', 'dark cyan', 'standout'), u' O '), ('light gray', u" Open link "),
                    (('black', 'dark cyan', 'standout'), u' B '), ('light gray', u" Back"),
                ])

                frame = urwid.Frame(body=answer_pile, header=question, footer=menu)

                #text = urwid.Text(answers[0])
                #filler = urwid.Filler(text, valign="top")
                #padding = urwid.Padding(filler, left=5, right=5)
                #linebox = urwid.LineBox(padding)

                main_loop.widget = urwid.Overlay(frame, layout, "center", 100, "middle", 50)
    elif input in ('o', 'O'): # Open link
        focus_widget, idx = content_container.get_focus()
        title = focus_widget.base_widget.text

        for result in glob_search_results:
            if title == stylize(result):
                webbrowser.open(result["URL"])
                break

        raise urwid.ExitMainLoop()
    elif input in ('q', 'Q'): # Quit
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
      ('menu', 'black', 'dark cyan', 'standout'),
      ('reveal focus', 'black', 'dark cyan', 'standout')]
    menu = urwid.Text([
        u'\n',
        ('menu', u' ENTER '), ('light gray', u" Open link "),
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
        sys.stdout.write(BOLD + BLUE + question + prompt + ENDC)
        choice = input().lower()
        if choice in valid:
            return valid[choice]

        sys.stdout.write("Please respond with 'yes' or 'no' (or 'y' or 'n').\n")
