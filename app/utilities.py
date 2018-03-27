# Globals #


# TODO: Truncate ListBox items

import urwid
import re
import sys
from bs4 import BeautifulSoup
import requests
from queue import Queue
from subprocess import PIPE, Popen
from threading import Thread
import webbrowser

SO_URL = "https://stackoverflow.com" # TODO: Change to stackexchange

GREEN = "\033[92m"
GRAY = "\033[90m"
BLUE = "\033[36m"
RED = "\033[31m"
ENDC = "\033[0m"
UNDERLINE = "\033[4m"
BOLD = "\033[1m"


# Helpers #


class SelectableText(urwid.Text):
    def selectable(self):
        return True


    def keypress(self, size, key):
        return key


def read(pipe, funcs):
    for line in iter(pipe.readline, b""):
        for func in funcs:
            func(line.decode("utf-8"))
    pipe.close()


def write(get):
    for line in iter(get, None):
        sys.stdout.write(line)


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


def stylize(search_result):
    if search_result["Answers"] == 1:
        return "(%s Answer) %s" % (search_result["Answers"], search_result["Title"])
    else:
        return "(%s Answers) %s" % (search_result["Answers"], search_result["Title"])


def handle_input(input):
    if input == "enter": # Open link
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


def search_stackoverflow(query, page_num):
    url = SO_URL + "/search?page=%s&q=%s" % (page_num, query.replace(" ", "+"))
    html = requests.get(url)
    soup = BeautifulSoup(html.text, "lxml")

    # TODO: Randomize the user agent

    if re.search("\.com/nocaptcha", html.url):
        # IDEA: We might be able to solve the captcha with Selenium. The checkbox is in an iframe, so theoretically we could target the captcha container, switch into the iframe, target the checkbox and call .click(), and then switch back to SO.

        return (None, True, True)

    search_results = get_search_results(soup)

    # Checks if we're on the last page
    page_nav_container = soup.find_all("div", class_="pager fl")[0]
    if page_nav_container == []:
        return (search_results, True, False)
    elif page_nav_container.find_all("span", class_="page-numbers next") == []:
        return (search_results, True, False)
    else:
        return (search_results, False, False)


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


def display_first_result(result, query):
    if result["Answers"] == 1:
        answers = GREEN + "(1 Answer)" + ENDC
    elif result["Answers"] > 0 and result["Answers"] != 1:
        answers = GREEN + "(%s Answers)" + ENDC % str(result["Answers"])
    else:
        answers =  "(%s Answers)" % str(result["Answers"])

    title = "\n" + BOLD + answers + BOLD + " " + result["Title"] + ENDC + "\n"
    body = "\n" + GRAY + result["Body"].strip().replace("\n", " ").replace("\r", "").replace("\t", " ") + ENDC + "\n"

    sys.stdout.write(title)
    sys.stdout.write(body)


def display_all_results(search_results, query):
    # TODO: Turn this all into a class with only local variables instead of globals; Python more efficiently accesses local variables than globals

    global glob_search_results
    global content_container
    global palette

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
