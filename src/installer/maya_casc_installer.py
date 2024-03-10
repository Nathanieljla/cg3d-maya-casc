import sys
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

#pyside6-uic D:\Users\Anderson\Documents\github\cg3d-maya-casc\src\installer\installer.ui -o D:\Users\Anderson\Documents\github\cg3d-maya-casc\src\installer\installer_ui.py



def get_cascadeur_settings_path():
    import os
    local_dir = Path(os.getenv('LOCALAPPDATA'))
    settings_json = local_dir.joinpath('Nekki Limited', 'cascadeur', 'settings.json')
    
    if not settings_json.exists():
        settings_json = None
        
    return settings_json



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
    


#logger : https://stackoverflow.com/questions/14058453/making-python-loggers-output-all-messages-to-stdout-in-addition-to-log-file
#https://betterstack.com/community/guides/logging/how-to-start-logging-with-python/
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
    
output = f"mod%{mod_file};path%{mod_path};version%{mod_version}"
print(output)
"""

def get_module_info(mayapy_path:Path)->Path:
    """See if any Maya installs exist"""
    #https://help.autodesk.com/view/MAYAUL/2024/ENU/?guid=GUID-D457D6A0-1E7F-4ED2-B0B4-8B57153B563B
    #run mayapy as a subprocess
    #https://stackoverflow.com/questions/69393513/send-commands-to-cmd-prompt-using-python-subprocess-module
    #https://www.datacamp.com/tutorial/python-subprocess
    #https://stackoverflow.com/questions/44206813/how-to-convert-function-to-str-for-python
    import subprocess
    
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



def install_repair(casc_json: Path, casc_install: Path, mayapy: Path,
                  mode_file: Path, maya_install: Path, dev):
    
    update_casc = casc_install.joinpath('cg3dguru').exists()
    if update_casc:
        print("Updating/Reparing cascadeur packages")
        pass
    
    
    
def remove(casc_json: Path, casc_install: Path, mayapy: Path,
                  mode_file: Path, maya_install: Path, dev):
    if dev:
        print("remove dev")
        return



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
                
        self.updater.quit()
        worker_signals.path_info.emit(mayapy_path, module_info)
        worker_signals.module_search_complete.emit()
        
        

class Logger(QThread):
    log_output = Signal(str)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._loop = True
        self.output = ''
    
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



class MainWindow(QWizard):
    def __init__(self):
        super(MainWindow, self).__init__()
        
        self.ui = Ui_Wizard()
        self.ui.setupUi(self)
        self.logger = Logger()
        self.logger.start()
        sys.stdout = self.logger
        self.module_editor = ModuleEditor()

        self.page_one_init = False
        self.casc_json_path = Path()
        self.casc_module_path = Path()        
        
        self.output_window = None
        self.mayapy_path = Path()
        self.maya_mod_file_path = Path()
        self.maya_mod_install_path = Path()
        self.module_info = None
        self.dev_install = True
        self.auto_hide_controls = True
        self.searching = False
        self.threadpool = QThreadPool()
        self.path_finder = PathFinder()

        self.ui.casc_json_set.pressed.connect(lambda: self.get_file(
            PathType.CASC_JSON, self.ui.casc_json_value, self.read_casc_settings, "JSON (*.json)")
        )
        self.ui.py_path_set.pressed.connect(lambda: self.get_file(
            PathType.MAYAPY, self.ui.py_path_value, None, "application (mayapy.exe)")
        )
        self.ui.maya_mod_set.pressed.connect(lambda: self.get_file(
            PathType.MOD_FILE, self.ui.maya_mod_value, self.read_mod_file, "Maya mod file (*.mod)")
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
        
        
    def get_file(self, path_type, text_ctrl, callback=None, filters=None):
        if filters is None:
            filters = "All (*.*)"
            
        file_path, extension = QFileDialog.getOpenFileName(self, 'pick file', filter=filters)
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

        
    def set_dev(self, value):
        self.dev_install = value
        
        
    def contextMenuEvent(self, event):
        menu = QMenu(self)        

        release_action = menu.addAction("Release", lambda: self.set_dev(False))
        dev_action = menu.addAction("Developer", lambda: self.set_dev(True))

        release_action.setCheckable(True)
        dev_action.setCheckable(True)
        
        action_group = QActionGroup(self)
        action_group.setExclusive(True)
        
        action_group.addAction(release_action)
        action_group.addAction(dev_action)
        release_action.setChecked(not self.dev_install)
        dev_action.setChecked(self.dev_install)
        
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
        mod_installed = self.is_path(self.maya_mod_install_path)
        upgrading = casc_installed or mod_file_installed or mod_installed
        
        if upgrading:
            self.ui.install_option.setText("Upgrade/Repair")
            self.ui.install_option.setVisible(True)
            self.ui.remove_option.setVisible(True)

        else:
            self.ui.install_option.setText('Install')
            self.ui.install_option.setChecked(True)
            self.ui.install_option.setVisible(False)
            self.ui.remove_option.setVisible(False)

        if casc_installed:
            self.ui.casc_install_set.setVisible(False)
        else:
            self.ui.casc_install_set.setVisible(True)
            
        if mod_file_installed:
            self.ui.maya_mod_set.setVisible(False)
            
        if mod_installed:
            self.ui.maya_install_set.setVisible(False)
            
        if cascadeur_ready and maya_ready:
            if upgrading:
                print("Select Upgrade/Repair or Remove then hit 'Next'")
            else:
                print("Hit 'Next' to install.")
                                 
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
        
        module_path = str(self.casc_module_path)
        self.ui.casc_install_value.setText(module_path)        


    def init_page_one(self):
        self.ui.casc_json_value.setReadOnly(True)
        self.ui.casc_install_value.setReadOnly(True)
        self.ui.py_path_value.setReadOnly(True)
        self.ui.maya_mod_value.setReadOnly(True)
        self.ui.maya_install_value.setReadOnly(True)
        self.show_layout(self.ui.progress_group, False)
        
        if self.page_one_init:
            return
        
        self.currentPage().set_parent(self)
        self.page_one_init = True
        #if True:
            #self.update_status()
            #return
        
        self.show_layout(self.ui.progress_group, False)
        #find cascaduer paths
        settings_json = get_cascadeur_settings_path()
        if settings_json:
            self.casc_json_path = settings_json
            self.read_casc_settings()
                    
        json_path = str(self.casc_json_path)
        self.ui.casc_json_value.setText(json_path)
     
        #find maya paths 
        maya_installs = get_maya_installs()
        if maya_installs:
            #Find out of any version of Maya already has the bridge installed
            version_keys = list(maya_installs.keys())
            version_keys.sort()
            version_keys.reverse()
            
            self.mayapy_path = maya_installs[version_keys[0]]
            self.ui.py_path_value.setText(str(self.mayapy_path))
            
        docs_path = get_user_docs_path()
        if docs_path:
            mod_path = docs_path.joinpath('maya', 'modules', 'cascadeur.mod')
            if mod_path.exists():
                self.maya_mod_file_path = mod_path
                self.ui.maya_mod_value.setText(str(mod_path))
                
            maya_install_path = docs_path.joinpath('maya', 'modules', 'cascadeur')
            if maya_install_path.exists():
                self.maya_mod_install_path = maya_install_path
                self.ui.maya_install_value.setText(str(maya_install_path))
                
            elif mod_path.exists():
                #Let's open the mod file to find the location of the install
                self.read_mod_file()
            
            
        self.update_status()
        
        
    def initializePage(self, page_id):
        if page_id == 0:
            self.output_window = self.ui.console_output
            self.init_page_one()
        if page_id == 1:
            self.output_window = self.ui.result_output
            continue_install = self.check_running_apps()
            if not continue_install:
                print('Install Canceled')
                return
            
            if self.ui.install_option.isChecked():
                install_repair(self.casc_json_path, self.casc_module_path,
                               self.mayapy_path, self.maya_mod_file_path,
                               self.maya_mod_install_path, self.dev_install)
            else:
                remove(self.casc_json_path, self.casc_module_path,
                       self.mayapy_path, self.maya_mod_file_path,
                       self.maya_mod_install_path, self.dev_install)

                
            
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