import sys
import os
import utilities as util
import webbrowser


def rebound(command):
    language = util.get_language(command[0]) # Gets the language name
    output, error = util.execute([language] + command[0:]) # Executes the command and pipes stdout
    error_msg = util.get_error_message(error, language) # Prepares error message for search

    if error_msg != None:
        query = "%s %s" % (language, error_msg)
        search_results, last_page, captcha = util.search_stackoverflow(query, 1)

        if search_results != []:
            if captcha:
                sys.stdout.write("\n" + util.RED + "Sorry, Stack Overflow blocked our request. Try again in a minute." + util.ENDC)
            elif util.confirm("\nDisplay Stack Overflow results?"):
                sys.stdout.write("\n" + util.GRAY + os.get_terminal_size().columns * "-" + util.ENDC + "\n") # TODO: Make this fancier and responsive

                util.display_first_result(search_results[0], query)

                sys.stdout.write("\n" + util.BOLD + util.BLUE + "Press ENTER for more choices, B to open in your browser, and any other key to quit: " + util.ENDC)
                key = input().lower()
                if key == "":
                    util.display_all_results(search_results, query, 1, last_page)
                elif key == "b":
                    webbrowser.open(search_results[0]["URL"])
        else:
            sys.stdout.write("\n" + util.RED + "No Stack Overflow results found." + util.ENDC)

rebound(sys.argv[1:])
