# Setup #


import sys
from queue import Queue
from subprocess import PIPE, Popen
from threading import Thread


# Helpers #


def read(pipe, funcs):
    for line in iter(pipe.readline, b""):
        for func in funcs:
            func(line.decode("utf-8"))
    pipe.close()


def write(get):
    for line in iter(get, None):
        sys.stdout.write(line)


# Main #


def execute(command, cwd=None, pass_through=True):
    outs, errs = None, None
    process = Popen(command.split(), cwd=cwd, shell=False, close_fds=True, stdout=PIPE, stderr=PIPE, bufsize=1)

    if pass_through:
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
    else:
        outs, errs = process.communicate()
        outs = "" if outs == None else outs.decode("utf-8")
        errs = "" if errs == None else errs.decode("utf-8")

    return (outs, errs)


def isolate_error(error):
    # TODO: Write this; needs to check for the language and filter code snippets
    if error == "":
        return None
    else:
        return error
