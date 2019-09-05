##########
## GLOBALS
##########


from rebound.web_scraping import search_stackoverflow
from rebound.file_execution import execute
from rebound.file_attributes import get_error_message, get_language
from rebound.interface import App
import time

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


USER_AGENTS = [
    "Mozilla/5.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1; AcooBrowser; .NET CLR 1.1.4322; .NET CLR 2.0.50727)",
    "Mozilla/5.0 (Windows; U; MSIE 9.0; Windows NT 9.0; en-US)",
    "Mozilla/5.0 (Windows; U; Windows NT 5.1; zh-CN) AppleWebKit/523.15 (KHTML, like Gecko, Safari/419.3) Arora/0.3 (Change: 287 c9dfb30)",
    "Mozilla/5.0 (X11; U; Linux; en-US) AppleWebKit/527+ (KHTML, like Gecko, Safari/419.3) Arora/0.6",
    "Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.8.1.2pre) Gecko/20070215 K-Ninja/2.1.1",
    "Mozilla/5.0 (Windows; U; Windows NT 5.1; zh-CN; rv:1.9) Gecko/20080705 Firefox/3.0 Kapiko/3.0",
    "Mozilla/5.0 (X11; Linux i686; U;) Gecko/20070322 Firefox/59",
    "Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.0.8) Gecko Fedora/1.9.0.8-1.fc10 Kazehakase/0.5.6",
    "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/535.11 (KHTML, like Gecko) Chrome/17.0.963.56 Safari/535.11",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_7_3) AppleWebKit/535.20 (KHTML, like Gecko) Chrome/19.0.1036.7 Safari/535.20",
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.113 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.90 Safari/537.36',
    'Mozilla/5.0 (Windows NT 5.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.90 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.2; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.90 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/44.0.2403.157 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.113 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/57.0.2987.133 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/57.0.2987.133 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.87 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.87 Safari/537.36',
    'Mozilla/4.0 (compatible; MSIE 9.0; Windows NT 6.1)',
    'Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; rv:11.0) like Gecko',
    'Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; WOW64; Trident/5.0)',
    'Mozilla/5.0 (Windows NT 6.1; Trident/7.0; rv:11.0) like Gecko',
    'Mozilla/5.0 (Windows NT 6.2; WOW64; Trident/7.0; rv:11.0) like Gecko',
    'Mozilla/5.0 (Windows NT 10.0; WOW64; Trident/7.0; rv:11.0) like Gecko',
    'Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.0; Trident/5.0)',
    'Mozilla/5.0 (Windows NT 6.3; WOW64; Trident/7.0; rv:11.0) like Gecko',
    'Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; Trident/5.0)',
    'Mozilla/5.0 (Windows NT 6.1; Win64; x64; Trident/7.0; rv:11.0) like Gecko',
    'Mozilla/5.0 (compatible; MSIE 10.0; Windows NT 6.1; WOW64; Trident/6.0)',
]

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
        print(BOLD + CYAN + question + prompt + END)
        choice = input().lower()
        if choice in valid:
            return valid[choice]

        print("Please respond with 'yes' or 'no' (or 'y' or 'n').\n")


def print_help():
    """Prints usage instructions."""
    print("%sRebound, V1.1.9a1 - Made by @shobrook%s\n" % (BOLD, END))
    print("Command-line tool that automatically searches Stack Overflow and displays results in your terminal when you get a compiler error.")
    print("\n\n%sUsage:%s $ rebound %s[file_name]%s\n" % (UNDERLINE, END, YELLOW, END))
    print("\n$ python3 %stest.py%s   =>   $ rebound %stest.py%s" % (YELLOW, END, YELLOW, END))
    print("\n$ node %stest.js%s     =>   $ rebound %stest.js%s\n" % (YELLOW, END, YELLOW, END))
    print("\nIf you just want to query Stack Overflow, use the -q parameter: $ rebound -q %sWhat is an array comprehension?%s\n\n" % (YELLOW, END))


## Main ##


def main():
    import sys
    if len(sys.argv) == 1 or sys.argv[1].lower() == "-h" or sys.argv[1].lower() == "--help":
        print_help()
    elif sys.argv[1].lower() == "-q" or sys.argv[1].lower() == "--query":
        query = ' '.join(sys.argv[2:])
        search_results, captcha = search_stackoverflow(query)

        if search_results != []:
            if captcha:
                print("\n%s%s%s" % (RED, "Sorry, Stack Overflow blocked our request. Try again in a minute.\n", END))
                return
            else:
                App(search_results) # Opens interface
        else:
            print("\n%s%s%s" % (RED, "No Stack Overflow results found.\n", END))
    else:
        language = get_language(sys.argv[1].lower()) # Gets the language name
        if language == '': # Unknown language
            print("\n%s%s%s" % (RED, "Sorry, Rebound doesn't support this file type.\n", END))
            return

        file_path = sys.argv[1:]
        if language == 'java':
            file_path = [f.replace('.class', '') for f in file_path]
        output, error = execute([language] + file_path) # Compiles the file and pipes stdout
        if (output, error) == (None, None): # Invalid file
            return

        error_msg = get_error_message(error, language) # Prepares error message for search
        if error_msg != None:
            language = 'java' if language == 'javac' else language # Fix language compiler command
            query = "%s %s" % (language, error_msg)
            search_results, captcha = search_stackoverflow(query)

            if search_results != []:
                if captcha:
                    print("\n%s%s%s" % (RED, "Sorry, Stack Overflow blocked our request. Try again in a minute.\n", END))
                    return
                elif confirm("\nDisplay Stack Overflow results?"):
                    App(search_results) # Opens interface
            else:
                print("\n%s%s%s" % (RED, "No Stack Overflow results found.\n", END))
        else:
            print("\n%s%s%s" % (CYAN, "No error detected :)\n", END))

    return
