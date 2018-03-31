"""
Name: Rebound
Version: 1.1
Description: Automatically displays Stack Overflow search results when you get an error, inside the terminal
Author: @shobrook
"""

import sys
import utilities as util


def main(command):
    language = util.get_language(command[0].lower()) # Gets the language name
    if language == '': # Unknown language
        sys.stdout.write("\n%s%s%s" % (util.RED, "Sorry, Rebound doesn't support this file type.", util.END))
        return

    util.get_question_and_answers("https://stackoverflow.com/questions/39182074/urwid-colored-text-simplified")

    output, error = util.execute([language] + command[0:]) # Executes the command and pipes stdout
    error_msg = util.get_error_message(error, language) # Prepares error message for search

    if error_msg != None:
        query = "%s %s" % (language, error_msg)
        search_results, captcha = util.search_stackoverflow(query)

        if search_results != []:
            if captcha:
                sys.stdout.write("\n%s%s%s" % (util.RED, "Sorry, Stack Overflow blocked our request. Try again in a minute.", util.END))
                return
            elif util.confirm("\nDisplay Stack Overflow results?"):
                return util.App(search_results)
        else:
            sys.stdout.write("\n%s%s%s" % (util.RED, "No Stack Overflow results found.", util.END))
    else:
        sys.stdout.write("\n%s%s%s" % (util.CYAN, "No error detected :)", util.END))
