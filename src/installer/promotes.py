from PySide6.QtCore import *
from PySide6.QtWidgets import *
from PySide6.QtGui import *
from PySide6.QtUiTools import *

                
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
        if enable_next != self.complete:
            self.complete = enable_next
            self.completeChanged.emit()
            
        return self.complete
    
    
    
class LastPage(QWizardPage):
    def __init__(self, parent=None):
        super(LastPage, self).__init__(parent)
        self.parent = parent
        self.complete = False
        
        
    def set_parent(self, parent):
        self.parent = parent
        
        
    def mark_complete(self):
        self.complete = True
        self.completeChanged.emit()
               
        
    def isComplete(self):
        if not self.parent:
            return False
        
        return self.complete
