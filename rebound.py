import click
import utilities as util

@click.command()
@click.argument("command")
def rebound(command):
    output, error = util.execute(command) # Excutes the command and pipes output
    error = util.isolate_error(error) # Isolates the error message

    if error != None:
        # TODO: Scrape Stack Overflow results for the error message
        if click.confirm('Display Stack Overflow results?'):
            click.echo("Hah!")
            # TODO: Display results in a user-friendly manner
