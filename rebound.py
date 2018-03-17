import sys
import os
#import click
import utilities as util


def rebound(file_path):
    language = util.get_language(file_path) # Gets the language name
    output, error = util.execute("%s %s" % (language, file_path)) # Executes the command and pipes stdout
    error_msg = util.get_error_message(error, language) # Prepares error message for search

    if error_msg != None:
        sys.stdout.write("\n" + os.get_terminal_size().columns * "-" + "\n") # Display divider

        query = "%s %s" % (language, error_msg)
        search_results, last_page, captcha = util.search_stackoverflow(query, 1)

        if search_results != []:
            if util.query_display_results("Display Stack Overflow results?"):
                if captcha:
                    sys.stdout.write("\nSorry, Stack Overflow blocked our request. Try again in a minute.") # TODO: Make this red
                else:
                    util.display_results(search_results, query, last_page)
        else:
            sys.stdout.write("\nNo Stack Overflow results found.")

rebound(sys.argv[1]) # TODO: Handle multiple arguments
