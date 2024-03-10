
#Cascadeur specific imports
#import stat
#import json
#import shutil
#import pathlib
#from importlib import reload
#from urllib.request import urlopen

#default imports
import os
import pathlib
import re
#import time
import platform
import sys
#import webbrowser
#import base64
#import math
#from datetime import datetime, timedelta
#import glob
import tempfile
#import shutil
import sys
import subprocess
from os.path import expanduser
#import zipfile
#from functools import partial
#import site

#try:
    ##python3
    #from urllib.request import urlopen
#except:
    ##python2
    #from urllib import urlopen

#try:
    ##python2
    #reload
#except:
    ##python3
    #from importlib import reload
        
#from PySide6.QtCore import *
#from PySide6.QtWidgets import *
#from PySide6.QtGui import *
#from PySide6.QtUiTools import *    


#class Platforms(object):
    #OSX = 0,
    #LINUX = 1,
    #WINDOWS = 2
    
    #@staticmethod
    #def get_name(enum_value):
        #if enum_value == Platforms.OSX:
            #return 'osx'
        #elif enum_value == Platforms.LINUX:
            #return 'linux'
        #else:
            #return 'windows'
        
        
#class Commandline(object):
    #print_output = True
    
    #@staticmethod        
    #def get_python_version():
        #"""Get the running version of python as a tuple of 3 ints"""
        #pmax, pmin, patch =  sys.version.split(' ')[0].split('.')
        #return( int(pmax), int(pmin), int(patch))
    
    
    #@staticmethod
    #def get_platform():
        #result = platform.platform().lower()
        #if 'darwin' in result:
            #return Platforms.OSX
        #elif 'linux' in result:
            #return Platforms.LINUX
        #elif 'window' in result:
            #return Platforms.WINDOWS
        #else:
            #raise ValueError('Unknown Platform Type:{0}'.format(result))
    
    
    #@staticmethod    
    #def run_shell_command(cmd, description):
        ##NOTE: don't use subprocess.check_output(cmd), because in python 3.6+ this error's with a 120 code.
        #print('\n{0}'.format(description))
        #print('Calling shell command: {0}'.format(cmd))

        #proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        #stdout, stderr = proc.communicate()
        #stdout = stdout.decode()
        #stderr = stderr.decode()
        
        #if Commandline.print_output:
            #print(stdout)
            #print(stderr)
            
        #if proc.returncode:
            #raise Exception('Command Failed:\nreturn code:{0}\nstderr:\n{1}\n'.format(proc.returncode, stderr))
        
        #return(stdout, stderr)
    
        
    #@staticmethod
    #def get_python_paths():
        #"""Returns maya's python path and location of a global pip
        
        #Note: The pip path might not exist on the system.
        #"""
        #python_path = ''
        #pip_path = ''
        #pmax, pmin, patch = Commandline.get_python_version()
        #platform = Commandline.get_platform()
        
        #version_str = '{0}.{1}'.format(pmax, pmin)
        #if platform == Platforms.WINDOWS:
            #python_path = os.path.join(os.getenv('MAYA_LOCATION'), 'bin', 'mayapy.exe')
            #if pmax > 2:
                ##python3 pip path
                #pip_path = os.path.join(os.getenv('APPDATA'), 'Python', 'Python{0}{1}'.format(pmax, pmin), 'Scripts', 'pip{0}.exe'.format(version_str))
            #else:
                ##python2 pip path
                #pip_path = os.path.join(os.getenv('APPDATA'), 'Python', 'Scripts', 'pip{0}.exe'.format(version_str))

        #elif platform == Platforms.OSX:
            #python_path = '/usr/bin/python'
            #pip_path = os.path.join( expanduser('~'), 'Library', 'Python', version_str, 'bin', 'pip{0}'.format(version_str) )
     
        #elif platform == Platforms.LINUX:
            #python_path = os.path.join(os.getenv('MAYA_LOCATION'), 'bin', 'mayapy')
            #pip_path = os.path.join( expanduser('~'), '.local', 'bin', 'pip{0}'.format(version_str) )
             
        #return (python_path, pip_path)
    
    
    #@staticmethod
    #def get_command_string():
        #"""returns a commandline string for launching pip commands
        
        #If the end-user is on linux then is sounds like calling pip from Mayapy
        #can cause dependencies issues when using a default python install.
        #So if the user is on osX or windows OR they're on linux and don't
        #have python installed, then we'll use "mayapy -m pip" else we'll
        #use the pipX.exe to run our commands.        
        #"""
        #python_path, pip_path = Commandline.get_python_paths()
        #platform = Commandline.get_platform()        

        #command = '{0}&-m&pip'.format(python_path)
        #global_pip = False
        #if platform == Platforms.LINUX:
            #try:
                ##I don't use "python" here, because on windows that opens the MS store vs. erroring.
                ##No clue what it might do on linux
                #Commandline.run_shell_command(['py'], 'Checking python install')
                #command = pip_path
                #global_pip = True
            #except:
                ##Python isn't installed on linux, so the default command is good
                #pass
            
        #return (command, global_pip)
    
    
    #@staticmethod
    #def pip(package, action, *args, **kwargs):
        #pip_command, global_pip = Commandline.get_command_string()
        #pip_args = pip_command.split('&')
        #pip_args.append(action)
        #pip_args.append(package)
        #pip_args += args
        #for key, value in kwargs.items():
            #if len(key) == 1:
                #name = '-{}'.format(key)
            #else:
                #name = '--{}'.format(key)
                
            #pip_args.append(name)
            #pip_args.append(value)
            
        #stdout, stderr = Commandline.run_shell_command(pip_args, 'PIP:{} Package'.format(action))
        
        #return stdout
        
                
    #@staticmethod
    #def pip_install(package, pip_args = [], *args, **kwargs):
        #pip_command, global_pip = Commandline.get_command_string()
        #cmd_str = ('{0}&install&{1}').format(pip_command, package)
        #args = cmd_str.split('&') + pip_args
        #stdout, stderr = Commandline.run_shell_command(args, 'PIP:Installing Package')
        
        #return stdout
    
    
    #@staticmethod
    #def pip_uninstall(package, pip_args = [], *args, **kwargs):
        #pip_command, global_pip = Commandline.get_command_string()
        #cmd_str = ('{0}&uninstall&{1}').format(pip_command, package)
        #args = cmd_str.split('&') + pip_args
        #stdout, stderr = Commandline.run_shell_command(args, 'PIP:Uninstalling Package')
        
        #return stdout
    

    #@staticmethod
    #def pip_list(pip_args = [], *args, **kwargs):
        #pip_command, global_pip  = Commandline.get_command_string()
        #cmd_str = ('{0}&list').format(pip_command)
        #args = cmd_str.split('&') + pip_args
        #stdout, stderr = Commandline.run_shell_command(args, 'PIP:Listing Packages')
        
        #return stdout    


    #@staticmethod
    #def pip_show(repo_name, pip_args = [], *args, **kwargs):
        #pip_command, global_pip  = Commandline.get_command_string()
        #cmd_str = ('{0}&show&{1}').format(pip_command, repo_name)
        #args = cmd_str.split('&') + pip_args
        #stdout, stderr = Commandline.run_shell_command(args, 'PIP:Show Package Info')
        
        #return stdout        
        

        
class ModuleDefinition(object):
    """A .mod file can have multiple entries. Each definition equates to one entry"""
    
    MODULE_EXPRESSION = r"(?P<action>\+|\-)\s*(MAYAVERSION:(?P<maya_version>\d{4}))?\s*(PLATFORM:(?P<platform>\w+))?\s*(?P<module_name>\w+)\s*(?P<module_version>\d+\.?\d*.?\d*)\s+(?P<module_path>.*)\n(?P<defines>(?P<define>.+(\n?))+)?"
        
    def __init__(self, module_name, module_version,
                 maya_version = '', platform = '',
                 action = '+', module_path = '',
                 defines = [],
                 *args, **kwargs):
        
        self.action = action
        self.module_name = module_name
        self.module_version = module_version
        
        self.module_path = r'.\{0}'.format(self.module_name)
        if module_path:
            self.module_path = module_path

        self.maya_version = maya_version
        if self.maya_version is None:
            self.maya_version = ''
        
        self.platform = platform
        if self.platform is None:
            self.platform = ''
        
        self.defines = defines
        if not self.defines:
            self.defines = []
        
    def __str__(self):
        return_string = '{0} '.format(self.action)
        if self.maya_version:
            return_string += 'MAYAVERSION:{0} '.format(self.maya_version)
            
        if self.platform:
            return_string += 'PLATFORM:{0} '.format(self.platform)
            
        return_string += '{0} {1} {2}\n'.format(self.module_name, self.module_version, self.module_path)
        for define in self.defines:
            if define:
                return_string += '{0}\n'.format(define.rstrip('\n'))
         
        return_string += '\n'    
        return return_string



class ModuleEditor(object):
    """Used to make modules and edit .mod files quickly and easily."""
    
    def __init__(self):
        self._path = None
        self._module_definitions = []
        
    
    def get_install_paths(self, include_missing_paths=False):
        """Return a dict of install locations where the key is the entry index"""
        if self._path is None:
            raise FileNotFoundError()
        
        out_paths = {}
        for idx, entry in enumerate(self._module_definitions):
            install_path = pathlib.Path(entry.module_path)
            if install_path.is_absolute():
                out_paths.append(install_path)
            else:
                abs_path = self._path.parent.joinpath(install_path)
                if abs_path.exists() or include_missing_paths:
                    out_paths[idx] = abs_path
                else:
                    print(f"can't find location:{abs_path}")
            
        return out_paths
    
    
    def read_module_definitions(self, path):
        self._module_definitions = []
        read_result = False
        if (os.path.exists(path)):
            self._path = path
            file = open(path, 'r')
            text = file.read()
            file.close()
          
            for result in re.finditer(ModuleDefinition.MODULE_EXPRESSION, text):
                resultDict = result.groupdict()
                if resultDict['defines']:
                    resultDict['defines'] = resultDict['defines'].split("\n")
                    
                definition = ModuleDefinition(**resultDict)
                self._module_definitions.append(definition)
                
            read_result = True
            
        return read_result
      
                        
    def write_module_definitions(self, path, relative_paths=True):
        if relative_paths:
            for entry in self._module_definitions:     
                install_path = pathlib.Path(entry.module_path)
                if not install_path.is_absolute():
                    continue
                
                #OS works better than pathlib, because it
                #lets you get relative in parent locations
                rel_path = os.path.relpath(install_path, path)
                if not rel_path.startswith('.'):
                    rel_path = f".\\{rel_path}"
                    
                entry.module_path = rel_path
                    
        
        file = open(path, 'w')
        for entry in self._module_definitions:
            file.write(str(entry))
        
        file.close()

                           
    def __get_definitions(self, search_list, key, value):
        results = []
        for item in search_list:
            if item.__dict__[key] == value:
                results.append(item)
                
        return results
        
          
    def _get_definitions(self, *args, **kwargs):
        result_list = self._module_definitions
        for i in kwargs:
            result_list = self.__get_definitions(result_list, i, kwargs[i])
        return result_list
    
    
    def remove_definitions(self, *args, **kwargs):
        """
        removes all definitions that match the input argument values
        example : module_manager_instance.remove_definitions(module_name='generic', platform='win', maya_version='2023')
        
        Returns:
        --------
        list
            the results that were removed from the manager.
        
        """ 
        results = self._get_definitions(**kwargs)
        for result in results:
            self._module_definitions.pop(self._module_definitions.index(result))
            
        return results
    
    
    def remove_definition(self, entry):
        self.remove_definitions(module_name=entry.module_name,
                                platform=entry.platform, maya_version=entry.maya_version)
    
    
    def add_definition(self, definition):
        """

        """
        #TODO: Add some checks to make sure the definition doesn't conflict with an existing definition
        self._module_definitions.append(definition)




#class ModuleManager(QThread):
    #"""Used to make modules and edit .mod files quickly and easily."""
    
    #def __init__(self, module_name, module_version, package_name='',
                 #include_site_packages = False):
        
        #QThread.__init__(self)
        #self.dev_branch = False
        #self.upgrade_action = False
        #self.uninstall_action = False
        
        #self.action_succeeded = False
        
        #self._module_definitions = []
        #self.module_name = module_name
        #self.module_version = module_version
        
        #self.package_name = package_name
        #if not self.package_name:
            #self.package_name = self.module_name
        
        #self.maya_version = self.get_app_version()
        #self.platform = Commandline.get_platform()
        
        #self.max, self.min, self.patch = Commandline.get_python_version()
        
        ##common locations
        #self._version_specific = self.is_version_specific()  
        #self.app_dir = os.getenv('MAYA_APP_DIR')
        #self.install_root = self.get_install_root()
        #self.relative_module_path = self.get_relative_module_path()
        #self.module_path = self.get_module_path()
        #self.icons_path = self.get_icon_path()
        #self.presets_path = self.get_presets_path()
        #self.scripts_path = self.get_scripts_path()
        #self.plugins_path = self.get_plugins_path()
        
        #self.site_packages_path = self.get_site_package_path()
        #if not include_site_packages:
            #self.site_packages_path = ''
            
        #self.package_install_path = self.get_package_install_path()
        
        ##Non-Maya python and pip paths are needed for installing on linux (and OsX?)
        #self.python_path, self.pip_path = Commandline.get_python_paths()
        #self.command_string, self.uses_global_pip = Commandline.get_command_string()
     
    
    #def __del__(self):
        ##TODO: Determine why I put a wait on this fuction 
        #self.wait()
 
       
    #@staticmethod
    #def get_app_version():
        #"""What version of Maya is this?"""
        #return int(str(maya.cmds.about(apiVersion=True))[:4])
    
    
    #@staticmethod
    #def get_platform_string(platform):
        #"""Convert the current Platform value to a Module string"""
        #if platform is Platforms.OSX:
            #return 'mac'
        #elif platform is Platforms.LINUX:
            #return 'linux'
        #else:
            #return 'win64'
    
    
    #@staticmethod
    #def make_folder(folder_path):
        #if not os.path.exists(folder_path):
            #os.makedirs(folder_path)  
   
    
    #@staticmethod
    #def package_installed(package_name):
        #"""returns True if the repo is already on the system"""
        
        #return Commandline.pip_list().find(package_name) != -1
    

    #@staticmethod
    #def package_outdated(package_name):
        #"""Check to see if a local package is outdated
        
        #Checks to see the local pacakge is out-of-date.  This will always
        #be true with remote packages that are from Git, but will be accurate
        #with packages registered on PyPi. Since package_outdated()
        #assumes the package exists before checking make sure you you first
        #check the existance of the package with package_installed() before
        #checking the outdated status.
        
        #Returns:
        #--------
        #bool
            #True if missing or outdated, else False
        #"""
        ##TODO: get version checking to work with git packages.
        ##https://stackoverflow.com/questions/11560056/pip-freeze-does-not-show-repository-paths-for-requirements-file
        ##https://github.com/pypa/pip/issues/609
        ##it looks like we'd have to install packages with pip -e for this to work,
        ##but then we can't install to a target dir. I'm getting errors about
        ##trying to install in maya/src, but --user doesn't work either.

        ##I'm using --uptodate here, because both --uptodate and --outdated
        ##will be missing the package if the pacakage isn't registered with PyPi
        ##so -uptodate is easier to verify with than -o with remote package that
        ## might or might not be registered with PyPi
        
              
        #result = Commandline.pip_list(pip_args =['--uptodate'])
        #outdated = result.find(package_name) == -1
        #if outdated:
            #return True
        #else:
            #return False
    

    #def install_remote_package(self, package_name = '', to_module = True):
        #if not package_name:
            #package_name = self.get_remote_package()
        
        
        #if not package_name:
            #return
        
        ##https://stackoverflow.com/questions/39365080/pip-install-editable-with-a-vcs-url
        ##github = r'https://github.com/Nathanieljla/fSpy-Maya.git'
        
        #pip_args = []
        #if to_module:
            #pip_args = [
                ##r'--user', 
                ##r'--editable=git+{0}#egg={1}'.format(github, self.repo_name), 
                #r'--target={0}'.format(self.scripts_path), 
            #]
        #Commandline.pip_install(package_name, pip_args)
    
    
    #def get_remote_package(self):
        #"""returns the github or PyPi name needed for installing"""
        #maya.cmds.error( "No Package name/github path defined.  User needs to override Module_manager.get_remote_package()" )

        
    #def __ensure_pip_exists(self):
        #"""Make sure OS level pip is installed
        
        #This is written to work with all platforms, but
        #I've updated this to only run when we're on linux
        #because it sounds like that's the only time it's needed
        #"""
        
        #if not self.uses_global_pip:
            #print("Using Maya's PIP")
            #return
        
        #if os.path.exists(self.pip_path):
            #print('Global PIP found')
            #return
        
        #tmpdir = tempfile.mkdtemp()
        #get_pip_path = os.path.join(tmpdir, 'get-pip.py')
        #print(get_pip_path)
        
        #if self.platform == Platforms.OSX:
            ##cmd = 'curl https://bootstrap.pypa.io/pip/{0}/get-pip.py -o {1}'.format(pip_folder, pip_installer).split(' ')
            #cmd = 'curl https://bootstrap.pypa.io/pip/get-pip.py -o {0}'.format(get_pip_path).split(' ')
            #Commandline.run_shell_command(cmd, 'get-pip')

        #else:
            ## this should be using secure https, but we should be fine for now
            ## as we are only reading data, but might be a possible mid attack
            ##response = urlopen('https://bootstrap.pypa.io/pip/{0}/get-pip.py'.format(pip_folder))
            #response = urlopen('https://bootstrap.pypa.io/pip/get-pip.py')
            #data = response.read()
            
            #with open(get_pip_path, 'wb') as f:
                #f.write(data)
                
        ## Install pip
        ## On Linux installing pip with Maya Python creates unwanted dependencies to Mayas Python version, so pip might not work 
        ## outside of Maya Python anymore. So lets install pip with the os python version. 
        #filepath, filename = os.path.split(get_pip_path)
        ##is this an insert, so this pip is found before any other ones?
        #sys.path.insert(0, filepath)
        
        
        #if self.platform == Platforms.OSX or self.platform == Platforms.LINUX:
            #python_str = 'python{0}.{1}'.format(self.max, self.min)
        #else:
            #python_str = self.python_path
            
        #cmd = '{0}&{1}&--user&pip'.format(python_str, get_pip_path).split('&')
        #Commandline.run_shell_command(cmd, 'install pip')
        
        #print('Global PIP is ready for use!')
        
        
    #def is_version_specific(self):
        #"""Is this install for a specific version of Maya?
        
        #Some modules might have specific code for different versions of Maya.
        #For example if Maya is running Python 3 versus. 2. get_relative_module_path()
        #returns a different result when this True vs.False unless overridden by
        #the user.
        
        #Returns:
        #--------
        #bool
            #False
        #"""        
        
        #return False
     
    #def get_install_root(self):
        #"""Where should the module's folder and defintion install?
        
        #Maya has specific locations it looks for module defintitions os.getenv('MAYA_APP_DIR')
        #For windows this is "documents/maya/modules" or "documents/maya/mayaVersion/modules"
        #However 'userSetup' files can define alternative locations, which is
        #good for shared modules in a production environment.
        
        #Returns:
        #--------
        #str
            #os.path.join(self.app_dir, 'modules')
        #"""        
        #return os.path.join(self.app_dir, 'modules')
    
    #def get_relative_module_path(self):
        #"""What's the module folder path from the install root?
        
        #From the install location we can create a series of folder to reach
        #the base of our module.  This is where Maya will look for the
        #'plug-ins', 'scripts', 'icons', and 'presets' dir.  At a minimum
        #you should return the name of your module. The default implementation
        #create as a path of 'module-name'/platforms/maya-version/platform-name/x64
        #when is_version_specific() returns True
        
        #Returns:
        #str
            #self.module_name when is_version_specific() is False
        
        #"""
        #root = self.module_name
        #if self._version_specific:
            #root = os.path.join(self.module_name, 'platforms', str(self.maya_version),
                                #Platforms.get_name(self.platform),'x64')  
        #return root
    
    #def get_module_path(self):
        #return os.path.join(self.install_root, self.relative_module_path)
    
    #def get_icon_path(self):
        #return os.path.join(self.module_path, 'icons')
    
    #def get_presets_path(self):
        #return os.path.join(self.module_path, 'presets')
    
    #def get_scripts_path(self):
        #return os.path.join(self.module_path, 'scripts')
    
    #def get_plugins_path(self):
        #return os.path.join(self.module_path, 'plug-ins')
    
    #def get_site_package_path(self):
        #return os.path.join(self.scripts_path, 'site-packages')
    
    #def get_package_install_path(self):
        #return os.path.join(self.scripts_path, self.module_name)
    
    #def read_module_definitions(self, path):
        #self._module_definitions = []
        #if (os.path.exists(path)):
            #file = open(path, 'r')
            #text = file.read()
            #file.close()
          
            #for result in re.finditer(ModuleDefinition.MODULE_EXPRESSION, text):
                #resultDict = result.groupdict()
                #if resultDict['defines']:
                    #resultDict['defines'] = resultDict['defines'].split("\n")
                    
                #definition = ModuleDefinition(**resultDict)
                #self._module_definitions.append(definition)
      
                        
    #def write_module_definitions(self, path):
        #file = open(path, 'w')
        #for entry in self._module_definitions:
            #file.write(str(entry))
        
        #file.close()

                           
    #def __get_definitions(self, search_list, key, value):
        #results = []
        #for item in search_list:
            #if item.__dict__[key] == value:
                #results.append(item)
                
        #return results
        
          
    #def _get_definitions(self, *args, **kwargs):
        #result_list = self._module_definitions
        #for i in kwargs:
            #result_list = self.__get_definitions(result_list, i, kwargs[i])
        #return result_list
    
    
    #def remove_definitions(self, *args, **kwargs):
        #"""
        #removes all definitions that match the input argument values
        #example : module_manager_instance.remove_definitions(module_name='generic', platform='win', maya_version='2023')
        
        #Returns:
        #--------
        #list
            #the results that were removed from the manager.
        
        #""" 
        #results = self._get_definitions(**kwargs)
        #for result in results:
            #self._module_definitions.pop(self._module_definitions.index(result))
            
        #return results
    
    
    #def remove_definition(self, entry):
        #self.remove_definitions(module_name=entry.module_name,
                                #platform=entry.platform, maya_version=entry.maya_version)
    
    #def add_definition(self, definition):
        #"""

        #"""
        ##TODO: Add some checks to make sure the definition doesn't conflict with an existing definition
        #self._module_definitions.append(definition)
        
   
    #def run(self):
        #"""this starts the QThread"""
        #try:
            #self.action_succeeded = self.main_action()
        #except Exception as e:
            #self.action_succeeded = False
            #if self.upgrade_action:
                #print('Upgrade Failed!!\n{0}'.format(e))
            #else:
                #print('Install Failed!!\n{0}'.format(e))
            
                 
    #def get_definition_entry(self):
        #"""Converts this class into a module_defintion
        
        #Returns:
        #--------
        #Module_definition
            #The module defintion that represents the data of the Module_manager
        
        #"""
        #maya_version = str(self.maya_version)
        #relative_path = '.\{0}'.format(self.relative_module_path)        
        #platform_name =  self.get_platform_string(Commandline.get_platform())
        
        #if not self._version_specific:
            #maya_version = ''
            #platform_name = ''
            
        #defines = []
        #if self.site_packages_path:
            #site_path =  'PYTHONPATH+:={0}'.format(self.site_packages_path.split(self.module_path)[1])
            #defines = [site_path]
        
        #module_definition = ModuleDefinition(self.module_name, self.module_version,
                                                             #maya_version=maya_version, platform=platform_name, 
                                                             #module_path=relative_path,
                                                             #defines=defines)
        #return module_definition
     
             
    #def update_module_definition(self, filename):
        #"""remove old defintions and adds the current defintion to the .mod
        
        #Returns:
        #--------
        #bool
            #True if the update was successful else False        
        #"""
        #new_entry = self.get_definition_entry()
        #self.remove_definition(new_entry) #removes any old entries that might match before adding the new one
        #self.add_definition(new_entry)  
        #try:
            #self.write_module_definitions(filename)
        #except IOError:
            #return False
        
        #return True
    
    
    #def uninstallable(self):
        #return self.package_installed(self.package_name)
    
    
    #def uninstall(self):
        #return True
    
    
    #def dev_uninstall(self):
        #return True
    
    
    #def should_upgrade(self):
        #"""Should the manager run the uppgrade operation instead of installing"""
        #return self.package_installed(self.package_name) and self.package_outdated(self.package_name)        
    
    
    #def pre_action(self, upgrade, uninstall):
        ##Cache this result
        #self.upgrade_action = upgrade
        #self.uninstall_action = uninstall
        
        #if self.dev_branch:
            #if self.upgrade_action:
                #return self.pre_dev_upgrade()
            #elif self.uninstall_action:
                ##there is no pre_dev_uninstall method
                #return True
            #else:
                #return self.pre_dev_install()
        #else:            
            #if self.upgrade_action:
                #return self.pre_upgrade()
            #elif self.uninstall_action:
                ##there is no pre_uninstall method
                #return True
            #else:
                #return self.pre_install()
    
    
    #def pre_upgrade(self):
        #return True
    
    
    #def pre_dev_upgrade(self):
        #return True
    
    
    #def pre_dev_install(self):
        #return True
    
    
    #def pre_install(self):
        #"""Called before install() to do any sanity checks and prep
        
        #This function attempts to create the required install folders
        #and update/add the .mod file. Sub-class should call this function
        #when overriding

        #Returns:
        #--------
        #bool
            #true if the install can continue
        #"""
        #try:
            #self.__ensure_pip_exists()

        #except Exception as e:
            #print('failed to setup global pip {0}'.format(e))
            #return False
        
        #try:          
            #self.make_folder(self.module_path)       
            #self.make_folder(self.icons_path)
            #self.make_folder(self.presets_path)
            #self.make_folder(self.scripts_path)
            #self.make_folder(self.plugins_path)
            
            #if self.site_packages_path:
                #self.make_folder(self.site_packages_path)
        #except OSError:
            #return False
        
        
    #def main_action(self):
        ##Cache this result
        #if self.dev_branch:
            #if self.upgrade_action:
                #return self.dev_upgrade()
            #elif self.uninstall_action:
                #return self.dev_uninstall()            
            #else:
                #return self.dev_install()
        #else:
            #if self.upgrade_action:
                #return self.upgrade()
            #elif self.uninstall_action:
                #return self.uninstall()
            #else:
                #return self.install()
    
    
    #def upgrade(self):
        #print("Upgrade")
        #return True
    
    
    #def dev_upgrade(self):
        #print("Dev Upgrade")
        #return True
    
    
    #def dev_install(self):
        #print("Dev Install")
        #return True
    

    #def install(self):
        #"""The main install function users should override
        
        #returns:
            #bool:was the installation successful?
        #"""        
        #installed = False
        #if not self.package_installed(self.package_name):

            #try:
                #self.install_remote_package()
                #installed = True
            #except:
                #pass
            
        #return installed
    
    
    #def post_action(self):
        #if self.dev_branch:
            #if self.upgrade_action:
                #return self.post_dev_upgrade(self.action_succeeded)
            #elif self.uninstall_action:
                ##uninstall has no post dev uninstall method
                #return True   
            #else:
                #return self.post_dev_install(self.action_succeeded)
        #else:
            #if self.upgrade_action:
                #return self.post_upgrade(self.action_succeeded)
            #elif self.uninstall_action:
                ##uninstall has no post uninstall method
                #return True            
            #else:
                #return self.post_install(self.action_succeeded)
    
    
    #def post_dev_upgrade(self, upgrade_succeeded: bool):
        #return True
    
    
    #def post_dev_install(self, install_succeeded: bool):
        #return True
    

    #def post_upgrade(self, upgrade_succeeded: bool):
        #return True
    
    
    #def post_install(self, install_succeeded: bool):
        #"""Used after install() to do any clean-up
        
        #This function also updates/adds the .mod file.
        #Sub-classes should call this function when overriding.
        
        #Returns:
        #--------
        #bool
            #True if all post install operations executed as expected
        #"""
        
        #print('post install')
        #if install_succeeded:
            ##make sure the scripts path has been added so we can start running code.
            #if self.scripts_path not in sys.path:
                #sys.path.append(self.scripts_path)
                #print('Add scripts path [{}] to system paths'.format(self.scripts_path))

            ##make the mod file.                
            #filename = os.path.join(self.install_root, (self.module_name + '.mod'))
            #self.read_module_definitions(filename)
                  
            #return self.update_module_definition(filename)
        
        #return True
