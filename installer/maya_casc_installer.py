import os
import sys
import subprocess
import shutil
import stat
import traceback
import re
import getpass

#import pathlib
from pathlib import Path
import winreg
import time
import json
import ctypes.wintypes
import enum
from installer.core import ModuleEditor

from PySide6.QtCore import *
from PySide6.QtWidgets import *
from PySide6.QtGui import *
from PySide6.QtUiTools import *

from installer.installer_ui import Ui_Wizard
import installer.core as icore


#pyside6-uic D:\Users\Anderson\Documents\github\cg3d-maya-casc\installer\installer.ui -o D:\Users\Anderson\Documents\github\cg3d-maya-casc\installer\installer_ui.py



         

pip_cmd =\
"""
mod_file = ''
mod_path = ''
mod_version = ''
try:
    import maya.standalone
    import maya.cmds as cmds
    maya.standalone.initialize(name='python')
    
    modules = cmds.moduleInfo(lm=True)

    if('cascadeur' in modules):
        mod_file = cmds.moduleInfo(definition=True,moduleName='cascadeur')
        mod_path = cmds.moduleInfo(path=True,moduleName='cascadeur')
        mod_version = cmds.moduleInfo(version=True,moduleName='cascadeur')
    
    maya.standalone.uninitialize()
    
except:
    pass
    
if mod_file:
    output = f"mod%{mod_file};path%{mod_path};version%{mod_version}"
else:
    output = ''
    
print(output)
"""

def get_module_info(mayapy_path:Path)->Path:
    """See if any Maya installs exist"""
    #https://help.autodesk.com/view/MAYAUL/2024/ENU/?guid=GUID-D457D6A0-1E7F-4ED2-B0B4-8B57153B563B
    #run mayapy as a subprocess
    #https://stackoverflow.com/questions/69393513/send-commands-to-cmd-prompt-using-python-subprocess-module
    #https://www.datacamp.com/tutorial/python-subprocess
    #https://stackoverflow.com/questions/44206813/how-to-convert-function-to-str-for-python

    #cmd = pip_cmd.format(module_name)
    #print(cmd)
    
    process = subprocess.Popen([mayapy_path, "-c", pip_cmd], shell=False, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    mod_line = ''
    while process.poll() is None:
        nextline = process.stdout.readline()

        if not nextline:
            continue
             
        nextline = nextline.strip()

        if nextline.decode().startswith("mod%"):
            mod_line = nextline.decode()
        else:
            print(nextline)

    module_info ={}
    if mod_line:
        results = mod_line.split(';')
        for item in results:
            key, value = item.split("%")
            if key == 'version':
                module_info[key] = tuple([float(n)for n in value.split('.')])
            else:
                module_info[key] = Path(value)

    print(module_info)
    return module_info



def process_id(process_name):
    """Returns the process ID of the running process name or None"""
    
    import subprocess
    call = 'TASKLIST', '/FI', 'imagename eq %s' % process_name

    output = subprocess.check_output(call)
    try:
        output = output.decode()
    except UnicodeDecodeError:
        output = output.decode('latin-1')
    
    search_expression = re.compile(r'{}\D*(?P<pid>\d+)(.*)'.format(process_name))
    pids = []
    for match in re.finditer(search_expression, output):
        group_dict = match.groupdict()
        pid = group_dict.get('pid', '')
        if pid:
            pids.append(int(pid))
    
    pid = None        
    if pids:
        pids.sort()
        pid = pids[0]
        
    return pid



def get_maya_installs():
    """Look through the registry and find all Maya installations"""
    #Computer\HKEY_LOCAL_MACHINE\SOFTWARE\Autodesk\Maya\2024\AppInfo
    #Computer\HKEY_LOCAL_MACHINE\SOFTWARE\Autodesk\Maya\2024\Setup\InstallPath
    #Computer\HKEY_LOCAL_MACHINE\SOFTWARE\Classes\MayaAsciiFile\shell\open\command
    
    #Computer\HKEY_LOCAL_MACHINE\SOFTWARE\Classes\Cascadeur
    #Computer\HKEY_LOCAL_MACHINE\SOFTWARE\Classes\Cascadeur\shell\open\command
    #Computer\HKEY_LOCAL_MACHINE\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\Cascadeur
    #Computer\HKEY_LOCAL_MACHINE\SOFTWARE\WOW6432Node\Nekki Limited\Cascadeur
    maya_installs = {}
    versions = [2023,2024]
    for version in versions:
        mkey = r'SOFTWARE\Autodesk\Maya\{}\Setup\InstallPath'.format(version)
        try:
            hkey = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, mkey, 0, winreg.KEY_READ)
            value, value_type = winreg.QueryValueEx(hkey, 'MAYA_INSTALL_LOCATION')

            winreg.CloseKey(hkey)
            py_exe = Path(value).joinpath('bin', 'mayapy.exe')
            if py_exe.exists():
                maya_installs[version] = py_exe
        except Exception as e:
            pass
            #print(f"failed {e}: Maya Version->{version}")
            
    return maya_installs



def get_user_docs_path():
    #https://stackoverflow.com/questions/3858851/how-to-get-windows-special-folders-for-currently-logged-in-user
    CSIDL_PERSONAL= 5
    SHGFP_TYPE_CURRENT= 0
    buf= ctypes.create_unicode_buffer(ctypes.wintypes.MAX_PATH)
    ctypes.windll.shell32.SHGetFolderPathW(0, CSIDL_PERSONAL, 0, SHGFP_TYPE_CURRENT, buf)
    
    path = Path(buf.value)
    if not path.exists():
        path = None
        
    return path


#user_paths = None

#def get_user_paths():
    ##This doesn't work, because the user might not have write permissions.
    #global user_paths
    
    #if user_paths is not None:
        #return user_paths
    
    #user_cache = Path(__file__).parent.joinpath('user_paths.json')
    #if user_cache.exists():
        #json_file = open(user_cache)
        #user_paths = json.load(json_file)
        #json_file.close()
    
    #else:
        #user_paths = {}
        #user_paths['LOCALAPPDATA'] = os.getenv('LOCALAPPDATA')
        #user_paths['DOCUMENTS'] =  str(get_user_docs_path())
        
        #json_file = open(user_cache, 'w')
        #formatted_json = json.dumps(user_paths, indent = 4)
        #json_file.write(formatted_json)
        #json_file.close()
        
    #user_paths['LOCALAPPDATA'] = Path(user_paths['LOCALAPPDATA'])
    #user_paths['DOCUMENTS'] = Path(user_paths['DOCUMENTS'])
    
    #return user_paths
    
    

    
                


def get_default_mod_file_path():
    #docs_path = get_user_paths()['DOCUMENTS']
    docs_path = get_user_docs_path()
    return docs_path.joinpath('maya', 'modules', 'cascadeur.mod')

def get_default_maya_install_path():
    #docs_path = get_user_paths()['DOCUMENTS']
    docs_path = get_user_docs_path()
    return docs_path.joinpath('maya', 'modules', 'cascadeur')

def get_default_casc_install():
    #local_dir = get_user_paths()['LOCALAPPDATA'] 
    local_dir = Path(os.getenv('LOCALAPPDATA'))
    return local_dir.joinpath('CG_3D_Guru', 'Cascadeur')

def get_cascadeur_settings_path():
    #local_dir = get_user_paths()['LOCALAPPDATA'] 
    local_dir = Path(os.getenv('LOCALAPPDATA'))
    settings_json = local_dir.joinpath('Nekki Limited', 'cascadeur', 'settings.json')
    
    if not settings_json.exists():
        settings_json = None
        
    return settings_json



class InstallType(enum.IntEnum):
    RELEASE = enum.auto()
    TEST_RELEASE = enum.auto()
    GIT = enum.auto()
    


class Updater(QThread):
    update_complete = Signal(bool)
    permission_error = Signal()
    
    def __init__(self, casc_json: Path, casc_install: Path, mayapy: Path,
                 mod_file: Path, maya_install: Path, install_type, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self._loop = True
        self.install_type = install_type
        self.casc_json = casc_json
        self.mayapy = mayapy
        self.casc_install = casc_install #if casc_install.is_absolute() else get_default_casc_install()
        self.mod_file = mod_file #if mod_file.is_absolute() else get_default_mod_file_path()
        self.maya_install = maya_install #if maya_install.is_absolute() else get_default_maya_install_path()  

    @Slot()
    def quit(self):
        self._loop = False
      
    @Slot()
    def exit(self, retcode=0):
        super().exit(retcode=retcode)
        self._loop = False
        
    def _run_pip(self, cmds):
        print(cmds)
        process = subprocess.Popen(cmds, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        while process.poll() is None and self._loop:
            nextline = process.stdout.readline()
            nextline = nextline.strip()
            if nextline:
                print(nextline.decode())
                
            nextline = process.stderr.readline()
            nextline = nextline.strip()
            if nextline:
                print(nextline.decode())
                
                
    def _install(self, package, path):
        cmds = [str(self.mayapy), '-m', 'pip', 'install', package, f'--target={str(path)}', '--upgrade', '--force-reinstall']
        if self.install_type == InstallType.TEST_RELEASE:
            cmds.insert(4, 'https://test.pypi.org/simple/')
            cmds.insert(4, '-i')            
        
        if self.install_type != InstallType.RELEASE:
            cmds.append('--no-dependencies')
        
        self._run_pip(cmds)        


    def _run(self):
        #install maya packages
        source_prefs = None
        backup_prefs = None
        print("\nINSTALLING MAYA PACKAGES")
        print("*****************************************************")
        maya_install_path = self.maya_install    
        maya_scripts_path = maya_install_path.joinpath('scripts')
        if not maya_scripts_path.exists():
            os.makedirs(maya_scripts_path)
            
        if not maya_scripts_path.exists():
            raise FileNotFoundError(f"could't make directory:{maya_scripts_path}")
        else:
            #lets do all our pip installs
            source_prefs = maya_scripts_path.joinpath('cg3dcasc', 'preferences', 'prefs.pickle')
            if source_prefs.exists():
                print("Backing up prefs")
                backup_prefs = Path().absolute().joinpath('prefs.pickle')
                try:
                    shutil.copyfile(source_prefs, backup_prefs)
                except Exception as e:
                    print(f"Failed to backup preferences:{e}")
                    backup_prefs = None
            
            
            package = 'cg3d-maya-casc'
            if self.install_type == InstallType.GIT:
                package = r'https://github.com/Nathanieljla/cg3d-maya-casc/archive/refs/heads/main.zip'
            elif self.install_type == InstallType.TEST_RELEASE:
                package = 'cg3d-maya-casc==1.1.3rc1'
                
            self._install(package, maya_scripts_path)
    
            source = maya_scripts_path.joinpath('cg3dcasc', 'usersetup.py')
            dest = maya_scripts_path.joinpath('usersetup.py')
            if not source.exists():
                print(f"Can't find user setup file:{source}")
            else:
                shutil.copyfile(source, dest)
                
            #testing the installer in test-pypi sucks. Let's get what need need from various places 
            if self.install_type == InstallType.TEST_RELEASE:
                #Install wingcarrier & cg3d-maya-core (without dependencies), and pymel 
                self._install('wing-carrier==1.1.1', maya_scripts_path)
                self._install('cg3d-maya-core==0.7.0', maya_scripts_path)
               
                cmds = [str(self.mayapy), '-m', 'pip', 'install', 'pymel', f'--target={str(maya_scripts_path)}', '--upgrade', '--force-reinstall']
                self._run_pip(cmds)
                
            elif self.install_type == InstallType.GIT:
                #Install wingcarrier & cg3d-maya-core (without dependencies), and pymel 
                self._install('https://github.com/Nathanieljla/wing-carrier/archive/refs/heads/main.zip', maya_scripts_path)
                self._install('https://github.com/Nathanieljla/cg3d-maya-core/archive/refs/heads/main.zip', maya_scripts_path)
               
                cmds = [str(self.mayapy), '-m', 'pip', 'install', 'pymel', f'--target={str(maya_scripts_path)}', '--upgrade', '--force-reinstall']
                self._run_pip(cmds)                
                                     
            
        if backup_prefs and backup_prefs.exists():
            try:
                shutil.copyfile(backup_prefs, source_prefs)
            except Exception as e:
                print(f"Failed to restore preferences:{e}")
                backup_prefs = None
                
                         
        #Let's make sure the module def is up-to-date
        print("Working on Module Definition File")
        version = 1.0
        init_path = maya_scripts_path.joinpath('cg3dcasc', '__init__.py')
        if init_path.exists():
            version_exps = r"(VERSION.*(?P<version>\(.*\)))"
            file = open(init_path, 'r')
            text = file.read()
            file.close()
          
            for result in re.finditer(version_exps, text):
                resultDict = result.groupdict()
                if resultDict['version']:
                    pack_version = resultDict['version']
                    version = pack_version.strip("()").replace(", ", ".")
            
        m_editor = icore.ModuleEditor()  
        if self.mod_file.exists():
            m_editor.read_module_definitions(self.mod_file)
            mod_entry = m_editor.get_entry_by_path(self.maya_install)
                
            if mod_entry is not None:
                mod_entry.module_version = version
            else:
                new_def = icore.ModuleDefinition('cascadeur', version, module_path=self.maya_install)
                m_editor.add_definition(new_def)
                
            m_editor.write_module_definitions()
                     
        else:
            new_def = icore.ModuleDefinition('cascadeur', version, module_path=self.maya_install)
            m_editor.add_definition(new_def)
            m_editor.write_module_definitions(self.mod_file)        
                
        #install cascadeur packages
        print("\nINSTALLING CASCADEUR PACKAGES")
        print("*****************************************************")
        casc_install_path = self.casc_install #.joinpath('cg3dguru')
        if not casc_install_path.exists():
            os.makedirs(casc_install_path)
         
        if not casc_install_path.exists():
            raise FileNotFoundError(f"could't make directory:{casc_install_path}")
        else:
            casc_package = 'cg3d-casc-core'
            if self.install_type == InstallType.TEST_RELEASE:
                casc_package = 'cg3d-casc-core'           
            elif self.install_type == InstallType.GIT:
                casc_package = r'https://github.com/Nathanieljla/cg3d-casc-core/archive/refs/heads/main.zip'
                
            self._install(casc_package, casc_install_path)
            
            wing_package = 'wing-carrier'
            if self.install_type == InstallType.TEST_RELEASE:
                wing_package = 'wing-carrier==1.1.1'
            elif self.install_type == InstallType.GIT:
                wing_package = 'https://github.com/Nathanieljla/wing-carrier/archive/refs/heads/main.zip'
                
            self._install(wing_package, casc_install_path)

            
        print("WRAPPING STUFF UP")
        print("*****************************************************")
        #copy maya specific commands to cascadeur
        casc_site = maya_scripts_path.joinpath('cg3dcasc/casc-site')
        if casc_site.exists() and casc_install_path.exists():
            print("COPYING MAYA COMMANDS TO CASCADEUR".lower().capitalize())
            for child in casc_site.iterdir():
                dest = casc_install_path.joinpath(child.name)
                if dest.exists():
                    shutil.rmtree(str(dest))

                shutil.copytree(child, dest)
                
        #Let's update the Cascadeur settings to see the new packages
        #settings_file = self.nekki_dir.joinpath('settings.json')
        if self.casc_json.exists():
            print("MODIFYING CASCADEUR SETTINGS JSON".lower().capitalize())
            settings = open(self.casc_json)
            data = json.load(settings)
            settings.close()

            target_string = str(casc_install_path)
            #casc requires paths to be forward slashes
            target_string = target_string.replace("\\", "/")
            if target_string not in data['Python']['Path']:
                data['Python']['Path'].append(target_string)
                
            if 'cg3dcmds' not in data['Python']['Commands']:
                data['Python']['Commands'].append('cg3dcmds')

            read_state = os.stat(self.casc_json).st_mode
            os.chmod(self.casc_json, stat.S_IWRITE)
            
            settings = open(self.casc_json, 'w')
            formatted_json = json.dumps(data, indent = 4)
            settings.write(formatted_json)
            settings.close()
    
            os.chmod(self.casc_json, read_state)


    def run(self):
        #import stat #I'm having to re-import this for some reason. WTF?!
        
        
        #def bad_path(m_path):
            #if m_path == m_path.parent:
                ##we're at the top of the harddrive
                #return True
            
            #elif not m_path.exists():
                #return bad_path(m_path.parent)
            
            #if not os.access(m_path, os.R_OK | os.W_OK | os.X_OK):
                #print(f"Can't read/write to {m_path}. Check your user permissions.")
                #return True
            #return False
                
        #if bad_path(self.casc_install) or \
           #bad_path(self.mod_file) or bad_path(self.maya_install) :
            #print("Action Failed")
            #return          
        
        
                
        #target_files = [self.casc_json]
        #file_stats = [os.stat(f).st_mode for f in target_files]
        
        print("*****************************************************")
        print(f"Python exe:  {self.mayapy}\n")
        print(f"CASC Settings:  {self.casc_json}")
        print(f"CASC Packages Folder:  {self.casc_install}\n")

        print(f"MAYA Mod File:  {self.mod_file}")
        print(f"MAYA Module Folder:  {self.maya_install}")
        print("*****************************************************\n")
        
        try:
            #for a_f in target_files:
                #os.chmod(a_f, stat.S_IWRITE)            
            
            self._run()
            print("*****************************************************")
            print("INSTALL COMPLETED SUCCESSFULLY !!")
            print("*****************************************************")
            self.update_complete.emit(True)
        except PermissionError as e:
            print("\n")
            print("*****************************************************")
            print(f"Installing FAILED !! : {e}")          
            print("*****************************************************")
            callstack = traceback.format_exc()
            print(callstack)
            self.permission_error.emit()
        except Exception as e:
            print("\n")
            print("*****************************************************")
            print(f"Installing FAILED !! : {e}")          
            print("*****************************************************")
            callstack = traceback.format_exc()
            print(callstack)            
            self.update_complete.emit(False)
        #finally:
            #for idx, stat in enumerate(file_stats):
                #os.chmod(target_files[idx], file_stats[idx])
    
    
class Remover(QThread):
    removal_complete = Signal(bool)
    
    def __init__(self, casc_json: Path, casc_install: Path, mayapy: Path,
                 mod_file: Path, maya_install: Path, dev, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self._loop = True        
        self.dev = dev
        self.casc_json = casc_json
        self.mayapy = mayapy
        self.casc_install = casc_install if casc_install.is_absolute() else get_default_casc_install()
        self.mod_file = mod_file if mod_file.is_absolute() else get_default_mod_file_path()
        self.maya_install = maya_install if maya_install.is_absolute() else get_default_maya_install_path()
        
    @Slot()
    def quit(self):
        self._loop = False
      
    @Slot()
    def exit(self, retcode=0):
        super().exit(retcode=retcode)
        self._loop = False
        

    def _run(self):
        print("Removing Install")
        m_editor = icore.ModuleEditor()  
        if self.mod_file.exists():
            m_editor.read_module_definitions(self.mod_file)
            mod_entry = m_editor.get_entry_by_path(self.maya_install)
            if mod_entry is not None:
                m_editor.remove_definition(mod_entry)
                
            if m_editor.is_empty():
                print("Deleting Mod file")
                self.mod_file.unlink()

        print("Cleaning Cascadeur settings json")   
        settings = open(self.casc_json)
        data = json.load(settings)
        settings.close()

        target_string = str(self.casc_install)
        #casc requires paths to be forward slashes
        target_string = target_string.replace("\\", "/")
        if target_string in data['Python']['Path']:
            data['Python']['Path'].remove(target_string)
            
        if 'cg3dcmds' in data['Python']['Commands']:
            data['Python']['Commands'].remove('cg3dcmds')

        read_state = os.stat(self.casc_json).st_mode
        os.chmod(self.casc_json, stat.S_IWRITE)
        
        settings = open(self.casc_json, 'w')
        formatted_json = json.dumps(data, indent = 4)
        settings.write(formatted_json)
        settings.close()

        os.chmod(self.casc_json, read_state)

        print("Deleting folders. Please wait for success message.")
        shutil.rmtree(self.maya_install, ignore_errors=True)   
        shutil.rmtree(self.casc_install, ignore_errors=True)
        
        
    def run(self):
        try:
            self._run()
            print("*****************************************************")
            print("REMOVAL COMPLETED SUCCESSFULLY !!")
            print("*****************************************************")
            self.removal_complete.emit(True)
        except Exception as e:
            print("\n")
            print("*****************************************************")
            print(f"REMOVAL FAILED !! : {e}")          
            print("*****************************************************")
            callstack = traceback.format_exc()
            print(callstack)            
            self.removal_complete.emit(False)



class WorkerSignals(QObject):
    #https://discourse.techart.online/t/communicating-with-maya-standalone/15029/4
    #https://www.pythonguis.com/tutorials/multithreading-pyside-applications-qthreadpool/
    progress_start = Signal(str, int)
    progress_update = Signal(int, str)
    progress_step = Signal()
    path_info = Signal(Path, dict)
    module_search_complete = Signal()
    
    
worker_signals = WorkerSignals()



class ProgressUpdater(QThread):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._loop = True
    
    @Slot()
    def quit(self):
        self._loop = False
      
    @Slot()
    def exit(self, retcode=0):
        super().exit(retcode=retcode)
        self._loop = False

    def run(self):
        while self._loop:
            worker_signals.progress_step.emit()
            time.sleep(.5)



class PathFinder(QRunnable):
    def __init__(self):
        super(PathFinder, self).__init__()

        self.maya_path = Path()
        self.updater = ProgressUpdater()
        
        
    def set_maya_path(self, path):
        self.maya_path = path
        
        
    @Slot()  # QtCore.Slot
    def run(self):
        mayapy_path = None
        module_info = None          
        try:
            if self.maya_path.is_absolute() and self.maya_path.exists():
                mayapy_path = self.maya_path
                worker_signals.progress_start.emit("Checking Maya", 50)
                self.updater.start()
                found_info = get_module_info(mayapy_path)
                if found_info:
                    module_info = found_info
                
            else:
                worker_signals.progress_start.emit("Finding Maya Installs", 50)
                self.updater.start()
                maya_installs = get_maya_installs()
                
                if maya_installs:
                    #Find out if any version of Maya already has the bridge installed
                    version_keys = list(maya_installs.keys())
                    version_keys.sort()
                    version_keys.reverse()
                    worker_signals.progress_start.emit("Checking Maya for bridge", 50)
                    for idx, key in enumerate(version_keys):
                        worker_signals.progress_update.emit(idx+1, f"Checking Maya {key}")
                        
                        found_info = get_module_info(maya_installs[key])
                        if found_info:
                            mayapy_path = maya_installs[key]
                            module_info = found_info
                            break
        except Exception as e:
            print(f'Path finder failed: {e}')
            callstack = traceback.format_exc()
            print(callstack)              
                
        self.updater.quit()
        worker_signals.path_info.emit(mayapy_path, module_info)
        worker_signals.module_search_complete.emit()
        
        

class Logger(QThread):
    #logger : https://stackoverflow.com/questions/14058453/making-python-loggers-output-all-messages-to-stdout-in-addition-to-log-file
    #https://betterstack.com/community/guides/logging/how-to-start-logging-with-python/    
    log_output = Signal(str)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._loop = True
        self.output = ''
        self.permission_error = False
    
    def write(self, input_string):
        self.output += input_string
        
    def flush(self, *args, **kwargs):
        pass
    
    @Slot()
    def quit(self):
        self._loop = False
      
    @Slot()
    def exit(self, retcode=0):
        super().exit(retcode=retcode)
        self._loop = False

    def run(self):
        while self._loop:
            if self.output:
                self.log_output.emit(self.output)
                self.output = ''
                
                

class PathType(enum.Enum):
    CASC_JSON = enum.auto()
    CASC_INSTALL = enum.auto()
    MAYAPY = enum.auto()
    MOD_FILE = enum.auto()
    MOD_INSTALL = enum.auto()
    TEST_LOCAL = enum.auto()



class MainWindow(QWizard):
    def __init__(self, *args):
        super(MainWindow, self).__init__()

        self.ui = Ui_Wizard()
        self.ui.setupUi(self)
        self.logger = Logger()
        self.logger.start()
        sys.stdout = self.logger
        self.module_editor = ModuleEditor()

        self.page_one_init = False
        self.page_two = None
        
        self.casc_json_path = Path()
        self.casc_module_path = Path()        
        
        self.output_window = None
        self.mayapy_path = Path()
        self.maya_mod_file_path = Path()
        self.maya_mod_install_path = Path()
        self.module_info = None
        self.install_type = InstallType.RELEASE
        self.test_location = getpass.getuser() == 'Anderson' and Path(r'D:\Users\Anderson\Documents\github').exists()
        self.auto_hide_controls = True
        self.searching = False
        self.threadpool = QThreadPool()
        self.path_finder = PathFinder()
        self.running_thread: QThread = None

        self.ui.casc_json_set.pressed.connect(lambda: self.get_file(
            PathType.CASC_JSON, self.ui.casc_json_value, self.read_casc_settings, "JSON (*.json)")
        )
        self.ui.py_path_set.pressed.connect(lambda: self.get_file(
            PathType.MAYAPY, self.ui.py_path_value, None, "application (mayapy.exe)")
        )
        self.ui.maya_mod_set.pressed.connect(lambda: self.get_file(
            PathType.MOD_FILE, self.ui.maya_mod_value, self.read_mod_file, "Maya mod file (*.mod)", True)
        )
        
        self.ui.casc_install_set.pressed.connect(lambda: self.get_folder(PathType.CASC_INSTALL, self.ui.casc_install_value))
        self.ui.maya_install_set.pressed.connect(lambda: self.get_folder(PathType.MOD_INSTALL, self.ui.maya_install_value))

        worker_signals.progress_start.connect(self.show_progress)
        worker_signals.progress_update.connect(self.update_progress)
        worker_signals.path_info.connect(self.set_paths)
        worker_signals.progress_step.connect(self.step_progress)
        worker_signals.module_search_complete.connect(self.search_complete)
        self.ui.find_module_button.pressed.connect(self.find_modules)
        self.logger.log_output.connect(self.log)
        self.ui.console_spacer.setVisible(False)
        
        if args:
            print(args)        

        
    def read_mod_file(self):
        file_read = self.module_editor.read_module_definitions(self.maya_mod_file_path)
        if file_read:
            installs = self.module_editor.get_install_paths()
            if installs:
                self.maya_mod_install_path = installs[0]
                self.ui.maya_install_value.setText(str(self.maya_mod_install_path))
                
                
    def get_folder(self, path_type, text_ctrl):
        start_dir = ''  
        if path_type == PathType.CASC_INSTALL:
            if self.is_path(self.casc_module_path):
                start_dir = str(self.casc_module_path)
            else:
                start_dir = str(get_user_docs_path())
        elif path_type == PathType.MOD_INSTALL:
            if self.is_path(self.maya_mod_install_path):
                start_dir = str(self.maya_mod_install_path)
            elif self.is_path(self.maya_mod_file_path):
                start_dir = str(self.maya_mod_file_path)
            else:
                start_dir = str(get_user_docs_path())
            
        file_path = QFileDialog.getExistingDirectory(self, 'pick install location', start_dir)
        if not file_path:
            return    
    
        text_ctrl.setText(file_path)
        file_path = Path(file_path)
        
        if path_type == PathType.CASC_INSTALL:
            self.casc_module_path = file_path
        elif path_type == PathType.MOD_INSTALL:
            self.maya_mod_install_path = file_path
            
        self.update_status()
        
        
    def get_file(self, path_type, text_ctrl, callback=None, filters=None, get_save=False):
        if filters is None:
            filters = "All (*.*)"
            
        dial = QFileDialog.getOpenFileName
        if get_save:
            dial = QFileDialog.getSaveFileName
            
        file_path, extension = dial(self, 'pick file', filter=filters)
        if not file_path:
            return
        
        text_ctrl.setText(file_path)
        file_path = Path(file_path)
        
        if path_type == PathType.CASC_JSON:
            self.casc_json_path = file_path
        elif path_type == PathType.MAYAPY:
            self.mayapy_path = file_path
        elif path_type == PathType.MOD_FILE:
            self.maya_mod_file_path = file_path

        if callback is not None:
            callback()
        
        self.update_status()

        
    def set_install_type(self, value):
        self.install_type = value
        
        
    def toggle_test_local(self):
        self.test_location = not self.test_location
        
        
    def contextMenuEvent(self, event):
        menu = QMenu(self)        

        release_action = menu.addAction("Release", lambda: self.set_install_type(InstallType.RELEASE))
        test_action = menu.addAction("Test Release", lambda: self.set_install_type(InstallType.TEST_RELEASE))
        git_action = menu.addAction("Git", lambda: self.set_install_type(InstallType.GIT))
        test_local_action = menu.addAction("Test Location", self.toggle_test_local )

        release_action.setCheckable(True)
        test_action.setCheckable(True)
        git_action.setCheckable(True)
        test_local_action.setCheckable(True)
        
        action_group = QActionGroup(self)
        action_group.setExclusive(True)
        
        action_group.addAction(release_action)
        action_group.addAction(git_action)
        action_group.addAction(test_action)
        release_action.setChecked(self.install_type == InstallType.RELEASE)
        git_action.setChecked(self.install_type == InstallType.GIT)
        test_action.setChecked(self.install_type==InstallType.TEST_RELEASE)
        test_local_action.setChecked(self.test_location)
        
        menu.insertSeparator(test_local_action)
        
        menu.exec(self.mapToGlobal(event.pos()))


    def show_console(self, show):
        self.ui.console_output.setVisible(show)
        self.ui.console_spacer.setVisible(not show)

        
    def search_complete(self):
        self.searching = False
        self.ui.progress_bar.setVisible(False)
        self.ui.find_module_button.setVisible(False)
        self.ui.console_output.clear()
        self.show_layout(self.ui.progress_group, False)
        
        
    def permission_error(self):
        self.install_complete(False)
        print("----STOP!----Please read carefully.")
        print("You don't have permission to write to the necessary directories.\nTo fix this you'll need to do 4 steps:")
        print("1. Copy the path locations listed below")
        print("2. Restart this application by right-clicking on the EXE and choosing 'Run as Adminstrator'")
        print("3. Have someone with Adminstrator privileges complete the pop-up box")
        print("4. Replace all default paths with the paths printed below. Use the Set button.")
        print("-------------------")     
        print(f"Cascaduer: Settings File: {self.casc_json_path}")
        print(f"Cascaduer: Install Location: {self.casc_module_path}")
        print(f"Maya: Module File: {self.maya_mod_file_path}")
        print(f"Maya: Install Location: {self.maya_mod_install_path}")
        
        
    def find_modules(self):
        if not self.searching:
            #self.show_console(True)
            self.searching = True
            self.ui.progress_bar.setVisible(True)
            self.path_finder.set_maya_path(self.mayapy_path)
            self.threadpool.start(self.path_finder)
        
        
    def log(self, input_string):
        self.output_window.append(input_string)
        #self.ui.console_output.append(input_string)
        

    def show_progress(self, label, max_steps):
        self.show_layout(self.ui.progress_group, True)
        self.ui.progress_label.setText(label)
        self.ui.progress_bar.setMaximum(max_steps)
        self.ui.progress_bar.setValue(0)
        
        
    def hide_progress(self):
        self.show_layout(self.ui.progress_group, False)
        
        
    def update_progress(self, value, label=None):
        if label:
            self.ui.progress_label.setText(label)
            
        self.ui.progress_bar.setValue(value)
        
        
    def step_progress(self):
        value = self.ui.progress_bar.value()+1
        if value > self.ui.progress_bar.maximum():
            value = 0
        self.ui.progress_bar.setValue( value )
        
        
    def show_layout(self, layout: QLayout, show: bool):
        if hasattr(layout, 'setVisible'):
            layout.setVisible(show)
            
        else:   
            for idx in range(0, layout.count()):
                item = layout.itemAt(idx).widget()
                if hasattr(item, 'setVisible'):
                    item.setVisible(show)
                    
        layout.layout()
        
        
    def check_running_apps(self):
        apps_running = True
        continue_action = False
        while apps_running:
            casc_running = process_id('cascadeur.exe') is not None
            maya_running = process_id('maya.exe') is not None
            
            if casc_running or maya_running:
                message = 'Please close:\n'
                if casc_running:
                    message += '    Cascadeur\n'
                if maya_running:
                    message += '    Maya\n'
                message += '\nThen hit OK'
                result = QMessageBox.critical(self, 'Close Apps', message,QMessageBox.StandardButton.Ok|QMessageBox.StandardButton.Cancel)
                if result == QMessageBox.StandardButton.Cancel:
                    continue_action = False
                    break
            else:
                apps_running = False
                continue_action = True
                
        return continue_action
            
            
    def is_path(self, path: Path):
        return path.is_absolute() and path.exists()
            
            
    def update_status(self):
        self.ui.console_output.clear()
        cascadeur_ready = self.is_path(self.casc_json_path)
        maya_ready = self.is_path(self.mayapy_path)
        
        casc_installed = self.is_path(self.casc_module_path.joinpath('cg3dmaya'))
        mod_file_installed = self.is_path(self.maya_mod_file_path)
        mod_installed = self.is_path(self.maya_mod_install_path.joinpath('scripts'))
        upgrading = casc_installed or mod_file_installed or mod_installed
        
        #if mod_file_installed and mod_installed:
            #self.ui.find_module_button.setVisible(False)
            ##self.ui.maya_mod_value.setVisible(False)
            ##self.ui.maya_mod_label.setVisible(False)
        #else:
            #self.ui.find_module_button.setVisible(True)
            #self.ui.maya_mod_value.setVisible(True)
            #self.ui.maya_mod_label.setVisible(True)
            
        #self.ui.casc_json_set.setVisible(not cascadeur_ready)
        
        if upgrading:
            self.ui.install_option.setText("Upgrade/Repair")
            self.ui.install_option.setVisible(True)
            self.ui.remove_option.setVisible(True)

        else:
            self.ui.install_option.setText('Install')
            self.ui.install_option.setChecked(True)
            self.ui.install_option.setVisible(False)
            self.ui.remove_option.setVisible(False)

        #This is dump, because if you run as admin, and the admin
        #has a path then you can't set it to your local folders.
        #if casc_installed:
            #self.ui.casc_install_set.setVisible(False)
        #else:
            #self.ui.casc_install_set.setVisible(True)
            
        #if mod_file_installed:
            #self.ui.maya_mod_set.setVisible(False)
            
        #if mod_installed:
            #self.ui.maya_install_set.setVisible(False)
            
            
        if cascadeur_ready and maya_ready:
            if upgrading:
                print("Select Upgrade/Repair or Remove then hit 'Next'")
                if not mod_file_installed or not casc_installed or not mod_installed:
                    print("\nWARNING: Some info is missing:")
                
                    if not casc_installed:
                        #This should probably never appear, but just in case.
                        print("    The custom cascadeur install location")
                    
                    suggest = False
                    if not mod_file_installed:
                        print('    The custom module FILE location')
                        suggest = True
                        
                    if not mod_installed:
                        print("    The custom module FOLDER location")
                        suggest = True
                     
                    print("")   
                    if suggest:
                        print("Hitting the 'find paths for me' button can help you with this\n")
                        
                    print("Without this information a repair will install to the default locations")
                    print("Without this information a REMOVE might not properly uninstall everything")
                
            else:
                print("Hit 'Next' to install.")
                print("IF you know everything is already installed then hit the 'Advanced Search' button.")
                                 
        self.currentPage().isComplete()

            
    def read_casc_settings(self):
        try:  
            with open(self.casc_json_path) as json_file:
                data = json.load(json_file)
    
                for entry in data['Python']['Path']:
                    entry = Path(entry)
                    module_path = entry.joinpath('cg3dmaya')
                    if module_path.exists():
                        self.casc_module_path = entry
                        break
        except:
            return
        
        if self.is_path(self.casc_module_path):
            self.ui.casc_install_value.setText(str(self.casc_module_path))        


    def init_page_one(self):
        self.ui.casc_json_value.setReadOnly(True)
        self.ui.casc_install_value.setReadOnly(True)
        self.ui.py_path_value.setReadOnly(True)
        #self.ui.maya_mod_value.setText("----FOR Advanced Users ONLY----")
        self.ui.maya_mod_value.setReadOnly(True)
        self.ui.maya_install_value.setReadOnly(True)
        self.show_layout(self.ui.progress_group, False)
        
        if self.page_one_init:
            return
        
        self.currentPage().set_parent(self)
        self.page_one_init = True
        
        self.show_layout(self.ui.progress_group, False)
        #find cascaduer paths
        settings_json = get_cascadeur_settings_path()
        if settings_json:
            self.casc_json_path = settings_json
            self.read_casc_settings()
                        
        json_path = str(self.casc_json_path)
        self.ui.casc_json_value.setText(json_path)
        
        if not self.is_path(self.casc_module_path):
            self.casc_module_path = get_default_casc_install()
            
        self.ui.casc_install_value.setText(str(self.casc_module_path)) 
     
        #find maya paths 
        maya_installs = get_maya_installs()
        if maya_installs:
            #Find out of any version of Maya already has the bridge installed
            version_keys = list(maya_installs.keys())
            version_keys.sort()
            version_keys.reverse()
            
            self.mayapy_path = maya_installs[version_keys[0]]
            self.ui.py_path_value.setText(str(self.mayapy_path))
          
            #self.casc_install = casc_install #if casc_install.is_absolute() else get_default_casc_install()
        self.maya_mod_file_path = get_default_mod_file_path()
        self.ui.maya_mod_value.setText(str(self.maya_mod_file_path))
        
        self.maya_mod_install_path = get_default_maya_install_path()
        if not self.maya_mod_install_path.exists() and self.maya_mod_file_path.exists():
            self.read_mod_file()
        else:
            self.ui.maya_install_value.setText(str(self.maya_mod_install_path))      
            
        self.update_status()
        
        
    def install_complete(self, successful):
        self.page_two.mark_complete()
        
        
    def init_page_two(self):
        if self.page_two is None:
            self.page_two = self.currentPage()
            self.page_two.set_parent(self)

        if self.running_thread is not None and self.running_thread.isRunning():
            return
        
        if not self.check_running_apps():
            print("Action Skipped due to running apps.")
            return        
        
        json_path = self.casc_json_path
        casc_mod_path = self.casc_module_path
        mod_file = self.maya_mod_file_path
        maya_mod_path = self.maya_mod_install_path
                
        if self.test_location:
            folder_path = QFileDialog.getExistingDirectory(self, 'Pick install location')
            if not folder_path:
                return
            
            folder_path = Path(folder_path)
            new_local = folder_path.joinpath('settings.json')
            shutil.copyfile(json_path, new_local)
            json_path = new_local
            
            casc_mod_path = folder_path.joinpath('CG_3D_Guru', 'Cascadeur')
            mod_file = folder_path.joinpath('cascadeur.mod')
            maya_mod_path = folder_path.joinpath('maya_cascadeur')
            
                    
        if self.ui.install_option.isChecked():
            self.running_thread = Updater(json_path, casc_mod_path,
                           self.mayapy_path, mod_file,
                           maya_mod_path, self.install_type)
            
            self.running_thread.update_complete.connect(self.install_complete)
            self.running_thread.permission_error.connect(self.permission_error)
            self.running_thread.start()
        else:
            self.running_thread = Remover(json_path, casc_mod_path,
                           self.mayapy_path, mod_file,
                           maya_mod_path, self.install_type)
            
            self.running_thread.removal_complete.connect(self.install_complete)
            self.running_thread.start()
            
        
        
    def initializePage(self, page_id):
        if page_id == 0:
            self.output_window = self.ui.console_output
            self.init_page_one()
        if page_id == 1:
            self.output_window = self.ui.result_output
            self.output_window.clear()

            self.init_page_two()
            
            
    def set_paths(self, mayapy_path, module_info):
        self.mayapy_path = mayapy_path
        self.module_info = module_info
      
        self.show_layout(self.ui.maya_group, True)
        self.show_layout(self.ui.progress_group, False)
        if isinstance(mayapy_path, Path):
            self.mayapy_path = mayapy_path
            self.ui.py_path_value.setText(str(mayapy_path))

        if self.module_info:
            path = self.module_info['mod']
            if isinstance(path, Path):
                self.maya_mod_file_path = path
                self.ui.maya_mod_value.setText(str(path))
   
            path = self.module_info['path']
            if isinstance(path, Path):
                self.maya_mod_install_path = path
                self.ui.maya_install_value.setText(str(path))
    
        self.update_status()    



def run():
    #https://gist.github.com/PaulCreusy/7fade8d5a8026f2228a97d31343b335e
    #https://signmycode.com/comodo-individual-code-signing
    #https://cheapsslsecurity.com/p/standard-vs-individual-vs-ev-code-signing-certificates/
    #get_module_info(pathlib.Path(r'C:\Program Files\Autodesk\Maya2024\bin\mayapy.exe'))
    args = sys.argv
    app = QApplication(args)
    app.setStyle('Fusion')
    window = MainWindow()
    window.show()
    app.exec()
 
if __name__ == '__main__':
    #commandline auto-py-to-exe
    run()
    
    
    #import ctypes, sys
    
    #def is_admin():
        #return Path(__file__).parent.joinpath('user_paths.json').exists()
        
        ##try:
            ##return ctypes.windll.shell32.IsUserAnAdmin()
        ##except:
            ##return False
    
    #if is_admin():
        ## Code of your program here
        #run()
    #else:
        #get_user_paths()
        ## https://stackoverflow.com/questions/130763/request-uac-elevation-from-within-a-python-script
        # Re-run the program with admin rights
        ##ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
    
    
    