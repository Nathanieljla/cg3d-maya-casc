
#default imports
import os
import re
import time
import platform
import sys
import webbrowser
import base64
#import math
#from datetime import datetime, timedelta
import glob
import tempfile
import shutil
import sys
import subprocess
from os.path import expanduser
import zipfile
from functools import partial
import site

try:
    #python3
    from urllib.request import urlopen
except:
    #python2
    from urllib import urlopen



class Platforms(object):
    OSX = 0,
    LINUX = 1,
    WINDOWS = 2
    
    @staticmethod
    def get_name(enum_value):
        if enum_value == Platforms.OSX:
            return 'osx'
        elif enum_value == Platforms.LINUX:
            return 'linux'
        else:
            return 'windows'

class Commandline(object):
    print_output = True
    
    @staticmethod        
    def get_python_version():
        """Get the running version of python as a tuple of 3 ints"""
        pmax, pmin, patch =  sys.version.split(' ')[0].split('.')
        return( int(pmax), int(pmin), int(patch))
    
    
    @staticmethod
    def get_platform():
        result = platform.platform().lower()
        if 'darwin' in result:
            return Platforms.OSX
        elif 'linux' in result:
            return Platforms.LINUX
        elif 'window' in result:
            return Platforms.WINDOWS
        else:
            raise ValueError('Unknown Platform Type:{0}'.format(result))
    
    
    @staticmethod    
    def run_shell_command(cmd, description):
        #NOTE: don't use subprocess.check_output(cmd), because in python 3.6+ this error's with a 120 code.
        print('\n{0}'.format(description))
        print('Calling shell command: {0}'.format(cmd))

        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = proc.communicate()
        stdout = stdout.decode()
        stderr = stderr.decode()
        
        if Commandline.print_output:
            print(stdout)
            print(stderr)
            
        if proc.returncode:
            raise Exception('Command Failed:\nreturn code:{0}\nstderr:\n{1}\n'.format(proc.returncode, stderr))
        
        return(stdout, stderr)
    
        
    @staticmethod
    def get_python_paths():
        """Returns maya's python path and location of a global pip
        
        Note: The pip path might not exist on the system.
        """
        python_path = ''
        pip_path = ''
        pmax, pmin, patch = Commandline.get_python_version()
        platform = Commandline.get_platform()
        
        version_str = '{0}.{1}'.format(pmax, pmin)
        if platform == Platforms.WINDOWS:
            python_path = os.path.join(os.getenv('MAYA_LOCATION'), 'bin', 'mayapy.exe')
            if pmax > 2:
                #python3 pip path
                pip_path = os.path.join(os.getenv('APPDATA'), 'Python', 'Python{0}{1}'.format(pmax, pmin), 'Scripts', 'pip{0}.exe'.format(version_str))
            else:
                #python2 pip path
                pip_path = os.path.join(os.getenv('APPDATA'), 'Python', 'Scripts', 'pip{0}.exe'.format(version_str))

        elif platform == Platforms.OSX:
            python_path = '/usr/bin/python'
            pip_path = os.path.join( expanduser('~'), 'Library', 'Python', version_str, 'bin', 'pip{0}'.format(version_str) )
     
        elif platform == Platforms.LINUX:
            python_path = os.path.join(os.getenv('MAYA_LOCATION'), 'bin', 'mayapy')
            pip_path = os.path.join( expanduser('~'), '.local', 'bin', 'pip{0}'.format(version_str) )
             
        return (python_path, pip_path)
    
    
    
    @staticmethod
    def get_command_string():
        """returns a commandline string for launching pip commands
        
        If the end-user is on linux then is sounds like calling pip from Mayapy
        can cause dependencies issues when using a default python install.
        So if the user is on osX or windows OR they're on linux and don't
        have python installed, then we'll use "mayapy -m pip" else we'll
        use the pipX.exe to run our commands.        
        """
        python_path, pip_path = Commandline.get_python_paths()
        platform = Commandline.get_platform()        

        command = '{0}&-m&pip'.format(python_path)
        global_pip = False
        if platform == Platforms.LINUX:
            try:
                #I don't use "python" here, because on windows that opens the MS store vs. erroring.
                #No clue what it might do on linux
                Commandline.run_shell_command(['py'], 'Checking python install')
                command = pip_path
                global_pip = True
            except:
                #Python isn't installed on linux, so the default command is good
                pass
            
        return (command,  global_pip)
    
    
    @staticmethod
    def pip(package, action, *args, **kwargs):
        pip_command, global_pip = Commandline.get_command_string()
        pip_args = pip_command.split('&')
        pip_args.append(action)
        pip_args.append(package)
        pip_args += args
        for key, value in kwargs.items():
            if len(key) == 1:
                name = '-{}'.format(key)
            else:
                name = '--{}'.format(key)
                
            pip_args.append(name)
            pip_args.append(value)
            
        stdout, stderr = Commandline.run_shell_command(pip_args, 'PIP:{} Package'.format(action))
        
        return stdout
        
                
    @staticmethod
    def pip_install(package, pip_args = [], *args, **kwargs):
        pip_command, global_pip = Commandline.get_command_string()
        cmd_str = ('{0}&install&{1}').format(pip_command, package)
        args = cmd_str.split('&') + pip_args
        stdout, stderr = Commandline.run_shell_command(args, 'PIP:Installing Package')
        
        return stdout
    
    
    @staticmethod
    def pip_uninstall(package, pip_args = [], *args, **kwargs):
        pip_command, global_pip = Commandline.get_command_string()
        cmd_str = ('{0}&uninstall&{1}').format(pip_command, package)
        args = cmd_str.split('&') + pip_args
        stdout, stderr = Commandline.run_shell_command(args, 'PIP:Uninstalling Package')
        
        return stdout
    

    @staticmethod
    def pip_list(pip_args = [], *args, **kwargs):
        pip_command, global_pip  = Commandline.get_command_string()
        cmd_str = ('{0}&list').format(pip_command)
        args = cmd_str.split('&') + pip_args
        stdout, stderr = Commandline.run_shell_command(args, 'PIP:Listing Packages')
        
        return stdout    


    @staticmethod
    def pip_show(repo_name, pip_args = [], *args, **kwargs):
        pip_command, global_pip  = Commandline.get_command_string()
        cmd_str = ('{0}&show&{1}').format(pip_command, repo_name)
        args = cmd_str.split('&') + pip_args
        stdout, stderr = Commandline.run_shell_command(args, 'PIP:Show Package Info')
        
        return stdout
    
    
    
def main(*args):
    import maya.cmds as cmds

    try:
        import pymel
        print(pymel.__file__)
        cmds.confirmDialog( title='Already installed', message=f'Pymel: {pymel.__version__}\nalready found at\n\n{pymel.__file__}\n\nYou can copy this path from the console window.', button=['Okay'], defaultButton='Okay' )
        return
    except:
        Commandline.pip_install('pymel')
        cmds.confirmDialog( title='Install Successful', message='Pymel should now be installed.', button=['Okay'], defaultButton='Okay' )
    

def onMayaDroppedPythonFile(*args):
    main()


if __name__ == "__main__":
    main()