
import os

import pymel.core as pm

try:
    from PySide2.QtWidgets import *
except:
    from PySide6.QtWidgets import *
    

import cg3dguru.ui
import cg3dcasc

WINDOW_NAME = 'HIK Export'

#for QT Designer "PromotTo" you want to put cg3dmaya/cascadeur/editor.py for the header
#and use QUiLoader.registerCustomWidget(DropLinEdit)
class DropLineEdit(QLineEdit):
    def __init__(self, *args, **kwargs):
        super(DropLineEdit, self).__init__(*args, **kwargs)
        self.setReadOnly(True)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        input_text = event.mimeData().text()
        entries = input_text.split('\n')
        
        if not entries or len(entries) != 1:
            return
        
        node = pm.PyNode(entries[0])
        if node.type() != 'joint':
            return
        
        event.acceptProposedAction()


    def dropEvent(self, event):
        input_text = event.mimeData().text()
        segments = input_text.split('|')
        
        try:
            #This will except when there's a name conflict
            pm.PyNode(segments[-1])
            input_text = segments[-1]
        except:
            print('Name conflict. Using long name')
        
        self.setText(input_text)



class HikExportEditor(cg3dguru.ui.Window):
    def __init__(self, windowKey, uiFilepath, *args, **kwargs):
        custom_widgets = [DropLineEdit]
        super(HikExportEditor, self).__init__(windowKey, uiFilepath, custom_widgets = custom_widgets)
        self.job_handlers = {}
        self.add_script_jobs()
        self.qrig_data_instance = cg3dcasc.QRigData()
        self.export_data_instance = cg3dcasc.CascExportData()
        self.scene_nodes = {}        
        self.spine_joints = {}
        self.extras = {}
        
        self.data_Changing = False #maya scene changed
        self.selection_changing = False #selection set selection change is occuring
        self.global_twist_changing = False
        self.node_to_select = None
        self.active_selection = None
        self.rig_data = None
        self.export_data = None

        self._init_drag_n_drop()
        self.init_ui()
        
        #signals
        self.ui.scene_list.currentTextChanged.connect(self.on_node_selected)
        self.ui.spine_list.currentTextChanged.connect( self.on_spine_choice_changed )
        self.ui.create_data_button.released.connect(self.on_create_data)
        self.ui.delete_data_button.released.connect(self.on_delete_data)
        self.ui.add_hik_button.released.connect(self.on_add_hik)
        
        self.ui.left_weapon_node.textChanged.connect( lambda : self.on_weapon_changed(self.ui.left_weapon_node, "leftWeapon") )
        self.ui.right_weapon_node.textChanged.connect( lambda : self.on_weapon_changed(self.ui.right_weapon_node, "rightWeapon") )
        self.ui.clear_left_weapon.pressed.connect(lambda : self.on_clear_weapon(self.ui.left_weapon_node))
        self.ui.clear_right_weapon.pressed.connect(lambda : self.on_clear_weapon(self.ui.right_weapon_node))
        self.ui.add_extras.pressed.connect(self.on_add_selection)
        self.ui.remove_extras.pressed.connect(self.on_remove_selection)
        self.ui.dynamic_set.stateChanged.connect(self.on_dynamic_changed)
        self.ui.align_pelvis.stateChanged.connect(self.on_align_pelvis)
        self.ui.create_layers.stateChanged.connect(self.on_create_layers)
        
        self.ui.strength_percents.pressed.connect(self.show_percents)
        self.ui.global_twist.currentIndexChanged.connect(self.on_global_twist_changed)
        
        self.ui.left_arm_twist.currentIndexChanged.connect(lambda: self.on_set_twist(self.ui.left_arm_twist, 'leftArmTwist'))
        self.ui.left_forearm_twist.currentIndexChanged.connect(lambda: self.on_set_twist(self.ui.left_forearm_twist, 'leftForearmTwist'))
        self.ui.left_upper_leg_twist.currentIndexChanged.connect(lambda: self.on_set_twist(self.ui.left_upper_leg_twist, 'leftUpperLegTwist'))
        self.ui.left_leg_twist.currentIndexChanged.connect(lambda: self.on_set_twist(self.ui.left_leg_twist, 'leftLegTwist'))
        
        self.ui.right_arm_twist.currentIndexChanged.connect(lambda: self.on_set_twist(self.ui.right_arm_twist, 'rightArmTwist'))
        self.ui.right_forearm_twist.currentIndexChanged.connect(lambda: self.on_set_twist(self.ui.right_forearm_twist, 'rightForearmTwist'))
        self.ui.right_upper_leg_twist.currentIndexChanged.connect(lambda: self.on_set_twist(self.ui.right_upper_leg_twist, 'rightUpperLegTwist'))
        self.ui.right_leg_twist.currentIndexChanged.connect(lambda: self.on_set_twist(self.ui.right_leg_twist, 'rightLegTwist'))

        self.ui.rig_current_button.pressed.connect(lambda: self.on_export(False))
        self.ui.rig_new_button.pressed.connect(lambda: self.on_export(True))
        
        
        
    def show_percents(self):
        if self.rig_data is None or not self.rig_data.characterNode.inputs():
            return
        
        #selection = pm.ls(sl=True)
        pm.select(self.rig_data.characterNode.inputs()[0].propertyState.get(), replace=True)
        
        pm.runtime.ToggleAttributeEditor()    
        visible = pm.windows.workspaceControl('AttributeEditor',visible=True,query=True)
        
        if not visible:
            pm.runtime.ToggleAttributeEditor()    
        
        #if visible and not selection:
            #return
        
        #elif visible and selection:
            #pm.Mel.eval('commitAENotes($gAECurrentTab); copyAEWindow;')
            #pm.select(selection, replace=True)
            
        #elif not visible and not selection:
            #pm.runtime.ToggleAttributeEditor()
            #return
        
        #elif not visible and selection:
            #pm.runtime.ToggleAttributeEditor()
            #pm.Mel.eval('commitAENotes($gAECurrentTab); copyAEWindow;')
            #pm.runtime.ToggleAttributeEditor()
            #pm.select(selection, replace=True)
        
        
    def on_global_twist_changed(self):
        if self.data_Changing or not self.rig_data or self.selection_changing:
            return
        
        value = self.ui.global_twist.currentIndex()
        if value < 3:
            self.global_twist_changing = True
            attrs = ['leftArmTwist', 'leftForearmTwist', 'leftUpperLegTwist',
                     'leftLegTwist', 'rightArmTwist', 'rightForearmTwist',
                     'rightUpperLegTwist', 'rightLegTwist']
            
            for attr in attrs:
                self.rig_data.attr(attr).set(value)
                
            self._init_twist_data()
            self.global_twist_changing = False
        
        
    def on_set_twist(self, control, attr_name):
        if self.data_Changing or not self.rig_data or self.selection_changing:
            return
        
        self.rig_data.attr(attr_name).set(control.currentIndex())
        
        if not self.global_twist_changing:
            self._init_twist_data()
                
                  
    def _create_export_data(self):
        node, data = cg3dcasc.CascExportData.create_node(nodeType = 'objectSet')
        return node
                

    def on_create_data(self, *args, **kwargs):
        data_name, ok = QInputDialog.getText(None, "New Node Name", 'Name this data')
        if not ok:
            return
        
        selection = pm.ls(sl=True)
        
        filtered_selection = pm.ls(sl=True,type=['transform','joint', 'skinCluster', 'mesh'])
        new_node = self._create_export_data()
        name = '{}_CSC_EXPORT'.format(data_name)
        pm.rename(new_node, name)
        self.node_to_select = new_node
        
        pm.select(selection, replace=True)
        
        if filtered_selection:
            answer =  QMessageBox.question(self.mayaWindow, 'Add', 'Add the current selection?')
            if answer == QMessageBox.StandardButton.Yes:
                if filtered_selection:
                    new_node.addMembers(filtered_selection)            
            
        self.init_ui()
        

    def on_delete_data(self, *args, **kwargs):
        if not self.active_selection:
            return

        pm.general.delete(self.active_selection)
        self.active_selection = None
        self.init_ui()


    def on_add_hik(self):
        invalid_nodes = self._get_invalid_characters()
        if not invalid_nodes:
            return
        
        names = []
        nodes = {}
        for node in invalid_nodes:
            names.append(node.name())
            nodes[node.name()] = node
            
        names.sort()
        char_name, ok = QInputDialog.getItem(None, "Select Character", "", names, 0, False)
        if ok:
            char_node = nodes[char_name]
            node = self._create_export_data()
            name = '{}_CSC_EXPORT'.format(char_node.name())
            pm.rename(node, name)
            
            data = self.qrig_data_instance.add_data(node)
            char_node.message >> data.characterNode
            
            self.node_to_select = node
            self.init_ui()
        
        
    def on_export(self, new_scene):
        if not self.export_data:
            return
        
        try:
            cg3dcasc.export_rig(new_scene, self.export_data.node()) #, qrig_data=self.rig_data, character_node=self.active_selection)
        except cg3dcasc.SpineException:
            pm.confirmDialog(message="You must set a chest joint before exporting",button=['Okay'])
        
        
    def on_dynamic_changed(self, *args):
        if self.data_Changing or not self.active_selection or self.selection_changing:
            return
        
        if not self.export_data:
            return
        
        self.export_data.dynamicSet.set(args[0] != 0)

        
    def on_align_pelvis(self, *args):
        if self.data_Changing or not self.active_selection or self.selection_changing:
            return
        
        self.rig_data.alignPelvis.set(args[0] != 0)
      
        
    def on_create_layers(self, *args):
        if self.data_Changing or not self.active_selection or self.selection_changing:
            return
        
        self.rig_data.createLayers.set(args[0] != 0)    
        
        
    def _get_active_node(self):
        self.active_selection = None
        self.rig_data = None
        self.export_data = None        
        
        if self.ui.scene_list.currentText():
            self.active_selection = self.ui.scene_list.currentData()
            self.export_data = self.export_data_instance.get_data(self.active_selection)
            
            if not self.export_data:
                pm.error("Casc Editor: Active node somehow doesn't have export data?!?")
            
            self.rig_data = self.qrig_data_instance.get_data(self.active_selection)
            
        #hide some data based on the selected data
        self.ui.tabs.setTabVisible(1, self.rig_data is not None)
        self.ui.delete_data_button.setEnabled(self.active_selection is not None)
        
        
    def _init_ui(self, selection_changing, data_Changing):
        self.selection_changing = selection_changing
        self.data_Changing = data_Changing
                
        self._init_scene_list()
        self._get_active_node()
        self._init_selection_set()
        self._init_spine_list()
        self._init_weapon_nodes()
        self._init_check_boxes()
        self._init_twist_data()
        if self.rig_data is not None:
            self.ui.tabs.setCurrentWidget(self.ui.rig_tab)
        else:
            self.ui.tabs.setCurrentWidget(self.ui.selection_tab)
            
        self.ui.tabs.setTabVisible(0, self.active_selection is not None)
            
        self.selection_changing = False
        self.data_Changing = False
        
        
    def on_node_selected(self, *args):
        if self.data_Changing:
            return

        self._init_ui(True, False)
        
        
    def on_remove_selection(self):
        if self.data_Changing or not self.export_data or self.selection_changing:
            return
        
        object_set = self.export_data.node()
        selected_items = self.ui.export_list.selectedItems()
        nodes_to_remove = []
        for item in selected_items:
            node = self.extras[item.text()]
            nodes_to_remove.append(node)
            #pm.Attribute.disconnect(node.message, self.export_data.exportNodes, nextAvailable=True)
            
        if nodes_to_remove:
            object_set.removeMembers(nodes_to_remove)
            
        self._init_selection_set()
        
        
    def on_add_selection(self):
        if self.data_Changing or not self.export_data or self.selection_changing:
            return              
        
        object_set = self.export_data.node()
        
        #special case for if someone adds the hikCharacterNode to an existing object set
        added_character_node = False
        selected_character_nodes = pm.ls(sl=True, type='HIKCharacterNode')
        invalid_nodes = self._get_invalid_characters()
        if selected_character_nodes and len(selected_character_nodes) == 1 and selected_character_nodes[0] in invalid_nodes:
            data = self.qrig_data_instance.add_data(object_set)
            selected_character_nodes[0].message >> data.characterNode
            added_character_node = True
            
        selection = pm.ls(sl=True,type=['transform','joint', 'skinCluster', 'mesh'])
        if selection:
            object_set.addMembers(selection)
                    
        if added_character_node:
            self._init_ui(True, False)
        else:
            self._init_selection_set()
            
        
        
    def on_clear_weapon(self, weapon):
        weapon.setText('')
        
        
    def on_weapon_changed(self, control, attr_name):
        if self.data_Changing or not self.active_selection or self.selection_changing:
            return                 
        
        name = control.text()
        if not name:
            if self.rig_data:
                attr = self.rig_data.attr(attr_name)
                inputs = attr.inputs(plugs=True)
                if inputs:
                    inputs[0] // attr
            
        else:    
            try:
                node = pm.PyNode(name)
            except:
                node = None
         
            if node:
                if self.rig_data:
                    attr = self.rig_data.attr(attr_name)
                    node.message >> attr  


    def on_spine_choice_changed(self, *args, **kwargs):
        if self.data_Changing or not self.active_selection or self.selection_changing:
            return        
        
        joint = self.ui.spine_list.currentData()
        if not joint:
            return
        
        if self.rig_data:
            joint.message >> self.rig_data.chestJoint
            
        blank_idx = self.ui.spine_list.findText('')
        if blank_idx > -1:
            self.ui.spine_list.removeItem(blank_idx)
        
        
    def _init_drag_n_drop(self):
        #https://stackoverflow.com/questions/60012363/set-qlineedit-to-read-only-but-still-accept-drops
        self.ui.left_weapon_node.setReadOnly(True)
        self.ui.left_weapon_node.setAcceptDrops(True)
        
        
    def _get_invalid_characters(self):
        hik_nodes = pm.ls(type='HIKCharacterNode')
        valid_nodes = cg3dguru.udata.Utils.get_nodes_with_data(nodes=pm.ls(type='objectSet'), data_class=cg3dcasc.QRigData)
        linked_characters = [node.characterNode.get() for node in valid_nodes if node.characterNode.get() is not None]
        hik_nodes = set(hik_nodes)
        linked_characters = set(linked_characters)
        
        return hik_nodes.difference(linked_characters)
        
        
    def _init_scene_list(self):
        #This list should only change when scene data is changing,
        #NOT when selection changes cause the ui to update.
        if not self.data_Changing:
            return
                
        self.scene_nodes.clear()
        self.ui.scene_list.clear()
            
        #Find the data in our scene
        scene_sets = pm.ls(type='objectSet')
        data_nodes = cg3dguru.udata.Utils.get_nodes_with_data(scene_sets, data_class=cg3dcasc.CascExportData)
        
        for node in  data_nodes:
            self.scene_nodes[node.name()] = node
            
        #Build our dropdown list when the names sorted
        node_names = list(self.scene_nodes)
        node_names.sort()
        
        self.active_selection = None
        if node_names:
            for name in node_names:
                self.ui.scene_list.addItem(name, self.scene_nodes[name])
            
            if self.node_to_select:
                idx = self.ui.scene_list.findText(self.node_to_select.name())
                self.node_to_select = None
                if idx > -1:
                    self.ui.scene_list.setCurrentIndex(idx)

            self.active_selection = self.ui.scene_list.currentData()
                 
        #let's activate and hide data based on our scene list
        invalid_nodes = self._get_invalid_characters()
        self.ui.add_hik_button.setEnabled(len(invalid_nodes) > 0)
#        self.ui.selected_data_group.setEnabled(self.active_selection is not None)

    
    def _init_spine_list(self):
        self.spine_joints.clear()
        self.ui.spine_list.clear()
        
        if not self.rig_data or not self.rig_data.characterNode.inputs():
            return
        
        character_node = self.rig_data.characterNode.inputs()
        if not character_node:
            return
        
        character_node = character_node[0] 
        
        spine_joints = cg3dcasc.get_spine_joints(character_node)
        for spine_name, joint in spine_joints:
            self.spine_joints[joint.name()] = joint
        
        spine_names = list(self.spine_joints)
        spine_names.sort()
        for name in spine_names:
            self.ui.spine_list.addItem(name, self.spine_joints[name])
        
        #Make an empty entry if the rig_data doesn't reference a valid spine
        #otherwise set the dropdown the matching spine
        inputs = self.rig_data.chestJoint.inputs()
        valid_spine = None
        if inputs and inputs[0].name() in self.spine_joints:
            valid_spine = inputs[0]
            
        if valid_spine is None:
            self.ui.spine_list.addItem('', None)
            self.ui.spine_list.setCurrentText('')
        else:
            self.ui.spine_list.setCurrentText(valid_spine.name())

        
    def _init_selection_set(self):
        self.ui.export_list.clear()
        self.extras.clear()
        
        if not self.active_selection:
            return
        
        object_set = self.export_data.node()
        names = []
        
        for node in object_set.flattened():
            if cg3dcasc.node_type_exportable(node):
                self.extras[node.name()] = node
                names.append(node.name())

        names.sort()
        self.ui.export_list.addItems(names)
        self.ui.dynamic_set.setChecked(self.export_data.dynamicSet.get())
        

    def _init_weapon_nodes(self):
        def set_ui_value(ui_element, attr_name):
            attr = self.rig_data.attr(attr_name)
            inputs = attr.inputs()
            if inputs:
                ui_element.setText(inputs[0].name())

        self.ui.left_weapon_node.setText('')
        self.ui.right_weapon_node.setText('')
                     
        if not self.rig_data:
            return
        
        set_ui_value(self.ui.left_weapon_node, 'leftWeapon')
        set_ui_value(self.ui.right_weapon_node, 'rightWeapon')

        
    def _init_check_boxes(self):
        if not self.rig_data:
            self.ui.align_pelvis.setChecked(False)
            self.ui.create_layers.setChecked(False)
        else:
            self.ui.align_pelvis.setChecked(self.rig_data.alignPelvis.get())
            self.ui.create_layers.setChecked(self.rig_data.createLayers.get())
            
            
            
    def _init_twist_data(self):
        has_data = self.rig_data is not None and len(self.rig_data.characterNode.inputs()) > 0
        self.ui.twist_settings.setVisible(has_data)
        if not has_data:
            return
        
        character_node = self.rig_data.characterNode.inputs()[0]
        if not cg3dcasc.has_twist(character_node):
            self.ui.twist_settings.setVisible(False)
            return
        
        valid_twists = []
        def get_twist_state(label, dropdown, twist_name, setting):
            has = cg3dcasc.has_twist(character_node, twist_name)
            label.setEnabled(has)
            dropdown.setCurrentIndex(setting.get())
            dropdown.setEnabled(has)
            
            if has:
                valid_twists.append(setting)

        get_twist_state(self.ui.left_arm, self.ui.left_arm_twist, 'LeafLeftArmRoll1', self.rig_data.leftArmTwist)
        get_twist_state(self.ui.left_forearm, self.ui.left_forearm_twist, 'LeafLeftForeArmRoll1', self.rig_data.leftForearmTwist)
        get_twist_state(self.ui.left_upper_leg, self.ui.left_upper_leg_twist, 'LeafLeftUpLegRoll1', self.rig_data.leftUpperLegTwist)
        get_twist_state(self.ui.left_leg, self.ui.left_leg_twist, 'LeafLeftLegRoll1', self.rig_data.leftLegTwist)
        
        get_twist_state(self.ui.right_arm, self.ui.right_arm_twist, 'LeafRightArmRoll1', self.rig_data.rightArmTwist)
        get_twist_state(self.ui.right_forearm, self.ui.right_forearm_twist, 'LeafRightForeArmRoll1', self.rig_data.rightForearmTwist)
        get_twist_state(self.ui.right_upper_leg, self.ui.right_upper_leg_twist, 'LeafRightUpLegRoll1', self.rig_data.rightUpperLegTwist)
        get_twist_state(self.ui.right_leg, self.ui.right_leg_twist, 'LeafRightLegRoll1', self.rig_data.rightLegTwist)
        
        twist_value = valid_twists[0].get()
        mixed = False
        for attr in valid_twists:
            if attr.get() != twist_value:
                mixed = True
                break
         
        mixed_idx = self.ui.global_twist.findText('...')   
        if mixed:
            if mixed_idx < 0:
                self.ui.global_twist.addItem('...')
            
            self.ui.global_twist.setCurrentIndex(3)
        else:
            if mixed_idx > -1:
                self.ui.global_twist.removeItem(mixed_idx)
                
            self.ui.global_twist.setCurrentIndex(twist_value)

         
    def init_ui(self):
        self._init_ui(False, True)
        
        
    def scene_loaded(self):
        isVisible = self.ui.centralwidget.isVisible()
        print("HikExportEditor: refreshing character list {}".format(isVisible))
        if isVisible:
            self.init_ui()
        
        
    def _add_script_job(self, event_name, func):
        jobId   = pm.scriptJob( event=[event_name, func] )
        handler = lambda : self.remove_script_job(jobId)
        self.job_handlers[jobId] = handler
        self.ui.destroyed.connect( handler )
        
        
    def add_script_jobs(self):
        self.job_handlers = {}
        self._add_script_job('PostSceneRead', self.scene_loaded)
        self._add_script_job('NewSceneOpened', self.scene_loaded)
    
    
    def remove_script_job(self, jobId):
        self.ui.destroyed.disconnect( self.job_handlers[jobId] )
        pm.scriptJob( kill = jobId )
        
  
        
def run(*args):
    filepath = os.path.join(cg3dcasc.__path__[0],  'Cascadeur.ui' )
    editor = HikExportEditor(WINDOW_NAME, filepath)

    editor.ui.resize(editor.ui.layout().minimumSize())
    editor.ui.show()

