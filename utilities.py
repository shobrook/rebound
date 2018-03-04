# Globals #


import sys
from bs4 import BeautifulSoup
import requests
from queue import Queue
from subprocess import PIPE, Popen
from threading import Thread

SO_URL = "https://stackoverflow.com"


# Helpers #


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


# Main #


def execute(command):
    process = Popen(command.split(), cwd=None, shell=False, close_fds=True, stdout=PIPE, stderr=PIPE, bufsize=1)

    outs, errs = [], []
    queue = Queue()

    stdout_thread = Thread(target=read, args=(process.stdout, [queue.put, outs.append]))
    stderr_thread = Thread(target=read, args=(process.stderr, [queue.put, errs.append]))
    writer_thread = Thread(target=write, args=(queue.get,))

    for thread in (stdout_thread, stderr_thread, writer_thread):
        thread.daemon = True
        thread.start()

    process.wait()

    for thread in (stdout_thread, stderr_thread):
        thread.join()

    queue.put(None)

    outs = " ".join(outs)
    errs = " ".join(errs)

    """
    outs, errs = process.communicate()
    outs = "" if outs == None else outs.decode("utf-8")
    errs = "" if errs == None else errs.decode("utf-8")
    """

    return (outs, errs)


def get_language(command):
    """Parses the command """
    if "python" in command.lower():
        return "python"
    elif "ruby" in command.lower():
        return "ruby"
    elif "java" or "javac" in command.lower():
        return "java"
    elif "make" or ".cpp" in command.lower():
        return "c++"
    elif "./" in command.lower():
        return "c++"
    elif ".js" in command.lower():
        return "javascript"
    else:
        "" # No language detected


def get_error_message(error, language):
    # TODO: Write this
    if error == "":
        return None


def search_stackoverflow(query, page_num):
    url = SO_URL + "/search?page={}&q={}".format(page_num, query.replace(" ", "+"))
    html = requests.get(url).text
    soup = BeautifulSoup(html, "lxml")

    # TODO: Handle captchas

    search_results = get_search_results(soup)

    # Checks if we're on the last page
    page_nav_container = soup.find_all("div", class_="pager fl")[0]
    if page_nav_container == []:
        return (search_results, True)
    elif page_nav_container.find_all("span", class_="page-numbers next") == []:
        return (search_results, True)
    else:
        return (search_results, False)
