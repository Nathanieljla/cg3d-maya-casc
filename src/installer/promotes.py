from PySide6.QtCore import *
from PySide6.QtWidgets import *
from PySide6.QtGui import *
from PySide6.QtUiTools import *

import pathlib

                
class PathsPage(QWizardPage):
    def __init__(self, parent=None):
        super(PathsPage, self).__init__(parent)
        self.parent = parent
        self.complete = False
        
        
    def set_parent(self, parent):
        self.parent = parent
               
        
    def isComplete(self):
        if not self.parent:
            return False
        
        enable_next = self.parent.is_path(self.parent.casc_json_path) and self.parent.is_path(self.parent.mayapy_path)
        #enable_next = enable_next and self.parent.mayapy_path.is_absolute() and self.parent.mayapy_path.exists()
        if enable_next != self.complete:
            self.complete = enable_next
            self.completeChanged.emit()
            
        return self.complete
