# Globals #


import click
import utilities as util


# Main #


@click.command()
@click.argument("command")
def rebound(command):
    output, error = util.execute(command) # Excutes the command and pipes output
    language = util.get_language(command) # Gets the language name
    #error_msg = util.get_error_message(error) # Prepares error message for search
    search_results, last_page = util.search_stackoverflow("TypeError: integer", 1)
    print(search_results)

    if error != None:
        #search_results, last_page = util.search_stackoverflow(language + " " + error_msg, 1)
        if click.confirm("Display Stack Overflow results?"):
            click.echo("Hah!")
            # TODO: Display search results in a user-friendly manner
            #if last_page and click.confirm("Display more results?"):
                #click.echo(":^)")
