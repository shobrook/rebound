import sys
import os
import inspect


#__all__=['']

#Using memcached for faster implementation of distributed memory
"""Function to get the filename and path to Python script calling Rebound Module
    get lines from python source file while attempting to optimize internally.
"""
def _get_caller_stack():
        # Get the full stack
        frame_stack = inspect.stack()
        # Get one level up from current
        caller_frame_record = frame_stack[-1]
        return caller_frame_record
        #caller_file_name = CallerFrame.filename  # Filename where caller lives

def _get_caller_path():
     # Get the module object of the caller 
    calling_script = inspect.getmodule(_get_caller_stack()[0])
    #module name from this path
    caller_path = os.path.dirname(calling_script.__file__)
    return(caller_path)                

        
def _main():
    #Get process id of running script
    process_id = os.getpid()
    #Monitor Terminal Output and Capture Standard Error to Logger
    sys.stderr = __logger
    #Run main.py From Open Terminal(path to modules log_file)
    os.system('start cmd /c rebound call -e %s -id%s'%(os.path.join(_caller_path,'log.err'),process_id))
    #__main = Popen(["python","main.py",str(process_id)],shell=True,stdin=sys.stdin,stdout=sys.stdout,start_new_session=True)#,executable=USERS_DEFAULT_SHELL)

#print(os.getenv('SHELL'))

#Execute,if Python File is Imported
if __name__ != '__main__':
    __module_path__ = os.path.dirname(__file__)
    _caller_path = _get_caller_path()    
    __python_path__ = sys.executable   
    #Open Logger
    __logger = open( os.path.join(_caller_path,'log.err'),'w')
    #assign global default comment methods
    _main()
    
    
    


