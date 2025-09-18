import json
import typing
import tempfile
import os
import pathlib
import uuid

import common.hierarchy
import rig_gen.add_support_info as rg_s_inf
import commands.rig_info.add_joints as aj
import csc
import rig_mode.on as rm_on
import rig_mode.off as rm_off

import cg3dguru
import cg3dguru.general.fbx as fbx


MAYA_BEHAVIOUR_NAME = 'Maya Data'
MAYA_ROOTS = 'Maya Roots'


def _import_maya_qrig_file(file_path):
    scene_manager = csc.app.get_application().get_scene_manager()
    application_scene = scene_manager.current_scene()
    rm_on.run_raw(application_scene.domain_scene(), [0.0, 0.5, 0.0])
    rig_tool = csc.app.get_application().get_tools_manager().get_tool('RiggingToolWindowTool').editor(application_scene)
    rig_tool.open_quick_rigging_tool()
    rig_tool.load_template_by_fileName(file_path)
    rig_tool.generate_rig_elements()
    

    
def _get_object_by_id(object_list, maya_id):
    global MAYA_BEHAVIOUR_NAME
    
    for obj in object_list:
        beh = obj.get_behaviour_by_name(MAYA_BEHAVIOUR_NAME)
        if beh:
            found_id = beh.datasWithSameNamesReadonly.get_by_name('maya_id')
            if found_id and found_id[0].get() == maya_id:
                print('found previous import')
                return obj
        
    return None



def _make_rig_info(scene, set_name, new_roots):
    #make a rig info and select it.
    new_selection = []
    for root in new_roots:
        new_selection.extend(common.hierarchy.get_object_branch_inclusive(root, root.scene.dom_scene))
        
    scene.edit('Change selection', lambda x: scene.select(new_selection))
    joints = scene.get_scene_objects(of_type='Joint')
    rig_info_node = None
    
    if joints:
        #Maybe we should really check to make sure the joints aren't already
        #in another rig_info node (like the official create command does)
        #but I think my logic won't get here if that's true.
        def make_mod(scene, set_name):
            nonlocal rig_info_node
            
            new_name = set_name.replace('CSC_EXPORT', '')
            new_name = set_name.rstrip('_')
            rig_info_node = scene.create_object('{}_Rig'.format(new_name))
            rig_info_beh = rig_info_node.add_behaviour('RigInfo')
            rig_info_beh.related_joints.set(joints)
        
        scene.edit('Make Rig Info', make_mod, set_name)
        
    if rig_info_node:
        scene.edit('Change selection', lambda x: scene.select([rig_info_node]))



def _create_data(scene, set_name, maya_id, new_roots):
    global MAYA_BEHAVIOUR_NAME
     
    #make the selection/object set   
    obj = scene.create_object(set_name)
    behaviour = obj.add_behaviour('Dynamic', MAYA_BEHAVIOUR_NAME)
    data_prop = behaviour.get_property('datasWithSameNamesReadonly')
    data_prop.create_data('maya_id', csc.model.DataMode.Static, maya_id, group_name='{} update'.format(MAYA_BEHAVIOUR_NAME))
    
    roots_behaviour = obj.add_behaviour('DynamicBehaviour', MAYA_ROOTS)
    roots_behaviour.behaviours.set( [obj.Basic for obj in new_roots] )
    
    return obj
    
    
    
def _get_modified_filter(existing_data, qrig_path, import_filter: fbx.FbxFilterType):
    if import_filter == fbx.FbxFilterType.ANIMATION:
        if not existing_data:
            return fbx.FbxFilterType.SKIP
        else:
            return fbx.FbxFilterType.ANIMATION
    elif import_filter == fbx.FbxFilterType.MODEL:
        if not existing_data:
            return fbx.FbxFilterType.MODEL
        else:
            return fbx.FbxFilterType.SKIP
    elif import_filter == fbx.FbxFilterType.SCENE:
        return fbx.FbxFilterType.SCENE
    elif import_filter == fbx.FbxFilterType.AUTO:
        if existing_data is None:
            #If no data exists, we'll import everything
            print("Importing scene")
            return fbx.FbxFilterType.SCENE
        elif qrig_path:
            #Else if we have data and a qrig_path exists, we'll assume
            #they just want to quick-rig the previous data
            print("Skpping FBX Data")
            return fbx.FbxFilterType.SKIP
        else:
            #else we'll assume only animation data needs updating
            print("Importing Animation")
            return fbx.FbxFilterType.ANIMATION
    else:
        raise (Exception("Add support for {}".format(import_filter)))
    
    
    
def _load_textures(scene):
    def mod(scene):
        temp_dir = pathlib.Path(os.path.join(tempfile.gettempdir(), 'mayacasc'))
        #load any textures
        texture_path: pathlib.Path = temp_dir.joinpath('texture_info.json')
        if texture_path.exists():
            texture_data = open(texture_path)
            texture_mapping = json.load(texture_data)
            texture_data.close()
            
            names = list(texture_mapping.keys())
            if not names:
                return
            
            objs = scene.get_scene_objects(names=names)
            for obj in objs:
                if not obj.has_behaviour('MeshObject'):
                    print("Can't find MeshObject for {}".format(obj.name))
                    continue
                                
                filename = texture_mapping[obj.name]
                if not obj.has_behaviour('TextureContainer'):
                    obj.add_behaviour('TextureContainer')
                    
                data = obj.TextureContainer.texture_paths.get_by_name('texture 0')
                if data:
                    data[0].set(filename)
                else:
                    obj.TextureContainer.start_frame.create_data('Start frame', csc.model.DataMode.Static, 0, group_name='maya_textures')
                    data = obj.create_data('texture 0', csc.model.DataMode.Static, filename, group_name='maya_textures')
                    obj.TextureContainer.texture_paths.add(data.id)
                    
                obj.MeshObject.textures.set(obj.TextureContainer)
     
    #mod(scene)               
    scene.edit("Load Textures", mod)
    
    
    
def _import_maya(new_scene, import_filter: fbx.FbxFilterType):
    if new_scene:
        scene = cg3dguru.new_scene()
    else:
        scene = cg3dguru.get_current_scene()

    scene.dom_scene.info("Importing Maya Data")
    temp_dir = pathlib.Path(os.path.join(tempfile.gettempdir(), 'mayacasc'))
    if not temp_dir.exists():
        scene.dom_scene.error("Can't find Maya data")
        return
    
        
    #pre_import_roots will allow me to find everything that's new to the
    #scene once all files are imported.  scene_roots will be updated
    #after each file import has been completed.
    pre_import_roots = set(scene.get_scene_objects(only_roots=True))
    scene_roots = set(pre_import_roots)
    
    files = {}
    for child in temp_dir.iterdir():
        name, ext = child.name.rsplit('.', 1)
        if name not in files:
            files[name] = dict()
            
        files[name][ext.lower()] = str(child)
        
    import_rig = ''
    for key, item in files.items():
        fbx_path = ''
        qrig_path = ''
        if 'fbx' in item:
            fbx_path = item['fbx']
        if 'qrigcasc' in item:
            qrig_path = item['qrigcasc']
            
        if not fbx_path and not qrig_path:
            #we'll skip files that don't match the name.id format
            #the texture file is an example of one of these files
            continue
        
        if qrig_path:
            import_rig = qrig_path
            
        set_name, maya_id = key.split('.') 
        existing_data = _get_object_by_id(pre_import_roots, maya_id)
        modified_filter = _get_modified_filter(existing_data, qrig_path, import_filter)
        
        if modified_filter != fbx.FbxFilterType.SKIP:
            #To-Do: Find a way to make this update the mesh for exsting data
            #
            #if existing_data and modified_filter == fbx.FbxFilterType.MODEL:
                ##selecting the existing data before importing a model should
                ##just update the mesh...I think.
                #root_beh = existing_data.get_behaviour_by_name(MAYA_ROOTS)
                #roots = [beh.object for beh in root_beh.behaviours.get()]
                
                #new_selection = []
                #for root in roots:
                    #new_selection.extend(common.hierarchy.get_object_branch_inclusive(root, root.scene.dom_scene))
                    
                #scene.edit('Change selection', lambda x: scene.select(new_selection))
                
            fbx.import_fbx(fbx_path, modified_filter)
            
            current_roots = set(scene.get_scene_objects(only_roots=True))
            new_roots = current_roots.difference(scene_roots)
            scene_roots = current_roots               


        #Let's find the stuff that was just imported and create a way
        #to search for it later.
        if existing_data is None and modified_filter != fbx.FbxFilterType.SKIP:
            scene.edit('Import maya data', _create_data, set_name, maya_id, new_roots)
            if qrig_path:
                _make_rig_info(scene, set_name, new_roots)
        else:
            scene.dom_scene.info("Updated existing data")
            
            
    _load_textures(scene)
              
                
    #rig generation has to come last, so all the other automation can complete properly
    #This is outside of the main file loop, because for now we can only import one
    #rig file per import actions, so the var should be initialized, and I need  do this after all
    #the textures have been assigned.  Once I can import rigs via script (without ui interaction)
    #this can stay inside the file loop and we can move the texture loading to the end.
    if import_rig:
        print("attempting rig import")
        _import_maya_qrig_file(import_rig)
            
     
        
def update_models():
    _import_maya(False, fbx.FbxFilterType.MODEL)
    
    
def update_animations():
    _import_maya(False, fbx.FbxFilterType.ANIMATION)
    
    
def import_rig(new_scene):
    _import_maya(new_scene, fbx.FbxFilterType.MODEL)    
    

def import_scene(new_scene):
    _import_maya(new_scene, fbx.FbxFilterType.SCENE)
    
    
def smart_import(new_scene):
    _import_maya(new_scene, fbx.FbxFilterType.AUTO)
    
    
def update_textures():
    scene = cg3dguru.get_current_scene()
    _load_textures(scene)
    
    

##----Export functions---- 
    
    
def _get_maya_sets(obj_list):
    return [obj for obj in obj_list if
            obj.get_behaviour_by_name(MAYA_BEHAVIOUR_NAME) is not None]
    
    
def _select_for_export(scene, new_selection):
    scene.select(new_selection)
    #scene.select_frame_range()
    
    
def _export(cmd_string):
    new_object = None
    def _create_new_set(scene):
        print("Making new set")
        nonlocal new_object
        current_roots = scene.get_scene_objects(only_roots=True)
        set_name = "MAYA_DATA_EXPORT"
        maya_id = uuid.uuid1()
        new_object = _create_data(scene, set_name, str(maya_id), current_roots)
    
    #remove any previous exports
    temp_dir = pathlib.Path(os.path.join(tempfile.gettempdir(), 'mayacasc'))
    print('Cascaduer Export Location {}'.format(temp_dir))
    if not temp_dir.exists():
        temp_dir.mkdir()

    #delete previous entries
    for child in temp_dir.iterdir():
        child.unlink(missing_ok=True)
        
    scene = cg3dguru.get_current_scene()
    
    #See if we have an export set selected
    selected = scene.get_scene_objects(selected=True)
    export_sets = _get_maya_sets(selected)
    
    #If not see if we can find any in the current scene
    if not export_sets:
        transforms = scene.get_scene_objects(of_type='Basic')
        export_sets = _get_maya_sets(transforms)
        if export_sets:
            print("Found previous import")
            print(export_sets)
        
    #If not, then this must be a first time export, so let's make an export set
    if not export_sets:
        scene.edit('Create Maya Export Set', _create_new_set)
        export_sets =  _get_maya_sets([new_object])
        
        
    for export_set in export_sets:
        root_beh = export_set.get_behaviour_by_name(MAYA_ROOTS)
        roots = [beh.object for beh in root_beh.behaviours.get()]
        
        new_selection = []
        for root in roots:
            new_selection.extend(common.hierarchy.get_object_branch_inclusive(root, root.scene.dom_scene))
            
        scene.edit('Change selection', _select_for_export, new_selection)

        maya_beh =root_beh.get_siblings_by_name(MAYA_BEHAVIOUR_NAME)[0]
        maya_id = maya_beh.datasWithSameNamesReadonly.get_by_name('maya_id')
        if maya_id:
            maya_id = maya_id[0]
            fbx_name = '{}.{}.fbx'.format(root_beh.object.name, maya_id.get())
            
            export_path = str(temp_dir.joinpath(fbx_name))
            
            print("Exporting to {}".format(fbx_name))
            
            #TODO: Change this to selection, once we know how to select a branch
            fbx.export_fbx(export_path, fbx.FbxFilterType.SELECTED) 
        
 
    import wingcarrier.pigeons
    maya = wingcarrier.pigeons.MayaPigeon()    
    maya.send_python_command(cmd_string)
    
    ##something isn't working here
    #scene.edit('Reset selection', lambda x: scene.select(list(selected)))
 
        
        
def export_maya_animation():
    cmd = "import cg3dcasc.core; cg3dcasc.core.import_fbx()"
    _export(cmd)
    
    
def run(*args, **kwargs):
    export_maya_animation()
    


