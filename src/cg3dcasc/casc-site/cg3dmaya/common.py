


#import json
#import typing
#import tempfile
#import os
#import pathlib
import uuid

#import common.hierarchy
#import rig_gen.add_support_info as rg_s_inf
#import commands.rig_info.add_joints as aj
import csc
#import rig_mode.on as rm_on
#import rig_mode.off as rm_off

from . import server
import pycsc
#import pycsc as cg3dguru
#import pycsc.general.fbx as fbx


MAYA_BEHAVIOUR_NAME = 'Maya Data'
MAYA_ROOTS = 'Maya Roots'
BAKE_ANIMATION = 'Bake Animation'


_active_port_number = None


def get_active_port():
    if _active_port_number is None:
        scene = pycsc.get_current_scene().ds
        scene.error("Maya not connected")
        return -1

    return _active_port_number

        
def _add_export_settings(behaviour):
    behaviour.datasWithSameNames.create_data(BAKE_ANIMATION, csc.model.DataMode.Static, True, group_name='{} update'.format(MAYA_BEHAVIOUR_NAME))
    

def _create_data(scene, set_name, maya_id, new_roots):
    global MAYA_BEHAVIOUR_NAME
     
    #make the selection/object set
    
    try:
        obj = scene.create_object(set_name, simple=True)
    except:
        obj = scene.create_object(set_name)
        
    if isinstance(obj.handle, csc.update.Object):
        obj = obj.object_id()
        
    behaviour = obj.add_behaviour('Dynamic', MAYA_BEHAVIOUR_NAME)
    data_prop = behaviour.get_property('datasWithSameNamesReadonly')
    data_prop.create_data('maya_id', csc.model.DataMode.Static, maya_id, group_name='{} update'.format(MAYA_BEHAVIOUR_NAME))

    _add_export_settings(behaviour)

    roots_behaviour = obj.add_behaviour('DynamicBehaviour', MAYA_ROOTS)
    roots_behaviour.behaviours.set([obj.Basic for obj in new_roots])
    

    behaviour = obj.get_behaviour_by_name(MAYA_BEHAVIOUR_NAME)
    
    return obj


def create_export_set(scene):
    new_object = None
    def _create_new_set(scene):
        print("Making new set")
        nonlocal new_object
        current_roots = scene.get_scene_objects(only_roots=True)
        if not current_roots:
            return
        
        set_name = "MAYA_DATA_EXPORT"
        maya_id = uuid.uuid1()
        new_object = _create_data(scene, set_name, str(maya_id), current_roots)
        
    scene.edit('Create Maya Export Set', _create_new_set)
    return new_object


def get_export_sets(scene, selected=False):
    export_sets = {b.object for b in scene.get_behaviours(MAYA_BEHAVIOUR_NAME)}
    selected_sets = {o for o in scene.get_scene_objects(selected=True) if o in export_sets}
    
    return (export_sets, selected_sets)


def get_maya_set_ids():
    """Return a list of ids in the current scene"""

    cmd = "cg3dcasc.core.get_set_ids()"
    success, data = server.send_and_listen(get_active_port(), cmd)
    if not success:
        return None

    return set(data)


def get_maya_coord_system():
    """returns the active coordinate system in Maya"""
    
    cmd = "cg3dcasc.core.get_coord_system()"
    success, data = server.send_and_listen(get_active_port(), cmd)
    if not success:
        return None

    match data.lower():
        case 'x':
            return csc.fbx.FbxSettingsAxis.X
        case 'y':
            return csc.fbx.FbxSettingsAxis.Y
        case 'z':
            return csc.fbx.FbxSettingsAxis.Z
        case _:
            return None

     
def set_active_port(port_number):
    global _active_port_number
    _active_port_number = int(port_number)


def report_port_number():
    global _active_port_number
    scene = pycsc.get_current_scene().ds
    scene.success(f"Connected to :{_active_port_number}")

