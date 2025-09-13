import os
import sys
import inspect
import subprocess
import platform

IS_WINDOWS = 'windows' in platform.platform().lower()
#PSUTILS_EXISTS = False

#try:
    #import psutil
    #print("wing-carrier: psutil found")
    #PSUTILS_EXISTS = True
#except:
    #_pigeons_path = os.path.dirname(__file__)
    #_wingcarrier_path = os.path.dirname(_pigeons_path)    
    #_parent_dir = os.path.dirname(_wingcarrier_path)
    #_psutils_dir = os.path.join(_parent_dir, 'psutil')
    #if (os.path.exists(_psutils_dir)):
        #sys.path.append(_parent_dir)
        #print('wing-carrier: found psutil package at sibling location')
        #try:
            ##I'm having psutils fail during __init__ so let's catch that
            #import psutil
            #PSUTILS_EXISTS = True
        #except:
            #print("psutils crashed on import. CascadeurPigeon functionality limited to receiving")
        #finally:
            #sys.path.remove(_parent_dir)
    #else:
        #if not IS_WINDOWS:
            #print("Missing python package 'psutil'. CascadeurPigeon functionality limited to receiving")
        #PSUTILS_EXISTS = False


#CSC_EXISTS = False
#try:
    #import csc
    #CSC_EXISTS = True
#except:
    ##this will fail when using the module in wing
    #pass


from .pigeon import *


class CascadeurPigeon(Pigeon):
    def __init__(self, *args, **kwargs):
        super(CascadeurPigeon, self).__init__(*args, **kwargs)
        self.known_pid = None


    @staticmethod
    def run_shell_command(cmd):
        #NOTE: don't use subprocess.check_output(cmd), because in python 3.6+ this error's with a 120 code.
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = proc.communicate()
        stdout = stdout.decode()
        stderr = stderr.decode()

        print(stdout)
        print(stderr)
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
    
    
    def get_running_path(self):
        """Return the exe path of any running instance of cascadeur"""
        
        if IS_WINDOWS:
            return self._get_windows_exe_path()
        else:
            print("Cascadeur exe path can't be found on non-windows Operating system")
            return ''            
        
        #if not PSUTILS_EXISTS:
            #return self._get_windows_exe_path()
        
        ##we might already have a cached pid from wing.  let's try it first.
        #if self.known_pid:
            #try:
                #process = psutil.Process(pid=self.known_pid)
                #return process.exe()
            #except:
                #self.known_pid = None


        ##let's search the running processes for cascadeur
        ##ls: list = [] # since many processes can have same name it's better to make list of them
        #for p in psutil.process_iter(['name', 'pid']):
            #if p.info['name'] == 'cascadeur.exe':
                ##we can only have one running process of cascadeur
                #return psutil.Process(p.info['pid']).exe()

        #return ''
    
    
    def process_id(self, process_name):
        """Returns the process ID of the running cascadeur.exe or None"""
        
        import subprocess
        call = 'TASKLIST', '/FI', 'imagename eq %s' % process_name
        # use buildin check_output right away
        output = subprocess.check_output(call).decode()
    
        # check in last line for process name
        last_line = output.split('\r\n')
        if len(last_line) < 3:
            return None
        
        #first result is 3 because the headers
        #or in case more than one, you can use the last one using [-2] index
        data = " ".join(last_line[3].split()).split()  
    
        #return a list with the name and pid 
        return data[1] 


    def can_dispatch(self):
        """Check if conditions are right to send code to application
        
        can_dispatch() is used to determine what dispatcher wing will use
        with when there's no active dispatcher found.
        """
        exe_path = self.get_running_path()
        if not exe_path:
            return False
        
        return self.process_id('cascadeur.exe') is not None
        
        #elif not PSUTILS_EXISTS:
            ##This must be a windows machine and the exe was found via the
            ##registry let's make sure the process is running
            #return self.process_id('cascadeur.exe') is not None
        
        #else:
            #return True
    
    
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
            return
        
        command = '{}&--run-python-code&{}'.format(exe_path, command_string)
        CascadeurPigeon.run_shell_command(command.split('&'))        


    @staticmethod
    def receive(module_path, file_path):
        if not module_path:
            CascadeurPigeon.read_file(file_path)
        else:
            CascadeurPigeon.import_module(module_path, file_path)