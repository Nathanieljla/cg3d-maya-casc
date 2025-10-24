

import json
import typing
import tempfile
import os
import pathlib
import uuid

import csc
import pycsc
import common.hierarchy as hierarchy

from . import common
from . import server
from . import fbx


def _get_maya_sets(obj_list):
    return [obj for obj in obj_list if
            obj.get_behaviour_by_name(common.MAYA_BEHAVIOUR_NAME) is not None]


def _select_for_export(scene, new_selection):
    scene.select(new_selection)


def _export(cmd):
    new_object = None
    def _create_new_set(scene):
        print("Making new set")
        nonlocal new_object
        current_roots = scene.get_scene_objects(only_roots=True)
        set_name = "MAYA_DATA_EXPORT"
        maya_id = uuid.uuid1()
        new_object = common._create_data(scene, set_name, str(maya_id), current_roots)
    
    #remove any previous exports
    temp_dir = pathlib.Path(os.path.join(tempfile.gettempdir(), 'mayacasc'))
    print('Cascaduer Export Location {}'.format(temp_dir))
    if not temp_dir.exists():
        temp_dir.mkdir()

    #delete previous entries
    for child in temp_dir.iterdir():
        child.unlink(missing_ok=True)
        
    scene = pycsc.get_current_scene().ds
    
    #See if we have an export set selected
    selected = scene.get_scene_objects(selected=True)
    export_sets = _get_maya_sets(selected)
    
    #If not see if we can find any in the current scene
    if not export_sets:
        transforms = scene.get_scene_objects(of_type='Basic')
        export_sets = _get_maya_sets(transforms)

        if not export_sets:
            #Set mistakenly became transforms when migrating to pycsc
            #so now I have to cover this edge case.
            transforms = scene.get_scene_objects(of_type="Transform")
            export_sets = _get_maya_sets(transforms)            

        
        if export_sets:
            print("Found previous import")
            print(export_sets)
        
    #If not, then this must be a first time export, so let's make an export set
    if not export_sets:
        scene.edit('Create Maya Export Set', _create_new_set)
        export_sets =  _get_maya_sets([new_object])
        

    up_axis = common.get_coord_system()
    if up_axis is None:
        print("Couldn't get Maya's Up Axis. Is Maya Running? Export Failed")
        return
        
    for export_set in export_sets:
        root_beh = export_set.get_behaviour_by_name(common.MAYA_ROOTS)
        roots = [beh.object for beh in root_beh.behaviours.get()]
        
        new_selection = []
        for root in roots:
            new_selection.extend(hierarchy.get_object_branch_inclusive(root, root.scene))
            
        scene.edit('Change selection', _select_for_export, new_selection)

        maya_beh = root_beh.get_siblings_by_name(common.MAYA_BEHAVIOUR_NAME)[0]
        maya_id = maya_beh.datasWithSameNamesReadonly.get_by_name('maya_id')
        if maya_id:
            maya_id = maya_id[0]
            fbx_name = '{}.{}.fbx'.format(root_beh.object.name, maya_id.get())
            
            export_path = str(temp_dir.joinpath(fbx_name))
            
            print("Exporting to {}".format(fbx_name))
            
            bake_anim_data = maya_beh.datasWithSameNames.get_by_name(common.BAKE_ANIMATION)
            if not bake_anim_data:
                common._add_export_settings(maya_beh)
                bake_anim_data = maya_beh.datasWithSameNames.get_by_name(common.BAKE_ANIMATION)
                
            settings = csc.fbx.FbxSettings()
            settings.bake_animation = bake_anim_data[0].get()
            settings.up_axis = up_axis

            #TODO: Change this to selection, once we know how to select a branch
            fbx.export_fbx(export_path, fbx.FbxFilterType.SELECTED) 
        

    server.send_to_maya(common._active_port_number, cmd)


def export_maya_animation():
    cmd = "cg3dcasc.core.import_fbx()"
    _export(cmd)
    

def smart_export(port_number):
    common.set_active_port(port_number)
    export_maya_animation()
    

def run(*args, **kwargs):
    export_maya_animation()
