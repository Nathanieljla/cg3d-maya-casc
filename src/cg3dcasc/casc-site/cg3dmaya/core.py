import typing
import tempfile
import os
import pathlib
import uuid

import csc
import rig_mode.on as rm_on
import rig_mode.off as rm_off

import cg3dguru.core
import cg3dguru.core.general.fbx as fbx


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
    
    

def _create_data(scene, set_name, maya_id, new_roots):
    global MAYA_BEHAVIOUR_NAME
        
    obj = scene.create_object(set_name)
    behaviour = obj.add_behaviour('Dynamic', MAYA_BEHAVIOUR_NAME)
    data_prop = behaviour.get_property('datasWithSameNamesReadonly')
    data_prop.create_data('maya_id', csc.model.DataMode.Static, maya_id, group_name='{} update'.format(MAYA_BEHAVIOUR_NAME))
    
    roots_behaviour = obj.add_behaviour('DynamicBehaviour', MAYA_ROOTS)
    roots_behaviour.behaviours.set( [obj.Basic for obj in new_roots] )
    
    return obj
    
    
    
def _get_modified_filter(existing_data, qrig_path, import_filter: fbx.FbxFilterType):
    if import_filter == fbx.FbxFilterType.ANIMATION:
        return fbx.FbxFilterType.ANIMATION
    elif import_filter == fbx.FbxFilterType.MODEL:
        return fbx.FbxFilterType.MODEL
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
    
    
    
def _import_maya(new_scene, import_filter: fbx.FbxFilterType):
    if new_scene:
        scene = cg3dguru.core.new_scene()
    else:
        scene = cg3dguru.core.get_current_scene()

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
        
        
    for key, item in files.items():
        fbx_path = ''
        qrig_path = ''
        if 'fbx' in item:
            fbx_path = item['fbx']
        if 'qrigcasc' in item:
            qrig_path = item['qrigcasc']
            
        set_name, maya_id = key.split('.') 
        existing_data = _get_object_by_id(pre_import_roots, maya_id)
        modified_filter = _get_modified_filter(existing_data, qrig_path, import_filter)
        
        if modified_filter != fbx.FbxFilterType.SKIP:
            fbx.import_fbx(fbx_path, modified_filter)


        #Let's find the stuff that was just imported and create a way
        #to search for it later.
        current_roots = set(scene.get_scene_objects(only_roots=True))
        new_roots = current_roots.difference(scene_roots)
        scene_roots = current_roots
        
        if existing_data is None:
            scene.edit('Import maya data', _create_data, set_name, maya_id, new_roots)
        else:
            scene.dom_scene.info("Updated existing data")
                
        #rig generation has to come last, so all the other automation can complete properly
        if qrig_path:
            _import_maya_qrig_file(qrig_path)
            
            
            
def update_models():
    _import_maya(False, fbx.FbxFilterType.MODEL)
    
    
def update_animations():
    _import_maya(False, fbx.FbxFilterType.ANIMATION)
    

def import_scene(new_scene):
    _import_maya(new_scene, fbx.FbxFilterType.SCENE)
    
    
def smart_import(new_scene):
    _import_maya(new_scene, fbx.FbxFilterType.AUTO)
    
    

##----Export functions---- 
    
    
def _get_maya_sets(obj_list):
    return [obj for obj in obj_list if
            obj.get_behaviour_by_name(MAYA_BEHAVIOUR_NAME) is not None]
    
    
    
def get_object_branch(obj, input_list):
    pass
    
    
    
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
        
    scene = cg3dguru.core.get_current_scene()
    
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
        scene.edit('Change selection', lambda x: scene.select(roots))

        maya_beh =root_beh.get_siblings_by_name(MAYA_BEHAVIOUR_NAME)[0]
        maya_id = maya_beh.datasWithSameNamesReadonly.get_by_name('maya_id')[0]
        fbx_name = '{}.{}.fbx'.format(root_beh.object.name, maya_id.get())
        export_path = str(temp_dir.joinpath(fbx_name))
        
        print("Exporting to {}".format(fbx_name))
        #TODO: Change this to selection, once we know how to select a branch
        fbx.export_fbx(export_path, fbx.FbxFilterType.SCENE)
        
 
    import wingcarrier.pigeons
    maya = wingcarrier.pigeons.MayaPigeon()    
    maya.send_python_command(cmd_string)
 
        
        
def export_maya_fbx_animation():
    cmd = "import cg3dmaya.cascadeur.core; cg3dmaya.cascadeur.core.import_fbx()"
    _export(cmd)
    
    
def run(*args, **kwargs):
    export_maya_fbx_animation()
    
  
print('core imported')  
    
#if __name__ == '__main__':
    #print("Importing")
    #import_fbx_file()
    


