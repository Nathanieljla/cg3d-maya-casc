
import os
import sys
import importlib

import pymel.core as pm

import cg3dguru.ui as ui
import cg3dguru.udata

WINDOW_NAME = 'User Data Editor'

       
class UserDataEditor(ui.Window):
    
    def __init__(self, windowKey, uiFilepath, *args, **kwargs):
        super(UserDataEditor, self).__init__(windowKey, uiFilepath)

        self.add_script_job()
        self.maya_nodes_selected = len(pm.ls(sl=True)) > 0

        self.classes = cg3dguru.udata.Utils.get_class_names()
        keys = list(self.classes.keys())
        keys.sort()
        self.ui.createDataList.addItems(keys)
        self.ui.searchDataList.addItems(keys)
        
        self.ui.createDataList.itemSelectionChanged.connect(lambda: self.on_selection_changed(self.ui.createDataList))
        self.ui.searchDataList.itemSelectionChanged.connect( lambda : self.on_selection_changed(self.ui.searchDataList) )
        
        self.ui.createData.clicked.connect(self.on_create)
        self.ui.addData.clicked.connect(self.on_add)
        self.ui.removeData.clicked.connect(self.on_delete)
        self.ui.sceneSelect.clicked.connect(self.on_select_from_scene)
        self.ui.filterSelection.clicked.connect(self.on_find_in_selection)
        self.ui.attribute_conflicts.clicked.connect(self.on_attribute_conflicts)
        
        
    def on_attribute_conflicts(self, *args, **kwargs):
        conflicts = cg3dguru.udata.Utils.find_attribute_conflicts(error_on_conflict=False)

        output = ''
        if conflicts:
            for attr_name in conflicts:
                classes = conflicts[attr_name]
                output += 'Attr Conflict: "{0}" exists in classes: {1}\n'.format(attr_name, classes)
        else:
            output = 'No attribute conflicts found. :)'

        self.ui.report_results.clear()
        self.ui.report_results.setPlainText(output)
        
        
    def add_script_job(self):
        jobId   = pm.scriptJob( event=['SelectionChanged', self.maya_selection_changed] )
        #print 'New Job: {0}'.format(jobId)
        self.handler = lambda : self.remove_script_job(jobId)
        #self.jobId = jobId
        self.ui.destroyed.connect( self.handler )        
        
        
    def remove_script_job(self, jobId):
        #print 'Nuke Job: {0}'.format(jobId)
        self.ui.destroyed.disconnect( self.handler )
        pm.scriptJob( kill = jobId )
        
        
    def _get_item_names(self, listWidget):
        selection = listWidget.selectedItems()
        names = []
        for item in selection:
            names.append( item.text() )
            
        return names
        
        
    def on_create(self):
        names = self._get_item_names(self.ui.createDataList)
        newNodes = []
        
        for name in names:
            data_class = self.classes[name]
            pyNode, data = data_class.create_node(name = name)
            newNodes.append(pyNode)
                
        if newNodes:
            pm.select(newNodes, replace = True)
        else:
            self.ui.statusbar.showMessage("No Data is selected")
    
    
    def on_add(self):
        names = self._get_item_names(self.ui.createDataList)
        cg3dguru.udata.Utils.validate_version(sl=True)
        
        for name in names:
            data_class = self.classes[name] #()
            for maya_node in pm.ls(sl=True):
                data_class.add_data( maya_node )
                
        self.on_selection_changed(self.ui.createDataList)
    
    
    def on_delete(self): 
        selection = pm.ls(sl=True)
        names = self._get_item_names(self.ui.createDataList)
        
        for name in names:
            data_class = self.classes[name] #()
            for mayaNode in selection:
                data_class.delete_data( mayaNode )
                
        self.maya_selection_changed()
    
    
    
    def _select(self, *args, **kwargs):
        names = self._get_item_names(self.ui.searchDataList)
        
        nodes = []
        for name in names:
            data_class = self.classes[name] #()
            found_nodes = cg3dguru.udata.Utils.get_nodes_with_data(data_class=data_class, **kwargs)
            
            nodes.extend(found_nodes)
            
        pm.select(nodes, replace=True)
        if not nodes:
            self.ui.statusbar.showMessage('No data found!', 5000)
        else:
            self.ui.statusbar.clearMessage()



    def on_select_from_scene(self):
        self._select()
            
    
    def on_find_in_selection(self):
        self._select(sl=True)
    
    
    def on_selection_changed(self, list_widget):
        #is anything selected in our list?
        enable = len( list_widget.selectedItems() ) > 0
        
        if list_widget is self.ui.createDataList:
            names = self._get_item_names(self.ui.createDataList)
            hasData  = False
            missData = False
            
            for name in names:
                data = None
                data = cg3dguru.udata.Utils.get_nodes_with_data(data_class = self.classes[name], sl=True)
                if data:
                    hasData  = True
                
                missData = len(data) != len(pm.ls(sl=True))
            
     
            self.ui.createData.setEnabled(enable)   
            self.ui.addData.setEnabled(enable and self.maya_nodes_selected and missData)
            self.ui.removeData.setEnabled(enable and hasData)
        else:
            print ("search list")
            
            
    def maya_selection_changed(self):
        self.maya_nodes_selected = len( pm.ls(sl=True) ) > 0
        
        if self.ui.createDataList.isVisible():
            self.on_selection_changed(self.ui.createDataList)
        else:
            self.on_selection_changed(self.ui.searchDataList)
    
 
def run(data_module = None):
    if data_module is not None:
        if data_module not in sys.modules:
            try:
                importlib.import_module(data_module)
            except Exception as e:
                print("failed to import {}".format(data_module))
                return

    filepath = os.path.join(cg3dguru.udata.__path__[0],  'user_data.ui' )
    editor = UserDataEditor(WINDOW_NAME, filepath)
    editor.ui.show()
    