
import json
import tempfile
import os
import pathlib
import shutil
import time

from maya import cmds
from . import hik

import wingcarrier.pigeons
import cg3dguru.udata
#import cg3dguru.animation.fbx as fbx

import cg3dguru.utils

from cg3dcasc import preferences
from .udata import *

from . import server
from . import common
from . import casc_qrt
from . import fbx
from . import materials
from . import maya as mayautil


def get_root_parent(input_transform):
    """Returns the highest level transform node for the given input transform"""
    parent = mayautil.parent(input_transform)
    if parent:
        return get_root_parent(parent)
    else:
        return input_transform
    
    
def add_transform_roots(transform_list, root_set):
    """Find the top level parent of each item in the list and add it to the set"""
    for dag in transform_list:
        root_parent = get_root_parent(dag)
        if root_parent not in root_set:
            root_set.add(root_parent)


def get_export_branches(root_transforms, *content_sets):
    """Return the nodes needed to export the given content from its roots

    Every node that is an ancestor of, is, or is a descendant of the content
    is kept. Branches under the roots that lead to no content at all get
    trimmed out. Selecting the result lets the FBX exporter run with
    include-children turned off, so rig controls and unrelated geometry stay
    out of the file.

    NOTE: the content sets must only contain DAG nodes. Don't pass in
    skin_clusters, as they aren't part of the DAG hierarchy.

    Args:
        root_transforms (set) : the top level parent of each content item.
        *content_sets : the joint, mesh and transform sets to keep.

    Returns:
        set : the transforms and shapes needed to export the content.
    """
    content = set()
    for content_set in content_sets:
        content.update(content_set)

    if not content:
        return set()

    branch = set(content)

    #ancestors: walk up from each item to its root. Branches that don't lead
    #to content never get walked, which is what trims them.
    for node in content:
        current = mayautil.parent(node)
        while current is not None and current not in branch:
            branch.add(current)

            #Every root_transform is parentless by construction, so this is
            #really just an early out. It's here so the roots read as an
            #explicit boundary.
            if current in root_transforms:
                break

            current = mayautil.parent(current)

    #descendants: anything under our content comes along for the ride, so a
    #skeleton stays whole below the joints that are actually skinned. Mesh
    #content is a shape node, which has no children of its own, so seed the
    #walk with its transform instead.
    seeds = set()
    for node in content:
        if cmds.objectType(str(node), isAType="shape"):
            seeds.add(mayautil.parent(node))
        else:
            seeds.add(node)

    branch.update(mayautil.descendants(seeds))

    return branch




def node_type_exportable(node):
    """See if the node set to export is a valid node type"""
    #This is used by the editor, so don't remove this function
    #just because it's not being used in the core.py
    return mayautil.node_type(node) in {
        "joint",
        "mesh",
        "skinCluster",
        "transform",
    }


def get_exportable_content(export_data):
    """Return a list of objects to export based on the ObjectSet elements
    
    When the CscExportData.dynamicSet is False then on the objects that are
    part of the ObjectSet will be returned.
    
    When the CscExportData.dynamicSet is True, then the function will look
    for any joints or meshes in the list and find their associated
    skinClusters. Then use these skinClusters to find a list of meshes and
    joints to include for export.    
    """

    
    joints, meshes, skin_clusters, transforms =\
        common.get_skinned_data_sets(mayautil.set_members(export_data.node()))
    
    if not export_data.dynamicSet.get():
        return (joints, meshes, skin_clusters, transforms)
           

    #We need to combine all joints and skinned meshes into a set of
    #skin_clusters, which can then be used to build a complete list
    #of joints and meshes that need exporting.
    character_node = common.get_character_node(export_data)
    if character_node:
        hik_joints = casc_qrt.get_hik_joints(character_node)
        joints.update(hik_joints)
        
    common.update_skinned_data_sets(joints, meshes, skin_clusters, transforms)

    return (joints, meshes, skin_clusters, transforms)

    

def _export_data(export_data, export_folder: pathlib.Path, export_rig: bool, export_fbx: bool):
    #When export_fbx and export_rig are both false then this function is
    #still useful as it will still returns a list of exportable_content
    qrig_data = QRigData.get_data(export_data.node())
    character_node = common.get_character_node(export_data)
    joints, meshes, skin_clusters, transforms = get_exportable_content(export_data)
    dynamic = export_data.dynamicSet.get()
    legacy = CascExportData.uses_legacy_export(export_data)

    file_id = export_data.cscDataId.get()
    node_name = export_data.node().name().split(':')[-1]

    root_transforms = set()
    add_transform_roots(joints, root_transforms)
    add_transform_roots(meshes, root_transforms)
    add_transform_roots(transforms, root_transforms)

    #This has to happen outside of the export_fbx block below, because
    #update_textures() runs this function with export_fbx off and still
    #needs to know what's being trimmed.
    if dynamic and not legacy:
        #0.2.0 : trim any branch that doesn't lead to exportable content
        export_content = get_export_branches(root_transforms, joints, meshes, transforms)
    else:
        export_content = root_transforms

    if export_fbx:
        if not cmds.pluginInfo("fbxmaya", query=True, loaded=True):
            cmds.loadPlugin("fbxmaya")
        #Hik should be exported from the stand position only when
        #exporting a rig
        current_source = None
        if export_rig and character_node:
            current_source = hik.get_character_source(character_node)
            hik.set_character_source(character_node, hik.SourceType.STANCE)

        user_selection = mayautil.ls(selection=True, long=True)
        if dynamic:
            #for legacy data export_content is the root transforms, which is
            #exactly what this used to select.
            cmds.select(mayautil.names(export_content), replace=True)
        else:
            cmds.select(mayautil.names(transforms), replace=True)
            cmds.select(mayautil.names(skin_clusters), add=True)
            cmds.select(mayautil.names(meshes), add=True)
            cmds.select(mayautil.names(joints), add=True)

        filename = '{}.{}.fbx'.format(node_name, file_id)
        fbx_file_path = export_folder.joinpath(filename)
        print('FBX file: {}'.format(fbx_file_path))
        
        prefs = preferences.get()
        bake = prefs.bake_animations == preferences.OptionEnum.ALWAYS
        if prefs.bake_animations == preferences.OptionEnum.ASK:
            result = cmds.confirmDialog(title='Export Animations', message='Bake Animation?', messageAlign='center', button=['Yes', 'No'], defaultButton='Yes', cancelButton='No', dismissString='No')
            bake = result == 'Yes'
            
        #0.2.0 selects the whole trimmed branch, so the exporter doesn't need
        #to pull in children of its own.
        fbx.export(
            fbx_file_path,
            bake_animations=bake,
            include_children=dynamic and legacy,
            embed_media=CascExportData.get_embed_textures(export_data),
        )

        if user_selection:
            cmds.select(mayautil.names(user_selection), replace=True)
        else:
            cmds.select(clear=True)
        
        if export_rig and character_node:
            hik.set_character_source(character_node, current_source)

    if export_rig and character_node:
        qrig_file_path = ''
        filename = '{}.{}.qrigcasc'.format(node_name, file_id)
        qrig_file_path = export_folder.joinpath(filename)
        casc_qrt.export_qrig_file(character_node, qrig_data, qrig_file_path)

    #For legacy and non-dynamic data, textures come off the whole root trees,
    #which is what actually gets exported. For 0.2.0 the trimmed branch is
    #already the complete list.
    if export_content is root_transforms:
        texture_nodes = set(root_transforms)
        if root_transforms:
            #NOTE: listRelatives() falls back to the active selection when
            #it's handed nothing, so the emptiness check isn't optional.
            texture_nodes.update(
                mayautil.descendants(root_transforms)
            )
    else:
        texture_nodes = export_content

    return texture_nodes


def _build_default_set():
    exportables = []
    selection = mayautil.ls(selection=True, long=True)
    if selection:
        exportables = selection
    else:
        assemblies = set(mayautil.ls(assemblies=True, long=True))
        cameras = set(mayautil.ls(type='camera', long=True))
        for c in cameras:
            #camera's are shape data, so we need to get the tranform
            assemblies.discard(mayautil.parent(c))
            
        exportables = list(assemblies)

    if not exportables:
        return None
        
    export_node, data = CascExportData.create_node(nodeType='objectSet')
    if exportables:
        mayautil.add_set_members(export_node, exportables)
        
    export_node = mayautil.rename(export_node, 'CACS_EXPORT')
    if selection:
        cmds.select(mayautil.names(selection), replace=True)
    else:
        cmds.select(clear=True)
    
    return CascExportData.get_data(export_node)


def cascadeur_available():
    #start_time = time.time()
    result = wingcarrier.pigeons.CascadeurPigeon().can_dispatch()
    #print(f"Time to check Dispatch: {time.time() - start_time}")
    return result


def _as_export_data(value):
    """Return the CascExportData block stored on a node or data handle."""
    if isinstance(value, cg3dguru.udata.Attribute):
        value = value.node()

    data = CascExportData.get_data(value)
    if data is None:
        raise ValueError(
            "Node {!r} does not contain CascExportData".format(value)
        )
    return data


def _clear_export_directory(directory):
    """Remove files and FBX media directories from an export directory."""
    for child in directory.iterdir():
        if child.is_symlink() or child.is_file():
            child.unlink()
        elif child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()


def export(export_set=None, export_rig=False, cmd='', textures=True, only_textures=False):
    if cmd and not cascadeur_available():
        cmds.error("Please make sure Cascadeur is running and try again.")
        return False
    
    #remove any previous exports
    temp_dir = pathlib.Path(os.path.join(tempfile.gettempdir(), 'mayacasc'))
    print('Cascaduer Export Location {}'.format(temp_dir))
    temp_dir.mkdir(parents=True, exist_ok=True)

    #delete previous entries
    _clear_export_directory(temp_dir)

    if export_set is not None:
        export_nodes = [_as_export_data(export_set)]
    else:
        export_sets = common.get_export_nodes()
        if export_sets:
            export_nodes = [_as_export_data(node) for node in export_sets]
        else:
            default_set = _build_default_set()
            if default_set:
                export_nodes = [_as_export_data(default_set)]
            else:
                cmds.confirmDialog(message="Nothing was found to export. Select some items to export and try again.", button=['Okay'])
                return False                
             
    #export our data
    material_exports = []
    for node in export_nodes:
        nodes = _export_data(node, temp_dir, export_rig, not only_textures)
        if (
            (textures or only_textures)
            and nodes
            and CascExportData.references_textures(node)
        ):
            material_exports.append(
                materials.build_export_data(node, list(nodes))
            )

    # Embed mode intentionally emits no material sidecar. In Reference mode,
    # Cascadeur updates the official Material instances created by FBX import.
    if material_exports:
        print("Exporting referenced materials")
        material_path = temp_dir.joinpath(materials.MATERIAL_INFO_FILE)
        with material_path.open("w", encoding="utf-8") as material_file:
            json.dump(
                materials.material_document(material_exports),
                material_file,
                indent=4,
            )

    if cmd:
        server.send_to_casc(cmd)

    return True
        

def update_animations():
    export(cmd=u"cg3dmaya.update_animations()", textures=False)
    
    
def update_models():
    export(cmd=u"cg3dmaya.update_models()")
    
    
def update_textures():
    """Rebuild and apply the current Reference material sidecar."""
    return export(cmd=u"cg3dmaya.update_textures()", only_textures=True)
    
    
def export_scene(new_scene):
    cmd = f"cg3dmaya.import_scene({new_scene})"
    export(cmd=cmd)
    

def export_rig(new_scene, export_set):
    cmd = f"cg3dmaya.import_rig({new_scene})"
    export(export_set, True, cmd=cmd)
    
    
def smart_export():
    cmd = f"cg3dmaya.smart_import()"
    export(cmd=cmd)

            
def run():
    pass

    
