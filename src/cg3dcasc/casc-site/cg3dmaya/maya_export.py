

import json
import typing
import tempfile
import os
import pathlib
import shutil
import uuid

import csc
import pycsc
import common.hierarchy as hierarchy

from . import common
from . import server
from . import fbx


temp_dir = pathlib.Path(os.path.join(tempfile.gettempdir(), 'mayacasc'))
HIK_MAPPING_VERSION = 1


def _select_for_export(scene, new_selection):
    scene.select(new_selection)


def _with_required_ancestors(objects):
    """Return objects plus every parent transform required by FBX export."""
    result = []
    # Some host/test wrappers are equality-comparable but intentionally
    # unhashable, so use a short ordered list rather than a set here.
    seen = []
    for obj in objects:
        chain = []
        current = obj
        while current is not None and current not in seen:
            chain.append(current)
            current = getattr(current, 'parent', None)
        for item in reversed(chain):
            if item not in seen:
                seen.append(item)
                result.append(item)
    return result
    
    
def _clean_export_location():
    print('Cascadeur Export Location {}'.format(temp_dir))
    temp_root = pathlib.Path(tempfile.gettempdir()).resolve()
    export_dir = temp_dir.resolve()
    if export_dir.parent != temp_root:
        raise RuntimeError(
            "Refusing to clear unexpected export directory '{}'".format(export_dir)
        )

    export_dir.mkdir(parents=True, exist_ok=True)

    #delete previous entries
    for child in export_dir.iterdir():
        if child.is_symlink() or child.is_file():
            child.unlink(missing_ok=True)
        elif child.is_dir():
            shutil.rmtree(child)
        else:
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
        new_selection = _with_required_ancestors(new_selection)

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
            if not pathlib.Path(export_path).is_file():
                scene.error(
                    "Maya Bridge FBX export failed; no file was created at {}".format(
                        export_path
                    )
                )
                return False

    cmd = "cg3dcasc.core.import_fbx()"
    server.send_to_maya(common._active_port_number, cmd)
    return True


def _rig_export_content(scene, rig_info):
    """Return RigInfo joints and meshes influenced by those joints."""
    joints = set(rig_info.related_joints.get())
    meshes = set()
    for mesh_behaviour in scene.get_behaviours('MeshObject'):
        if joints.intersection(mesh_behaviour.linked_objects.get()):
            meshes.add(mesh_behaviour.object)
    return joints | meshes


def _rig_export_roots(export_objects):
    """Reduce character content to the top-level roots stored by normal sets."""
    return common._get_roots_from_selected(set(export_objects))


def _spline_ik_chains(scene, rig_joints):
    """Return SplineIK joint names belonging to this character.

    Cascadeur's reference range is not guaranteed to be hierarchical. Maya
    restores parent-chain order after the FBX skeleton has been imported.
    """
    rig_joints = set(rig_joints)
    chains = []
    # Normal scenes contain SplineIk. Rig Mode can still expose the proto
    # behaviour, whose ``joints`` range has the same meaning.
    for behaviour_name in ('SplineIk', 'ProtoSplineIk'):
        for spline_ik in scene.get_behaviours(behaviour_name):
            chain = [joint_behaviour.object for joint_behaviour in spline_ik.joints.get()]
            if len(chain) < 2 or not rig_joints.intersection(chain):
                continue
            names = [joint.name for joint in chain]
            if names not in chains:
                chains.append(names)
    return chains


def _new_rig_export_set(scene, rig_info, export_objects):
    """Create the persistent Maya export set used by later updates."""
    result = None
    export_roots = _rig_export_roots(export_objects)

    def create(edit_scene):
        nonlocal result
        set_name = '{}_CSC_EXPORT'.format(rig_info.object.name.rstrip('_'))
        result = common._create_data(
            edit_scene,
            set_name,
            str(uuid.uuid1()),
            export_roots,
        )

    scene.edit('Create Maya Character Export Set', create)
    return result


def _matching_rig_export_set(scene, rig_info, export_objects):
    """Find an export set whose members exactly match this character."""
    all_sets, unused_selected_sets = common.get_export_sets(scene)
    expected_name = '{}_CSC_EXPORT'.format(rig_info.object.name.rstrip('_'))
    export_roots = _rig_export_roots(export_objects)
    matches = [
        export_set
        for export_set in all_sets
        if common.get_set_members(export_set) == export_roots
    ]
    if not matches:
        return None
    return min(
        matches,
        key=lambda export_set: (
            export_set.name != expected_name,
            export_set.name,
        ),
    )


def _get_or_create_rig_export_set(scene, rig_info, export_objects):
    """Reuse the character's export set so its Maya ID remains stable."""
    existing = _matching_rig_export_set(scene, rig_info, export_objects)
    if existing is not None:
        return existing
    return _new_rig_export_set(scene, rig_info, export_objects)


def export_character_and_rig():
    """Export one Cascadeur RigInfo skeleton and its influenced meshes to Maya."""
    scene = pycsc.get_current_scene().ds
    rig_infos = list(scene.get_behaviours('RigInfo'))
    if not rig_infos:
        scene.error("Can't export character: no Rig Info behaviour was found.")
        return False
    if len(rig_infos) != 1:
        scene.error("Can't export multiple characters. The scene has multiple Rig Info behaviours.")
        return False

    rig_info = rig_infos[0]
    qrt_json = rig_info.qrt_json.get()
    if not qrt_json or not qrt_json.strip():
        scene.error("Can't export character: Rig Info does not define qrt_json.")
        return False
    try:
        json.loads(qrt_json)
    except (TypeError, ValueError):
        scene.error("Can't export character: Rig Info qrt_json is invalid.")
        return False

    rig_joints = set(rig_info.related_joints.get())
    if not rig_joints:
        scene.error("Can't export character: Rig Info does not define any related joints.")
        return False
    export_objects = _rig_export_content(scene, rig_info)

    try:
        _clean_export_location()
    except (OSError, RuntimeError) as error:
        scene.error("Could not clear Maya Bridge export location: {}".format(error))
        return False

    export_set = _get_or_create_rig_export_set(scene, rig_info, export_objects)
    if export_set is None:
        scene.error("Can't export character: the Maya export set could not be created.")
        return False

    export_behaviour = export_set.get_behaviour_by_name(common.MAYA_BEHAVIOUR_NAME)
    maya_id = export_behaviour.datasWithSameNamesReadonly.get_by_name('maya_id')[0].get()
    filename_base = '{}.{}'.format(export_set.name, maya_id).replace(':', '_')
    temp_dir.joinpath(filename_base + '.qrigcasc').write_text(qrt_json, encoding='utf-8')
    temp_dir.joinpath(filename_base + '.hikmap').write_text(
        json.dumps(
            {
                'version': HIK_MAPPING_VERSION,
                'spline_ik_chains': _spline_ik_chains(scene, rig_joints),
            },
            indent=2,
        ),
        encoding='utf-8',
    )

    _export(scene, {export_set})
    return True

 
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
    try:
        _clean_export_location()
    except (OSError, RuntimeError) as error:
        scene.error("Could not clear Maya Bridge export location: {}".format(error))
        return False
    determine_export_action(scene)
    return True


def run(*args, **kwargs):
    export_maya_animation()
