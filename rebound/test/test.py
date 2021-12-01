import argparse
import os
from psutil import Process,NoSuchProcess
from search_engine_parser.core.engines.google import Search as GoogleSearch
import sys


parser = argparse.ArgumentParser (prog='Rebound',description='Command-line tool that automatically searches Stack Overflow and displays results in your terminal when you get a compiler error.\n Made by @shobrook')
parser.add_argument('-v','--version', action='version', version='%(prog)s 1.1.9a1')
parser.add_argument("-s","--script",help="Run Script from Terminal")
parser.add_argument('-q','--query',help='Query stackoverflow with Error message ')
subparser = parser.add_subparsers(dest='command')
call = subparser.add_parser('call')
call.add_argument("-id",'--pid',required=True)
call.add_argument('-e','--err',required=True)
args = parser.parse_args()


if args.command=='call':
    if os.path.isfile(args.err):
        ProcessId= int(args.pid)
        MonitorProcess(args.err,ProcessId)
    else:
        raise Exception("-e takes path to Error logfile Only")    
elif args.query is not None:
    search_results = search_google(args.query)
    if search_results != []:
        App(search_results) # Opens interface        
    else:
        print("\n%s%s%s" % (RED, "No Google results found.\n", END))

elif args.script is not None:
    ProcessScript(args.script)
        
else: parser.print_help()
        
def execute_task(ProcessId):
  try:      
      while True:
          RunningProcess = Process(ProcessId)
  except NoSuchProcess as e:
        return

def MonitorProcess(ErrorLog,pid):
    ProcessState = execute_task(pid)
    with open(ErrorLog,'r') as log:
        ErrorMessage = log.read()
    ValidError= print(RED+BOLD+ErrorMessage,file=sys.stdout) if get_error_message(ErrorMessage,'python3') is None else get_error_message(ErrorMessage,'python3') 
    if ValidError is not None:
            print(RED+BOLD+ErrorMessage,file=sys.stdout)
            site = 'site:stackoverflow.com'
            query = "%s %s %s" % ('python', ValidError,site)
            search_results = search_google(query)
            if search_results != []:
                if confirm("\nDisplay Stack Overflow results?"):
                    App(search_results) # Opens interface
                    #print([i['title'] for i in search_results])
                    print([result for result in search_results]) 
            else:
                print("\n%s%s%s" % (RED, "No Google results found.\n", END))
    return 

def ProcessScript(script):
        language = get_language(script.lower()) # Gets the language name
        if language == '': # Unknown language
            print("\n%s%s%s" % (RED, "Sorry, Rebound doesn't support this file type.\n", END))
            return
        file_path = script
        if language == 'java':
            file_path = [f.replace('.class', '') for f in file_path]
        output, error = execute([language] + file_path) # Compiles the file and pipes stdout
        if (output, error) == (None, None): # Invalid file
            return
        error_msg = get_error_message(error, language) # Prepares error message for search
        if error_msg != None:
            language = 'java' if language == 'javac' else language # Fix language compiler command
            site = 'site:stackoverflow.com'
            query = "%s %s %s" % (language, error_msg,site)
            search_results = search_google(query)
            if search_results != []:
                if confirm("\nDisplay Stack Overflow results?"):
                    App(search_results) # Opens interface
            else:
                print("\n%s%s%s" % (RED, "No Google results found.\n", END))
        else:
            print("\n%s%s%s" % (CYAN, "No error detected :)\n", END))
                