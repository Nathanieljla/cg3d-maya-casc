"""
Drag-n-drop this into a maya viewport to install packages

This is copied from:
https://github.com/Nathanieljla/cg3d-maya-core/blob/main/src/cg3dguru/utils/drop_installer.py

If you want to modify this script for your own purposes it's better
to pull a copy from the source location.

changes:
v1.0.0 : Users can now upgrade and uninstall as well as test from development builds
v0.9.2 : post_install now receives bool on if main install was successful


How to use:
Users should modify the main() and MyInstaller class. Everything else should
be hands off.
"""

__author__ = "Nathaniel Albright"
__email__ = "developer@3dcg.guru"

VERSION = (1, 0, 0)
__version__ = '.'.join(map(str, VERSION))



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

try:
    #python2
    reload
except:
    #python3
    from importlib import reload

try:
    import maya.utils
    import maya.cmds
    from maya import OpenMayaUI as omui
    
    MAYA_RUNNING = True
except ImportError:
    MAYA_RUNNING = False
    
    
if MAYA_RUNNING:
    try:
        from PySide2.QtCore import * 
        from PySide2.QtWidgets import *
        from PySide2.QtUiTools import *
        from PySide2 import __version__
        from shiboken2 import wrapInstance
    except:
        from PySide6.QtCore import * 
        from PySide6.QtWidgets import *
        from PySide6.QtUiTools import *
        from PySide6 import __version__
        from shiboken6 import wrapInstance       


RESOURCES = None
    
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
        stdout, stderr = Commandline.run_shell_command(args, 'PIP:Installing Package')
        
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



class ModuleManager(QThread):
    """Used to make modules and edit .mod files quickly and easily."""
    
    def __init__(self, module_name, module_version, package_name='',
                 include_site_packages = False):
        
        QThread.__init__(self)
        self.dev_branch = False
        self.upgrade_action = False
        self.uninstall_action = False
        
        self.action_succeeded = False
        
        self._module_definitions = []
        self.module_name = module_name
        self.module_version = module_version
        
        self.package_name = package_name
        if not self.package_name:
            self.package_name = self.module_name
        
        self.maya_version = self.get_app_version()
        self.platform = Commandline.get_platform()
        
        self.max, self.min, self.patch = Commandline.get_python_version()
        
        #common locations
        self._version_specific = self.is_version_specific()  
        self.app_dir = os.getenv('MAYA_APP_DIR')
        self.install_root = self.get_install_root()
        self.relative_module_path = self.get_relative_module_path()
        self.module_path = self.get_module_path()
        self.icons_path = self.get_icon_path()
        self.presets_path = self.get_presets_path()
        self.scripts_path = self.get_scripts_path()
        self.plugins_path = self.get_plugins_path()
        
        self.site_packages_path = self.get_site_package_path()
        if not include_site_packages:
            self.site_packages_path = ''
            
        self.package_install_path = self.get_package_install_path()
        
        #Non-Maya python and pip paths are needed for installing on linux (and OsX?)
        self.python_path, self.pip_path = Commandline.get_python_paths()
        self.command_string, self.uses_global_pip = Commandline.get_command_string()
     
    
    def __del__(self):
        #TODO: Determine why I put a wait on this fuction 
        self.wait()
 
       
    @staticmethod
    def get_app_version():
        """What version of Maya is this?"""
        return int(str(maya.cmds.about(apiVersion=True))[:4])
    
    
    @staticmethod
    def get_platform_string(platform):
        """Convert the current Platform value to a Module string"""
        if platform is Platforms.OSX:
            return 'mac'
        elif platform is Platforms.LINUX:
            return 'linux'
        else:
            return 'win64'
    
    
    @staticmethod
    def make_folder(folder_path):
        print(folder_path)
        
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)


    @staticmethod
    def get_ui_parent():
        return wrapInstance( int(omui.MQtUtil.mainWindow()), QMainWindow )      
   
    
    @staticmethod
    def package_installed(package_name):
        """returns True if the repo is already on the system"""
        
        return Commandline.pip_list().find(package_name) != -1
    

    @staticmethod
    def package_outdated(package_name):
        """Check to see if a local package is outdated
        
        Checks to see the local pacakge is out-of-date.  This will always
        be true with remote packages that are from Git, but will be accurate
        with packages registered on PyPi. Since package_outdated()
        assumes the package exists before checking make sure you you first
        check the existance of the package with package_installed() before
        checking the outdated status.
        
        Returns:
        --------
        bool
            True if missing or outdated, else False
        """
        #TODO: get version checking to work with git packages.
        #https://stackoverflow.com/questions/11560056/pip-freeze-does-not-show-repository-paths-for-requirements-file
        #https://github.com/pypa/pip/issues/609
        #it looks like we'd have to install packages with pip -e for this to work,
        #but then we can't install to a target dir. I'm getting errors about
        #trying to install in maya/src, but --user doesn't work either.

        #I'm using --uptodate here, because both --uptodate and --outdated
        #will be missing the package if the pacakage isn't registered with PyPi
        #so -uptodate is easier to verify with than -o with remote package that
        # might or might not be registered with PyPi
        
              
        result = Commandline.pip_list(pip_args =['--uptodate'])
        outdated = result.find(package_name) == -1
        if outdated:
            return True
        else:
            return False
    

    def install_remote_package(self, package_name = '', to_module = True):
        if not package_name:
            package_name = self.get_remote_package()
        
        
        if not package_name:
            return
        
        #https://stackoverflow.com/questions/39365080/pip-install-editable-with-a-vcs-url
        #github = r'https://github.com/Nathanieljla/fSpy-Maya.git'
        
        pip_args = []
        if to_module:
            pip_args = [
                #r'--user', 
                #r'--editable=git+{0}#egg={1}'.format(github, self.repo_name), 
                r'--target={0}'.format(self.scripts_path), 
            ]
        Commandline.pip_install(package_name, pip_args)
    
    
    def get_remote_package(self):
        """returns the github or PyPi name needed for installing"""
        maya.cmds.error( "No Package name/github path defined.  User needs to override Module_manager.get_remote_package()" )

        
    def __ensure_pip_exists(self):
        """Make sure OS level pip is installed
        
        This is written to work with all platforms, but
        I've updated this to only run when we're on linux
        because it sounds like that's the only time it's needed
        """
        
        if not self.uses_global_pip:
            print("Using Maya's PIP")
            return
        
        if os.path.exists(self.pip_path):
            print('Global PIP found')
            return
        
        tmpdir = tempfile.mkdtemp()
        get_pip_path = os.path.join(tmpdir, 'get-pip.py')
        print(get_pip_path)
        
        if self.platform == Platforms.OSX:
            #cmd = 'curl https://bootstrap.pypa.io/pip/{0}/get-pip.py -o {1}'.format(pip_folder, pip_installer).split(' ')
            cmd = 'curl https://bootstrap.pypa.io/pip/get-pip.py -o {0}'.format(get_pip_path).split(' ')
            Commandline.run_shell_command(cmd, 'get-pip')

        else:
            # this should be using secure https, but we should be fine for now
            # as we are only reading data, but might be a possible mid attack
            #response = urlopen('https://bootstrap.pypa.io/pip/{0}/get-pip.py'.format(pip_folder))
            response = urlopen('https://bootstrap.pypa.io/pip/get-pip.py')
            data = response.read()
            
            with open(get_pip_path, 'wb') as f:
                f.write(data)
                
        # Install pip
        # On Linux installing pip with Maya Python creates unwanted dependencies to Mayas Python version, so pip might not work 
        # outside of Maya Python anymore. So lets install pip with the os python version. 
        filepath, filename = os.path.split(get_pip_path)
        #is this an insert, so this pip is found before any other ones?
        sys.path.insert(0, filepath)
        
        
        if self.platform == Platforms.OSX or self.platform == Platforms.LINUX:
            python_str = 'python{0}.{1}'.format(self.max, self.min)
        else:
            python_str = self.python_path
            
        cmd = '{0}&{1}&--user&pip'.format(python_str, get_pip_path).split('&')
        Commandline.run_shell_command(cmd, 'install pip')
        
        print('Global PIP is ready for use!')
        
        
    def is_version_specific(self):
        """Is this install for a specific version of Maya?
        
        Some modules might have specific code for different versions of Maya.
        For example if Maya is running Python 3 versus. 2. get_relative_module_path()
        returns a different result when this True vs.False unless overridden by
        the user.
        
        Returns:
        --------
        bool
            False
        """        
        
        return False
     
    def get_install_root(self):
        """Where should the module's folder and defintion install?
        
        Maya has specific locations it looks for module defintitions os.getenv('MAYA_APP_DIR')
        For windows this is "documents/maya/modules" or "documents/maya/mayaVersion/modules"
        However 'userSetup' files can define alternative locations, which is
        good for shared modules in a production environment.
        
        Returns:
        --------
        str
            os.path.join(self.app_dir, 'modules')
        """        
        return os.path.join(self.app_dir, 'modules')
    
    def get_relative_module_path(self):
        """What's the module folder path from the install root?
        
        From the install location we can create a series of folder to reach
        the base of our module.  This is where Maya will look for the
        'plug-ins', 'scripts', 'icons', and 'presets' dir.  At a minimum
        you should return the name of your module. The default implementation
        create as a path of 'module-name'/platforms/maya-version/platform-name/x64
        when is_version_specific() returns True
        
        Returns:
        str
            self.module_name when is_version_specific() is False
        
        """
        root = self.module_name
        if self._version_specific:
            root = os.path.join(self.module_name, 'platforms', str(self.maya_version),
                                Platforms.get_name(self.platform),'x64')  
        return root
    
    def get_module_path(self):
        return os.path.join(self.install_root, self.relative_module_path)
    
    def get_icon_path(self):
        return os.path.join(self.module_path, 'icons')
    
    def get_presets_path(self):
        return os.path.join(self.module_path, 'presets')
    
    def get_scripts_path(self):
        return os.path.join(self.module_path, 'scripts')
    
    def get_plugins_path(self):
        return os.path.join(self.module_path, 'plug-ins')
    
    def get_site_package_path(self):
        return os.path.join(self.scripts_path, 'site-packages')
    
    def get_package_install_path(self):
        return os.path.join(self.scripts_path, self.module_name)
    
  
    def read_module_definitions(self, path):
        self._module_definitions = []
        if (os.path.exists(path)):
            file = open(path, 'r')
            text = file.read()
            file.close()
          
            for result in re.finditer(ModuleDefinition.MODULE_EXPRESSION, text):
                resultDict = result.groupdict()
                if resultDict['defines']:
                    resultDict['defines'] = resultDict['defines'].split("\n")
                    
                definition = ModuleDefinition(**resultDict)
                self._module_definitions.append(definition)
      
                        
    def write_module_definitions(self, path):
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
        
   
    def run(self):
        """this starts the QThread"""
        try:
            self.action_succeeded = self.main_action()
        except Exception as e:
            self.action_succeeded = False
            if self.upgrade_action:
                print('Upgrade Failed!!\n{0}'.format(e))
            else:
                print('Install Failed!!\n{0}'.format(e))
            
                 
    def get_definition_entry(self):
        """Converts this class into a module_defintion
        
        Returns:
        --------
        Module_definition
            The module defintion that represents the data of the Module_manager
        
        """
        maya_version = str(self.maya_version)
        relative_path = '.\{0}'.format(self.relative_module_path)        
        platform_name =  self.get_platform_string(Commandline.get_platform())
        
        if not self._version_specific:
            maya_version = ''
            platform_name = ''
            
        defines = []
        if self.site_packages_path:
            site_path =  'PYTHONPATH+:={0}'.format(self.site_packages_path.split(self.module_path)[1])
            defines = [site_path]
        
        module_definition = ModuleDefinition(self.module_name, self.module_version,
                                                             maya_version=maya_version, platform=platform_name, 
                                                             module_path=relative_path,
                                                             defines=defines)
        return module_definition
     
             
    def update_module_definition(self, filename):
        """remove old defintions and adds the current defintion to the .mod
        
        Returns:
        --------
        bool
            True if the update was successful else False        
        """
        new_entry = self.get_definition_entry()
        self.remove_definition(new_entry) #removes any old entries that might match before adding the new one
        self.add_definition(new_entry)  
        try:
            self.write_module_definitions(filename)
        except IOError:
            return False
        
        return True
    
    
    def uninstallable(self):
        return self.package_installed(self.package_name)
    
    
    def uninstall(self):
        return True
    
    
    def dev_uninstall(self):
        return True
    
    
    def should_upgrade(self):
        """Should the manager run the uppgrade operation instead of installing"""
        return self.package_installed(self.package_name) and self.package_outdated(self.package_name)        
    
    
    def pre_action(self, upgrade, uninstall):
        #Cache this result
        self.upgrade_action = upgrade
        self.uninstall_action = uninstall
        
        if self.dev_branch:
            if self.upgrade_action:
                return self.pre_dev_upgrade()
            elif self.uninstall_action:
                #there is no pre_dev_uninstall method
                return True
            else:
                return self.pre_dev_install()
        else:            
            if self.upgrade_action:
                return self.pre_upgrade()
            elif self.uninstall_action:
                #there is no pre_uninstall method
                return True
            else:
                return self.pre_install()
    
    
    def pre_upgrade(self):
        return True
    
    
    def pre_dev_upgrade(self):
        return True
    
    
    def pre_dev_install(self):
        return True
    
    
    def pre_install(self):
        """Called before install() to do any sanity checks and prep
        
        This function attempts to create the required install folders
        and update/add the .mod file. Sub-class should call this function
        when overriding

        Returns:
        --------
        bool
            true if the install can continue
        """
        try:
            self.__ensure_pip_exists()

        except Exception as e:
            print('failed to setup global pip {0}'.format(e))
            return False
        
        try:          
            self.make_folder(self.module_path)       
            self.make_folder(self.icons_path)
            self.make_folder(self.presets_path)
            self.make_folder(self.scripts_path)
            self.make_folder(self.plugins_path)
            
            if self.site_packages_path:
                self.make_folder(self.site_packages_path)
        except OSError:
            return False
        
        
    def main_action(self):
        #Cache this result
        if self.dev_branch:
            if self.upgrade_action:
                return self.dev_upgrade()
            elif self.uninstall_action:
                return self.dev_uninstall()            
            else:
                return self.dev_install()
        else:
            if self.upgrade_action:
                return self.upgrade()
            elif self.uninstall_action:
                return self.uninstall()
            else:
                return self.install()
    
    
    def upgrade(self):
        print("Upgrade")
        return True
    
    
    def dev_upgrade(self):
        print("Dev Upgrade")
        return True
    
    
    def dev_install(self):
        print("Dev Install")
        return True
    

    def install(self):
        """The main install function users should override
        
        returns:
            bool:was the installation successful?
        """        
        installed = False
        if not self.package_installed(self.package_name):

            try:
                self.install_remote_package()
                installed = True
            except:
                pass
            
        return installed
    
    
    
    def post_action(self):
        if self.dev_branch:
            if self.upgrade_action:
                return self.post_dev_upgrade(self.action_succeeded)
            elif self.uninstall_action:
                #uninstall has no post dev uninstall method
                return True   
            else:
                return self.post_dev_install(self.action_succeeded)
        else:
            if self.upgrade_action:
                return self.post_upgrade(self.action_succeeded)
            elif self.uninstall_action:
                #uninstall has no post uninstall method
                return True            
            else:
                return self.post_install(self.action_succeeded)
    
    
    
    def post_dev_upgrade(self, upgrade_succeeded: bool):
        return True
    
    
    def post_dev_install(self, install_succeeded: bool):
        return True
    

    def post_upgrade(self, upgrade_succeeded: bool):
        return True
    
    
    def post_install(self, install_succeeded: bool):
        """Used after install() to do any clean-up
        
        This function also updates/adds the .mod file.
        Sub-classes should call this function when overriding.
        
        Returns:
        --------
        bool
            True if all post install operations executed as expected
        """
        
        print('post install')
        if install_succeeded:
            #make sure the scripts path has been added so we can start running code.
            if self.scripts_path not in sys.path:
                sys.path.append(self.scripts_path)
                print('Add scripts path [{}] to system paths'.format(self.scripts_path))

            #make the mod file.                
            filename = os.path.join(self.install_root, (self.module_name + '.mod'))
            self.read_module_definitions(filename)
                  
            return self.update_module_definition(filename)
        
        return True
    
     
                
    def install_pymel(self):
        """Installs pymel to a common Maya location"""
        if not self.package_installed('pymel'):
            Commandline.pip_install('pymel')
        
    
    
##-----begin UI----##
    
class IconButton(QPushButton):
    def __init__(self, text, highlight=False, icon=None, success=False, *args, **kwargs):
        super(IconButton, self).__init__(QIcon(icon), text, *args, **kwargs)

        self.icon = icon
        self.highlight = highlight
        self.success = success
        self.setMinimumHeight(34)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        if self.highlight:
            font = self.font()
            font.setPointSize(14)
            font.setBold(True)
            self.setFont(font)

        if self.success:
            font = self.font()
            font.setPointSize(14)
            font.setBold(True)
            self.setFont(font)

        if self.icon:
            self.setIconSize(QSize(22, 22))
            self.setIcon(QIcon(self.AlphaImage()))

    def AlphaImage(self):
        if self.highlight and not self.success:
            AlphaImage = QPixmap(self.icon)
            painter = QPainter(AlphaImage)

            painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
            painter.fillRect(AlphaImage.rect(), '182828')

            return AlphaImage

        else:
            return QPixmap(self.icon)
        
     

class Resources(object):
    preloaderAnimBase64 = '''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'''
    BYTE_GIF = QByteArray.fromBase64( preloaderAnimBase64.encode() )
    
    company_base64 = None
    install_base64 = '''iVBORw0KGgoAAAANSUhEUgAAAFgAAABYCAYAAABxlTA0AAAABHNCSVQICAgIfAhkiAAAAAlwSFlzAAALEwAACxMBAJqcGAAAA2NJREFUeJztnN9RGzEQh3+ryTvuIHQAqSCOzn4OJUAFoYO4BKeCpAR4PkvjdGA6oATTgDYvx4xjwv3x7Z7kyX5v3N5I6w8h6eQ9AMMwDMMwDMMwDMMwDMMwDON/gHIn0JcY4+fDn733v3PlMoTiBdd1feGcewYwO7zOzNvFYvElT1b9cbkT6MI5t8aRXAAgonkI4XuGlAZRvGAANy2x+8myOJFzEPxm9PaMFcE5CD5rTLAyJlgZE6yMCVbGBCtjgpX5oNHoZrP5hr8fEPbOuZX3/kmjv6HEGK9SSuvDa865tff+Ubov8bOIGONXZn74R+g5pXS9XC5fhrQXQuC2eFVVgz5Dc7axA3B5FNoT0Vx6EIhPESml1TuhSyLa1nV9Id1nX+q6viCiLd7KBYDZ8aiWQFwwEV23xXJJfpXbkd9cut/JF7kckvvI1UJcMDNvu+6ZUvIQuX1yH4q4YOfcPYB9131TSB44cvdN7qKIC/bePzVzWVbJQ+Vq7CAApTk4t+RS5AKKi1wuySXJBZR3EVNLLk0uMME2bSrJJcoFJtoHa0suVS4wcV1EjPGq2Wt2flnJzDtmnjvnWn8pKaVZqXKBDIUnQyV3ietzT8PkcoFMlT1DJAuRRS6QsXRqQsnZ5AKZa9MmkJxVLlBA8Z+i5OxygQIEAyqSi5ALFCIYEJVcjFygIMGAiOSi5AKFCQZGSS5OLiAoWLLE/wTJo+VqvaIwWrBWif8AyaPkar+iMPqwR6vEv+cB0eiRq/2KgsRpmlqJfyP59p2w1Jyr+oqChGDVEn/v/SMRXTPz7vUaM29TSpdCC5pq/iq1adI0Ij/lzuMU1A/cY4xX2n2cyvHOQYPRgruKNVJK87F9aJFSap1jJQpRRk8RRPTcEV9tNhsw86+hlZVahBA+MvOaiNoWOBDRri3eh9GCmXnbstIDwIyI1kS0DiGM7U4Mou5HgKYScxQSU8QDenyZeYbsJQqyRwtu/uzF62pzw8wriXZEdhEppfXhPvXcYebdYrH4IdGWiODlcvnCzHON8s+pYeYtM8+l2hM/rgwh/ARwK93uRPyqqupOskHxB42qqu6Y+RZntvAx8720XEDxwL0pZ7oBcNOcihX3rweaKe2hpD26YRiGYRiGYRiGYRiGYRiGYRiGYRjD+AN6etoeN+hk/AAAAABJRU5ErkJggg=='''
    close_base64 = '''iVBORw0KGgoAAAANSUhEUgAAAFgAAABYCAYAAABxlTA0AAAABHNCSVQICAgIfAhkiAAAAAlwSFlzAAALEwAACxMBAJqcGAAAA7lJREFUeJztm8tx2zAQhv9lA3YHdiqwO4iGpM5xB6Y7UAdRKohSQeQO5DMfo3Qgd6B0IDfAzSHgjOwhJQDCgvTMfleCXPIbEI8FACiKoiiKoiiKoiiKoiiKoiiKoiiKoijKECT14LqubwAUzDwDACLatW27nM/nb1IxbWia5o6ZF8x8a95rT0SrNE1fJeKJCK7r+ieARc+ldZZlTxIxbSjL8oqItkR0//EaEd1LSA4u2NSQ3Yki67ZtF7Frcl3XN8y86ZNr2GdZ9iV03CT0A5n54UyRgoi2ZVlehY49RNM0dwB2J+QCwK1EbAnBh3NliOg+lmTzR20BXEvH6iO44CRJtjblYkh2kXumWfMmuOA0TV+ZeWNTlojukyTZm184KFVVPRpptjV3HfodAAHBAMDMhUONuGbmbUjJVVU9EtHa4ZZ1nue/QsU/RkTwfD5/Y+aZ+T1tCCbZQ+5KcugoNtHoqOv6N4DCsviBmRd5nj97xhoaf/fCzIVvLFvEBQPOkr0+PEYMH6IIBmQFTFUuEFEw4NU+LrMs+zF00Ux910R0bnLTcSCimVTeoY+oggG/Hr6vEzqVVxggulxgBMHA5ZI/i1xgJMEA0DTNVzMhsZ4ItG27SJLk+kzS5h3MvCOihyzL/vq/rT+jCQbc8wRG1q1LeWaejZmDHlUwIJeMmYJcQGgm50Kapq9ENAuZbGHmzRTkAhOowR0eHdcQo66afGQygoEgkiclF5hAE3GMR5LoGNGkjS+TEgz8l0xEW8fbDh73RGFSTQTgnlc4JmaOwZZJCb5EbsfUJE9CcFmWV0mSrHCh3A6TUxZZoXBldMEBh2cfmcSIYtROzidp4/D4wjQ5ozKaYFe5Jg8xM7lfW9GjSx6lifBJ8hxPfS+9PybRBYeS81kkR20iPKRsh6R0SSIAe5tnxdyu9S5urEBmFWMFhwS7zSjAo6PcE9FDrNWNKIJDrcMNMeUlJHHB0nI7pipZVHBd198BLG3Lh5jmuu4kIqIiTdOXS2KeQvKMxmibQaa0EUVEsGuzIPGBrpJNxxe8JosM04hoaVn0QEQzidqTZdkTM1tvBGzbdhn6HQABwVVVPcLuvEPXyfwJ/Q4deZ7/YubCpqxAsgmAgGCzb+Ec0YZJeZ4/20qWQELwyeMDXdIm5jamPM+fLZJEe4nYImc0AKz6rnX5gDH2iKVp+mKm1n2S9w47NJ0QG6Y1TfOtbdvjTmbNzJuxN4P0HPHdj3EwUlEURVEURVEURVEURVEURVEURVEURVGAf9l4XANGvwF5AAAAAElFTkSuQmCC'''

    def __init__(self):
        super(Resources, self).__init__()        
        self.installer = None
        
    def __del__(self):
        if self.installer:
            self.installer.deleteLater()
             
    @staticmethod
    def base64_to_QPixmap(base64Image):
        pixmap = QPixmap()
        byte_array =  QByteArray.fromBase64( base64Image.encode() )
        pixmap.loadFromData(byte_array)
        
        return QPixmap(pixmap)
    
    @staticmethod
    def qPixmap_to_base64(pixmap, extension):
        #https://doc.qt.io/qtforpython/index.html
        #https://forum.qt.io/topic/85064/qbytearray-to-string/2
        image = pixmap.toImage()
        byteArray = QByteArray()
        buffer = QBuffer(byteArray)
        image.save(buffer, "png")
        base64 = byteArray.toBase64().data()
        result = str(base64, encoding='utf-8')
            
        return result
            
    @staticmethod
    def file_to_base64(file_path):
        extension = os.path.basename(file_path).split('.')[-1]
        pixmap = QPixmap()
        if pixmap.load(file_path):
            return Resources.qPixmap_to_base64(pixmap, extension)
        else:
            return ''
        
    @staticmethod
    def print_file_string(image_path):
        image_string =  Resources.file_to_base64(image_path)
        if image_string:
            print ("Use the next line for the Resources.company_base64")
            print(image_string)
  
      
    def set_installer(self, installer):
        self.installer = installer
    
    
    @property
    def close_icon(self):        
        return self.base64_to_QPixmap(Resources.close_base64)
    
    @property
    def install_icon(self):        
        return self.base64_to_QPixmap(Resources.install_base64)
              
    @property
    def company_icon(self):
        result = None
        if Resources.company_base64:
            result = self.base64_to_QPixmap(Resources.company_base64)
        
        return result
    
    @company_icon.setter
    def company_icon(self, value):
        Resources.company_base64 = value
      
    
class InstallerUi(QWidget):
    def __init__(self, name, module_manager, background_color = '',
                 company_logo_size = [64, 64],
                 launch_message='', 
                 installing_message = 'Installing, please wait ...',
                 failed_message='Install Failed!',
                 success_message="Install Completed Successfully!",
                 post_error_messsage='Install Successful. Clean-up errored.  See output.',
                 show_dev_menu=False, 
                 *args, **kwargs
                 ):
        
        parent = module_manager.get_ui_parent()
        super(InstallerUi, self).__init__(parent=parent, *args, **kwargs)
        
        self.name = name
        self.module_manager = module_manager
        self.upgradable = self.module_manager.should_upgrade()
        self.uninstallable = self.upgradable or self.module_manager.uninstallable()
        self.is_uninstall = not self.upgradable and self.uninstallable
        
        self.launch_message = launch_message
        self.installing_message = installing_message
        self.failed_message = failed_message
        self.success_message = success_message
        self.post_error_messsage =  post_error_messsage
        self.show_dev_menu = show_dev_menu
        
        self.create_layout(background_color, company_logo_size)
        self.set_default_size(name)
        self.install_button.clicked.connect(self.on_action)
        self.close_button.clicked.connect(self.on_close)
        
        
        
    def contextMenuEvent(self, event):
        if not self.show_dev_menu:
            return
        
        menu = QMenu(self)

        release_action = menu.addAction("Release")
        dev_action = menu.addAction("Developer")

        release_action.setCheckable(True)
        dev_action.setCheckable(True)
        
        action_group = QActionGroup(self)
        action_group.setExclusive(True)
        
        action_group.addAction(release_action)
        action_group.addAction(dev_action)
        release_action.setChecked(not self.module_manager.dev_branch)
        dev_action.setChecked(self.module_manager.dev_branch)
        
        action = menu.exec_(self.mapToGlobal(event.pos()))
        if action is not None:
            self.module_manager.dev_branch = action==dev_action
            
            
        self.set_install_button_label()
        

    def set_default_size(self, name):
        self.animated_gif.hide()         
        self.setObjectName(name)
        self.setWindowTitle(name)
        self.setWindowModality(Qt.ApplicationModal)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setWindowFlags(Qt.Tool)
        self.setFixedSize(self.layout().minimumSize())
        self.close_button.hide()
        
        size = self.layout().minimumSize()
        width = size.width()
        height = size.height()
        desktop = QApplication.desktop()
        screenNumber = desktop.screenNumber(QCursor.pos())
        screenRect = desktop.screenGeometry(screenNumber)
        widthCenter = (screenRect.width() / 2) - (width / 2)
        heightCenter = (screenRect.height() / 2) - (height / 2)        
        self.setGeometry(QRect(widthCenter, heightCenter, width, height))
        
        
        
    def set_install_button_label(self):
        label = ''
        if self.upgradable:
            label = 'Upgrade'
            if self.module_manager.dev_branch:
                label += ' (Dev)'
                
        elif self.is_uninstall:
            label = 'Uninstall'
            
        else:
            label = 'Install'
            if self.module_manager.dev_branch:
                label += ' (Dev)'
                
        self.install_button.setText(label)
        
        
    def create_layout(self, background_color, company_logo_size):
        #background color
        if background_color:
            palette = self.palette()
            palette.setColor(self.backgroundRole(), background_color)
            self.setPalette(palette)             
        
        ##-----create all our ui elements THEN arrange them----##
        logo = None

        if RESOURCES.company_icon is not None:
            logo = QLabel()
            smallLogo = RESOURCES.company_icon.scaled(company_logo_size[0], company_logo_size[1], Qt.KeepAspectRatio, Qt.SmoothTransformation)
    
            logo.setPixmap(smallLogo)
            logo.setAlignment(Qt.AlignCenter | Qt.AlignCenter)
            logo.setMargin(15)
            
        
        self.install_button = IconButton('Install', highlight=True) #, icon=RESOURCES.install_icon)
        self.install_button.setMinimumHeight(42)
        self.close_button = IconButton(' Close', icon=RESOURCES.close_icon)
        self.close_button.setMinimumHeight(42)
        self.set_install_button_label()

        self.message_label = QLabel()
        self.message_label.setText(self.launch_message)
        self.message_label.show()
        
        self.movie = QMovie()
        self.device = QBuffer(Resources.BYTE_GIF)
        self.movie.setDevice(self.device)
        self.animated_gif = QLabel()

        self.animated_gif.setMovie(self.movie)
        self.animated_gif.setMaximumHeight(24)
        self.animated_gif.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.animated_gif.setScaledContents(True)
        self.animated_gif.setMaximumWidth(24)
        outer = QVBoxLayout()
        self.setLayout(outer)
        if logo:
            outer.addWidget(logo, 0)
            
        message_layout = QVBoxLayout()
        message_layout.addWidget(self.message_label, 1)
        message_layout.setAlignment(Qt.AlignCenter)
        outer.addLayout(message_layout)
        
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(self.install_button, 0)
        button_layout.addWidget(self.close_button, 0)
        button_layout.addWidget(self.animated_gif, 0)
        button_layout.addStretch()
        button_layout.setAlignment(Qt.AlignCenter)

        outer.addLayout(button_layout)
        self.layout()
            
    def _message(self, message):
        if self.module_manager.upgrade_action:
            return message.replace("Install", "Upgrade")
        elif self.is_uninstall:
            return message.replace('Install', 'Uninstall')
        else:
            return message
        
            
                
    def on_action(self):
        self.install_button.hide()
        #self.movie.start() #I'm thinking this causes maya to crash when debugging in WING
        self.animated_gif.show()
        self.message_label.setText(self._message(self.installing_message))
        self.message_label.show()
        self.repaint()
        
        
        if self.module_manager.pre_action(self.upgradable, self.is_uninstall):
            self.connect(self.module_manager, SIGNAL('finished()'), self.done)
            self.module_manager.start()
        else:
            self.close_button.show()
            self.animated_gif.hide()
            
            self.message_label.setText(self._message(self.failed_message))
        
    
    def done(self):
        self.close_button.show()
        self.animated_gif.hide()
        if self.module_manager.action_succeeded:
            self.message_label.setText(self._message(self.success_message))
        else:
            self.message_label.setText(self._message(self.failed_message))
         
        no_errors = self.module_manager.post_action()
        if not no_errors:
            self.message_label.setText(self._message(self.post_error_messsage))
    
        
    def on_close(self):
        self.close()
        
    def clean(self):
        self.movie.stop()
        if self.device.isOpen():
            self.device.close()

    def closeEvent(self, event):
        self.clean()
        
        
        
class MyInstaller(ModuleManager):
    def __init__(self, *args, **kwargs):
        super(MyInstaller, self).__init__(*args, **kwargs)

        
    def get_remote_package(self):
        """Users must override this with pypi name or github address"""
        return self.package_name
              
        
    
def main():
    if MAYA_RUNNING:
        MODULE_NAME = 'module name'
        MODULE_VERSION = 1.0
        PACKAGE_NAME = '' #your official pypi name goes here
        
        manager = MyInstaller(MODULE_NAME, MODULE_VERSION, package_name = PACKAGE_NAME)
        
        Resources.company_base64 = '''''' #must be surrounded by three '.  Uses Resources.print_file_string to generate a string from an iFXf00cV114ukwm9xUSVHtiM
        logo_size = [64, 64]
        background_color = '' #hex string

        global RESOURCES
        RESOURCES = Resources()
        window_name =  manager.module_name.replace("_", " ")
        installer = InstallerUi(window_name, manager, background_color=background_color, company_logo_size=logo_size, show_dev_menu=False)
        RESOURCES.set_installer(installer)

        installer.show()

           
def onMayaDroppedPythonFile(*args):
    main()
    

def run():
    """
    Run is a function used by WingIDE to execute code after telling Maya to import the module
    """    
    main()
    

if __name__ == "__main__":
    main()