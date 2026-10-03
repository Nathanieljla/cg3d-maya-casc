import sys
import os
import importlib
import subprocess

import __main__


psutil_exists = False
try:
    import psutil
    psutil_exists = True
except:
    pass


class Pigeon(object):
    def __init__(self, *args, **kwargs):
        pass
    
    
    @staticmethod
    def decode(output):
        try:
            return output.decode('utf-8')
        except UnicodeDecodeError:
            return output.decode('latin-1')
        
        
    @staticmethod
    def encode(output):
        try:
            return output.encode('utf-8')
        except UnicodeEncodeError:
            return output.encode('latin-1')        
        
    
    @classmethod
    def get_temp_filename(cls):
        """the name of the temporary file wing will use in write_temp_file()
        
        Sub-classes can override this is they want a unique name for their
        Pigeon.
        """
        return('wing_output_text.txt')
    

    @classmethod
    def get_temp_filepath(cls):
        """Returns the full path of the temp file on the local system."""
        return os.path.join(os.environ['TMP'], cls.get_temp_filename())


    @classmethod
    def write_temp_file(cls, txt):
        """writes the input text to the get_temp_filepath()"""
    
        # Save the text to a temp file. If we're dealing with mel, make sure it
        # ends with a semicolon, or Maya could become angered!
        #txt = get_wing_text()
        temp_path = cls.get_temp_filepath()
        f = open(temp_path, "wb")
    
        print('writing temp file:{}'.format(temp_path))
        f.write(Pigeon.encode(txt))
    
        f.close()

        temp_path = temp_path.replace("\\", "/")
        return temp_path
    
    
    @staticmethod
    def read_file(file_path):
        """Executes the python code stored in the file path.
        
        Args:
            file_path (string) : The absolute file path of the py file to read
        
        """
        
        print("WING: executing code from file {}\n".format(file_path))
        if os.access(file_path, os.F_OK):
            # execute the file contents in Maya:
            with open(file_path, "rb") as f:
                data = f.read()
                data = Pigeon.decode(data)
                exec(data, __main__.__dict__, __main__.__dict__) 

        else:
            print("No Wing-generated temp file exists: " + file_path)
            
            
    @classmethod
    def post_module_import(cls, module):
        """called if a Pigeon.import_module() is successful.
        
        The default behavior is to call the run() on the module if one
        exists. Override this method in a sub-class if you have custom logic
        for how you want what happens after a module has been
        imported/reloaded.
        
        Args:
            module : The module that was imported/reloaded from import_module()
        """
        if hasattr(module, 'run'):
            module.run()
            
            
    @classmethod
    def import_module(cls, module_name, file_path):
        """Attempts to import/reload the input module name and execute any run()
        
        If importing/reloading fails, then the file path is read (if
        defined). If sub-classes don't want to call run() they should
        override post_module_import().
        
        Args:
            module_name (string) : The name of the module relative to any
            package namespace.
            file_path (string) : The absolute file path to the py file.
        """
        
        print('\n')
        imported = module_name in sys.modules
        if imported:
            print('reloading module:{0}'.format(module_name))
            importlib.reload(sys.modules[module_name])
        else:
            try:
                print('Attempting module import of:{0}'.format(module_name))
                importlib.import_module(module_name)
            except ModuleNotFoundError:
                if file_path:
                    cls.read_file(file_path)


        if module_name in sys.modules:
            cls.post_module_import(sys.modules[module_name])
    
    
    def can_dispatch(self):
        """Check if conditions are right to send code to application
        
        can_dispatch() is used to determine what dispatcher wing will use
        with when there's no active dispatcher found.
        """
        raise NotImplementedError
    
    
    def owns_process(self, process):
        """Returns true if the process is the pigeon's target application
        
        This is used when an external application is connects to wing. When True
        is returned the Dispatcher becomes the active dispatcher to send commands
        to.
        
        Args:
            process (psutils.Process) : The node to remove the data from.  
        """
        raise NotImplementedError
    

    def send(self, highlighted_text, module_path, file_path, doc_type):
        """The main entry point for sending content from wing to an external app
        
        sub-classes should override this with application specfic logic for how
        the data is sent to an external application.        
        """
        raise NotImplementedError
    
    
    def send_python_command(self, command_string):
        """Send a custom python command to the target application
        
        Returns:
            bool : True if the command was successfully sent.        
        """
        raise NotImplementedError
    
    
    @staticmethod
    def get_exe_path_from_pid(pid):
        """
        Retrieves the executable path of a process given its PID using subprocess.
    
        Args:
            pid: The process ID (integer).
    
        Returns:
            The executable path (string) if found, otherwise None.
        """
        
        powershell_command = [
            "powershell.exe",
            "-Command",
            f"(Get-CimInstance Win32_Process -Filter 'ProcessId={pid}').ExecutablePath"
        ]
        
        try:
            result = subprocess.run(powershell_command, capture_output=True, text=True, check=True)
            return result.stdout.strip()
        except (subprocess.CalledProcessError):
            return None
        
        
    @staticmethod
    def find_exe_paths_by_name(process_name):
        """
        Finds and returns a list of executable paths for all processes
        matching the given name.
        """
        
        if not psutil_exists:
            raise ImportError("Can't find putil package")

        paths = []
        for proc in psutil.process_iter(['name', 'exe']):
            try:
                if proc.info['name'] == process_name:
                    paths.append(proc.info['exe'])
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                # Handle processes that may terminate or be inaccessible during the loop
                continue
            
        return paths    
    
    
    @staticmethod
    def process_id(process_name):
        """Returns the process ID of the running process_name or None"""

        pid = None
        psutil_failed = False
        if psutil_exists:
            try:
                pid = next(proc.pid for proc in psutil.process_iter(['name']) if proc.info['name'] == process_name)
            except (StopIteration, psutil.AccessDenied, psutil.NoSuchProcess):
                pass
            except:
                psutil_failed = True
            
        elif not psutil_exists or psutil_failed:
            #This is "Substantially slower than using psutil
            #wing-carrier doesn't rely on psutil due to a bug in the package once
            #making wing-carrier unuseable.
            import subprocess
            call = 'TASKLIST', '/FI', 'imagename eq %s' % process_name
            # use buildin check_output right away
            output = Pigeon.decode(subprocess.check_output(call))

            # check in last line for process name
            last_line = output.split('\r\n')
            if len(last_line) < 3:
                return None

            #first result is 3 because the headers
            #or in case more than one, you can use the last one using [-2] index
            data = " ".join(last_line[3].split()).split()
            pid = data[1]

        return pid


