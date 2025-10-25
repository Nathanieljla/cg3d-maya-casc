

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


def create_export_set(scene, current_roots=None):
    new_object = None
    def _create_new_set(scene):
        print("Making new set")
        nonlocal new_object, current_roots
        
        if current_roots is None:
            current_roots = scene.get_scene_objects(only_roots=True)
            
        if not current_roots:
            return
        
        set_name = "MAYA_DATA_EXPORT"
        maya_id = uuid.uuid1()
        new_object = _create_data(scene, set_name, str(maya_id), current_roots)
        
    scene.edit('Create Maya Export Set', _create_new_set)
    return new_object


def get_export_sets(scene, selected=False):
    all_sets = {b.object for b in scene.get_behaviours(MAYA_BEHAVIOUR_NAME)}
    selected_sets = {o for o in scene.get_scene_objects(selected=True) if o in all_sets}
    
    return (all_sets, selected_sets)


def _get_roots_from_selected(selected):
    searched = set()
    roots = set()
    def walk_up(obj):
        nonlocal roots, searched

        if obj in searched:
            return
        
        searched.add(obj)
        parent = obj.parent
        if parent is None:
            roots.add(obj)
            return
        else:
            walk_up(parent)

    for obj in selected:
        walk_up(obj)
        
    return roots


def _get_filtered_selection(scene):
    selected = scene.get_scene_objects(selected=True)
    selected = {obj for obj in selected if not isinstance(obj.handle, csc.domain.Tool_object_id)}
    if not selected:
        scene.error("Please select some objects")
        return []

    return _get_roots_from_selected(selected)


def _add_to_set(scene, objects, target_set):
    def mod(scene):
        nonlocal objects, target_set
        
        root_beh = target_set.get_behaviour_by_name(MAYA_ROOTS)
        if not root_beh:
            scene.error("Can't find Maya Roots Behaviour")
            return

        for obj in objects:
            basic_beh = obj.get_behaviour_by_name("Basic")
            if not basic_beh:
                continue
            
            root_beh.behaviours.add(basic_beh)

    scene.edit("Add selected to set", mod)


def add_selection_to(new_set: bool):
    scene = pycsc.get_current_scene().ds
    selected_roots = _get_filtered_selection(scene)
    if not selected_roots:
        return

    all_sets, selected_sets = get_export_sets(scene)
    maya_roots = set()
    
    for export_set in all_sets:
        beh = export_set.get_behaviour_by_name(MAYA_ROOTS)
        if beh:
            assigned_roots = {b.object for b in beh.behaviours.get()}
            maya_roots.update(assigned_roots)

    new_roots = {obj for obj in selected_roots if obj not in maya_roots and obj not in all_sets}
    if not new_roots:
        scene.error("Selected objects are already assigned to existing export sets")
        return
    
    target_sets = selected_sets if selected_sets else all_sets
    if new_set or not target_sets:
        create_export_set(scene, new_roots)
        return

    if len(target_sets) == 1:
        _add_to_set(scene, new_roots, list(target_sets)[0])
        return

    dialog_buttons = []
    for target_set in target_sets:
        dialog_buttons.append(
            csc.view.DialogButton(target_set.name, lambda: _add_to_set(scene, new_roots, target_set))
        )
        
    dialog_buttons.append(csc.view.DialogButton(csc.view.StandardButton.Cancel))
    csc.view.DialogManager.instance().show_buttons_dialog("Add selected to", "Pick a set to add you selection to",
                                                          dialog_buttons)


def remove_selection_from():
    scene = pycsc.get_current_scene().ds
    selected_roots = _get_filtered_selection(scene)
    if not selected_roots:
        return

    all_sets, selected_sets = get_export_sets(scene)
    selected_roots = {obj for obj in selected_roots if obj not in all_sets}
    roots_to_remove = {}
    removed_count = 0
    for export_set in all_sets:
        beh = export_set.get_behaviour_by_name(MAYA_ROOTS)
        if not beh:
            continue
        
        assigned_roots = {b.object for b in beh.behaviours.get()}
        common_elements = assigned_roots & selected_roots
        if common_elements:
            common_elements = {obj.get_behaviour_by_name("Basic") for obj in common_elements if obj.get_behaviour_by_name("Basic")}
            roots_to_remove[beh] = common_elements
            removed_count += len(common_elements)
            
    def mod(scene):
        nonlocal roots_to_remove
        for beh, objs in roots_to_remove.items():
            for obj in objs:
                beh.behaviours.remove(obj)

    scene.edit("Remove selected from export set", mod)
    scene.success(f"Removed {common_elements} count")
    


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
    
    
    


