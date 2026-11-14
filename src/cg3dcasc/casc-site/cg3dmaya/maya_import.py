


import json
#import typing
import tempfile
import os
import pathlib
#import uuid

import common.hierarchy as hierarchy
#import rig_gen.add_support_info as rg_s_inf
#import commands.rig_info.add_joints as aj
import csc
import pycsc
import rig_mode.on as rm_on
#import rig_mode.off as rm_off

#from . import server

from . import common
from . import fbx



def _import_maya_qrig_file(file_path):
    scene_manager = csc.app.get_application().get_scene_manager()
    application_scene = scene_manager.current_scene()
    rm_on.run_raw(application_scene.domain_scene(), [0.0, 0.5, 0.0])
    rig_tool = csc.app.get_application().get_tools_manager().get_tool('RiggingToolWindowTool').editor(application_scene)
    rig_tool.open_quick_rigging_tool()
    rig_tool.load_template_by_fileName(file_path)
    rig_tool.generate_rig_elements()
    
    
def _get_object_by_id(object_list, maya_id):
    for obj in object_list:
        beh = obj.get_behaviour_by_name(common.MAYA_BEHAVIOUR_NAME)
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
        new_selection.extend(hierarchy.get_object_branch_inclusive(root, root.scene))
        
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



MATERIAL_INFO_FILE = 'material_info.json'
MATERIAL_INFO_VERSION = 1

_MATERIAL_MAP_RESETS = {
    'normal_map': '',
    'base_color_map': '',
    'emissive_color_map': '',
    'roughness_map': '',
    'metallic_map': '',
    'reflectance_map': '',
    'ambient_occlusion_map': '',
    'roughness_channel': 0,
    'metallic_channel': 0,
    'reflectance_channel': 0,
    'ambient_occlusion_channel': 0,
}


def _path_segments(path):
    return [
        part
        for part in str(path).replace('\\', '/').replace('|', '/').split('/')
        if part
    ]


def _without_namespace(name):
    return str(name).rsplit(':', 1)[-1]


def _material_name(material):
    prop = material.get_property('name')
    return prop.get() if prop and prop.id is not None else ''


def _mesh_materials(obj):
    mesh = obj.get_behaviour_by_name('MeshObject')
    if not mesh:
        return []
    return list(mesh.get_property('materials').get())


def _mesh_score(obj, mesh_data):
    maya_name = mesh_data.get('name', '')
    exact_name = obj.name == maya_name
    short_name = _without_namespace(obj.name) == _without_namespace(maya_name)
    if not exact_name and not short_name:
        return -1

    maya_parts = _path_segments(mesh_data.get('path', maya_name))
    casc_parts = _path_segments(obj.get_path_name().to_string())
    suffix_matches = 0
    for maya_part, casc_part in zip(reversed(maya_parts), reversed(casc_parts)):
        if maya_part == casc_part:
            suffix_matches += 1
        elif _without_namespace(maya_part) == _without_namespace(casc_part):
            suffix_matches += 1
        else:
            break

    wanted_materials = {
        item.get('name', '') for item in mesh_data.get('materials', [])
    }
    found_materials = {_material_name(item) for item in _mesh_materials(obj)}
    material_matches = len(wanted_materials.intersection(found_materials))
    return (100 if exact_name else 50) + suffix_matches * 10 + material_matches * 20


def _match_mesh(meshes, mesh_data, used):
    candidates = [item for item in meshes if item not in used]
    scored = sorted(
        ((_mesh_score(item, mesh_data), item) for item in candidates),
        key=lambda item: item[0],
        reverse=True,
    )
    if not scored or scored[0][0] < 0:
        return None
    return scored[0][1]


def _set_material_values(scene, material, values):
    # Treat the sidecar as a complete snapshot of the material's texture
    # mappings. Clearing first ensures a disconnected or reassigned Maya map
    # cannot leave its previous Cascadeur path/channel behind.
    updates = dict(_MATERIAL_MAP_RESETS)
    updates.update(values)
    for field, value in updates.items():
        prop = material.get_property(field)
        if not prop or prop.id is None:
            print("Cascadeur Material has no '{}' property".format(field))
            continue
        scene.de.set_data_value(prop.id, value)


def _apply_mesh_materials(scene, obj, mesh_data):
    materials = _mesh_materials(obj)
    by_name = {}
    for material in materials:
        by_name.setdefault(_material_name(material), []).append(material)

    applied = 0
    for material_data in mesh_data.get('materials', []):
        name = material_data.get('name', '')
        matches = by_name.get(name, [])
        if not matches:
            matches = [
                material
                for material in materials
                if _without_namespace(_material_name(material))
                == _without_namespace(name)
            ]
        slot = material_data.get('slot', -1)
        material = matches[0] if matches else None
        if material is None and 0 <= slot < len(materials):
            # FBX owns the polygon-to-slot assignment. Slot order is the safest
            # fallback when a DCC has renamed a material during import.
            material = materials[slot]
        if material is None:
            print("Can't find material '{}' on '{}'".format(name, obj.name))
            continue
        _set_material_values(scene, material, material_data.get('properties', {}))
        applied += 1
    return applied


def _load_materials(scene):
    temp_dir = pathlib.Path(os.path.join(tempfile.gettempdir(), 'mayacasc'))
    material_path = temp_dir.joinpath(MATERIAL_INFO_FILE)
    if not material_path.exists():
        # Embed mode deliberately has no sidecar and performs no texture work.
        return

    with material_path.open(encoding='utf-8') as material_file:
        document = json.load(material_file)
    if document.get('version') != MATERIAL_INFO_VERSION:
        scene.warning('Unsupported Maya material data version')
        return

    def mod(edit_scene):
        all_sets, unused_selected = common.get_export_sets(edit_scene)
        sets_by_id = common.get_ids(all_sets)
        applied = 0
        for export_data in document.get('exports', []):
            export_set = sets_by_id.get(export_data.get('id'))
            if export_set is None:
                print(
                    "Can't find imported Maya set '{}'".format(
                        export_data.get('set_name', export_data.get('id'))
                    )
                )
                continue

            branch = set()
            for root in common.get_set_members(export_set):
                branch.update(hierarchy.get_object_branch_inclusive(root, root.scene))
            meshes = [item for item in branch if item.has_behaviour('MeshObject')]
            used = set()
            for mesh_data in export_data.get('meshes', []):
                obj = _match_mesh(meshes, mesh_data, used)
                if obj is None:
                    print("Can't find Maya mesh '{}'".format(mesh_data.get('path')))
                    continue
                used.add(obj)
                applied += _apply_mesh_materials(edit_scene, obj, mesh_data)
        edit_scene.su.generate_update()
        print('Applied {} Maya material instance(s)'.format(applied))

    scene.edit('Load Maya Materials', mod)


def _import_maya(new_scene, import_filter: fbx.FbxFilterType):
    if new_scene:
        scene = pycsc.new_scene().ds
    else:
        scene = pycsc.get_current_scene().ds

    scene.info("Importing Maya Data")
    temp_dir = pathlib.Path(os.path.join(tempfile.gettempdir(), 'mayacasc'))
    if not temp_dir.exists():
        scene.error("Can't find Maya data")
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
        
    #up_axis = common.get_maya_coord_system()
    #if up_axis is None:
        #print("Couldn't get Maya's Up Axis. Is Maya Running? Export Failed")
        #return

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
            #To-Do: Find a way to make this update the mesh for existing data
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


            settings = csc.fbx.FbxSettings()
            #settings.up_axis = up_axis
            fbx.import_fbx(fbx_path, modified_filter, False, settings)

            current_roots = set(scene.get_scene_objects(only_roots=True))
            new_roots = current_roots.difference(scene_roots)
            scene_roots = current_roots               


        #Let's find the stuff that was just imported and create a way
        #to search for it later.
        if existing_data is None and modified_filter != fbx.FbxFilterType.SKIP:
            scene.edit('Import maya data', common._create_data, set_name, maya_id, new_roots)
            if qrig_path:
                _make_rig_info(scene, set_name, new_roots)
        else:
            scene.info("Updated existing data")


    _load_materials(scene)


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
    
    
def smart_import():
    _import_maya(False, fbx.FbxFilterType.AUTO)
    
    
def update_textures():
    """Read the latest Maya material sidecar and replace current mappings."""
    scene = pycsc.get_current_scene().ds
    return _load_materials(scene)
