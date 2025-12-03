

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


temp_dir = pathlib.Path(os.path.join(tempfile.gettempdir(), 'mayacasc'))


def _select_for_export(scene, new_selection):
    scene.select(new_selection)
    
    
def _clean_export_location():
    print('Cascaduer Export Location {}'.format(temp_dir))
    if not temp_dir.exists():
        temp_dir.mkdir()

    #delete previous entries
    for child in temp_dir.iterdir():
        child.unlink(missing_ok=True)    


def _export(scene, export_sets):
    
    if not export_sets:
        scene.warning("Maya Bridge: Nothing to export!")
        return      

    #up_axis = common.get_maya_coord_system()
    #if up_axis is None:
        #print("Couldn't get Maya's Up Axis. Is Maya Running? Export Failed")
        #return
        
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
            fbx_name = fbx_name.replace(":", "_")
            export_path = str(temp_dir.joinpath(fbx_name))

            print("Exporting to {}".format(fbx_name))
            
            bake_anim_data = maya_beh.datasWithSameNames.get_by_name(common.BAKE_ANIMATION)
            if not bake_anim_data:
                common._add_export_settings(maya_beh)
                bake_anim_data = maya_beh.datasWithSameNames.get_by_name(common.BAKE_ANIMATION)
                
            settings = csc.fbx.FbxSettings()
            settings.bake_animation = bake_anim_data[0].get()
            #axis is wrong
            #settings.up_axis = up_axis

            fbx.export_fbx(export_path, fbx.FbxFilterType.SELECTED, settings)
        
    cmd = "cg3dcasc.core.import_fbx()"
    server.send_to_maya(common._active_port_number, cmd)

 
def export_sets(scene, export_sets):
    cmd = "cg3dcasc.core.import_fbx()"
    

def create_new_set_and_export(scene):
    new_set = common.create_export_set(scene)
    export_sets = set() if new_set is None else {new_set}
    _export(scene, export_sets)


def determine_export_action(scene):
    maya_sets = common.get_all_maya_set_ids()
    if maya_sets is None:
        scene.error("Is Maya Connected? Export failed.")
        return    
    
    all_sets, selected_sets = common.get_export_sets(scene)
    export_sets = selected_sets if selected_sets else all_sets
    
    matches = set()
    for export_set in export_sets:
        maya_beh = export_set.get_behaviour_by_name(common.MAYA_BEHAVIOUR_NAME)
        maya_id = maya_beh.datasWithSameNamesReadonly.get_by_name('maya_id')[0].get()

        if maya_id in maya_sets:
            matches.add(export_set)

    title = ''
    message = ''
    dialog_buttons = ''                  

    title = f"Maya:{len(maya_sets)} Casc:{len(export_sets)} Common:{len(matches)}"
    if not export_sets:
        #title = f"Maya:{len(maya_sets)} Casc:0"
        message = "There's no data to export.\nDo you want to create a new export set and add it Maya?\n(The export set will contain all scene data)"
        dialog_buttons = [csc.view.DialogButton("Yes", lambda: create_new_set_and_export(scene)),
                          csc.view.DialogButton(csc.view.StandardButton.Cancel)]
    #0,1
    elif not maya_sets and export_sets:
        #title = f"Maya:0 Casc:{len(export_sets)}"
        message = "This will add new data to Maya. Continue?"
        dialog_buttons = [csc.view.DialogButton("Yes", lambda: _export(scene, export_sets)),
                          csc.view.DialogButton(csc.view.StandardButton.Cancel)]
    #!=
    elif len(export_sets) != len(matches):
        message = "What do you want to export?"
        all_message = "All Selected Export Sets" if export_sets == selected_sets else "All Scene Export Sets"
        dialog_buttons = [csc.view.DialogButton("Only Matching Export Sets", lambda: _export(scene, matches)),
                          csc.view.DialogButton(all_message, lambda: _export(scene, export_sets)),
                          csc.view.DialogButton(csc.view.StandardButton.Cancel)]
    #1,1
    else:
        #the amount of data matches between both scenes
        _export(scene, export_sets)
        return
    
    if message and dialog_buttons:
        csc.view.DialogManager.instance().show_buttons_dialog(title, message,
                                                              dialog_buttons)
        

def export_maya_animation():   
    scene = pycsc.get_current_scene().ds
    _clean_export_location()
    determine_export_action(scene)


def run(*args, **kwargs):
    export_maya_animation()
