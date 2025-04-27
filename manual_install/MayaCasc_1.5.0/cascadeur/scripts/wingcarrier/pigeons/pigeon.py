import sys
import os
import importlib
import __main__

class Pigeon(object):
    def __init__(self, *args, **kwargs):
        pass
    
    
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
        f.write(txt.encode())
    
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
                data = data.decode()
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


