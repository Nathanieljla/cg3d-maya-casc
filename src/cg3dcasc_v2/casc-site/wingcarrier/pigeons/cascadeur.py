import os
import sys
import inspect
import subprocess
import platform

IS_WINDOWS = 'windows' in platform.platform().lower()

from .pigeon import *


class CascadeurPigeon(Pigeon):
    process_name = "cascadeur.exe"

    def __init__(self, *args, **kwargs):
        super(CascadeurPigeon, self).__init__(*args, **kwargs)
        self.known_pid = None
        

    @staticmethod
    def run_shell_command(cmd):
        #NOTE: don't use subprocess.check_output(cmd), because in python 3.6+ this error's with a 120 code.
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = proc.communicate()
        stdout = CascadeurPigeon.decode(stdout)
        stderr = CascadeurPigeon.decode(stderr)

        #print(f"casc out:\n{stdout}")
        #print(f"casc err:\n{stderr}")
        if proc.returncode:
            raise Exception('Command Failed:\nreturn code:{0}\nstderr:\n{1}\n'.format(proc.returncode, stderr))

        return(stdout, stderr)


    @classmethod
    def get_temp_filename(cls):
        return('cascadeur_code.txt')
    
    
    def _get_windows_exe_path(self):
        import winreg
        casc_path = ''
        try:
            access_registry = winreg.ConnectRegistry(None,winreg.HKEY_CLASSES_ROOT)
            access_key = winreg.OpenKey(access_registry, r"Cascadeur\shell\open\command")
            casc_path = winreg.QueryValue(access_key, None)
        except Exception as e:
            print("Couldn't find the EXE in winreg. Let's look at this case! Error:{}".format(e))
            
        return casc_path.strip("\"")
    
    
    def get_own_process(self):
        return self.process_id(self.process_name)

    
    def get_running_path(self):
        """Return the exe path of any running instance of cascadeur"""

        try:
            paths = self.find_exe_paths_by_name(self.process_name)
            return paths[0] if paths else ''

        except ImportError:     
            if IS_WINDOWS:    
                pid = self.get_own_process()
                if pid is None:
                    return ''

                path = self.get_exe_path_from_pid(pid)
                return path
            else:
                print("Cascadeur exe path can't be found on non-windows Operating system")
                return ''            
    

    def can_dispatch(self):
        """Check if conditions are right to send code to application
        
        can_dispatch() is used to determine what dispatcher wing will use
        with when there's no active dispatcher found.
        """
        return self.get_own_process() is not None
    
    
    def owns_process(self, process):
        """Returns true if the process is the pigeons target application
        
        This is used when an external application is connects to wing. When True
        is returned the Dispatcher becomes the active dispatcher to send commands
        to.
        
        Args:
            process (psutils.Process) : The node to remove the data from.  
        """
        valid_process = 'cascadeur' in process.name()
        
        if valid_process:
            self.known_pid = process.pid
            
        return valid_process
    

    @classmethod
    def post_module_import(cls, module):
        """call the run function on the imported module if it exists
        
        We'll assume that if the run() takes any arguments that the first
        argument is the current scene, since this is the cascadeur standard.
        """

        print("Calling post module import")
        if hasattr(module, 'run'):
            signature = inspect.signature(module.run)
            if signature.parameters:
                if CSC_EXISTS:
                    scene = csc.app.get_application().get_scene_manager().current_scene()
                    module.run(scene)
                else:
                    module.run(None)
            else:
                module.run()


    def send(self, highlighted_text, module_path, file_path, doc_type):            
        if highlighted_text:
            command_string = highlighted_text
        else:
            command_string = u"import wingcarrier.pigeons; wingcarrier.pigeons.CascadeurPigeon.receive(\'{}\',\'{}\')".format(module_path, file_path)
            
        self.send_python_command(command_string)  
          
    
    def send_python_command(self, command_string):
        exe_path = self.get_running_path()
        if not exe_path:
            print('No instance of cascadeur is running')
            return False

        success = False
        try: 
            command = '{}&--run-python-code&{}'.format(exe_path, command_string)
            CascadeurPigeon.run_shell_command(command.split('&'))
            success = True
        except:
            pass
        
        return success


    @staticmethod
    def receive(module_path, file_path):
        if not module_path:
            CascadeurPigeon.read_file(file_path)
        else:
            CascadeurPigeon.import_module(module_path, file_path)