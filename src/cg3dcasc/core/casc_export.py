
import json
import tempfile
import os
import pathlib
import time

import pymel.core as pm
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


def get_root_parent(input_transform):
    """Returns the highest level transform node for the given input transform"""
    parent = input_transform.getParent()
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
            


def node_type_exportable(node):
    """See if the node set to export is a valid node type"""
    #This is used by the editor, so don't remove this function
    #just because it's not being used in the core.py
    if isinstance(node, pm.nodetypes.Joint) \
       or isinstance(node, pm.nodetypes.Mesh) \
     or isinstance(node, pm.nodetypes.SkinCluster) \
     or isinstance(node, pm.nodetypes.Transform):
        return True
    
    return False


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
        common.get_skinned_data_sets(export_data.node().flattened())    
    
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
    
    root_transforms = set()
    add_transform_roots(joints, root_transforms)
    add_transform_roots(meshes, root_transforms)
    add_transform_roots(transforms, root_transforms)    

    if export_fbx:
        pm.mel.eval('if (!`pluginInfo -q -l "fbxmaya"`){ loadPlugin "fbxmaya"; }')
        #Hik should be exported from the stand position only when
        #exporting a rig
        current_source = None
        if export_rig and character_node:
            current_source = hik.get_character_source(character_node)
            hik.set_character_source(character_node, hik.SourceType.STANCE)

        user_selection = pm.ls(sl=True)
        if dynamic:
            pm.select(list(root_transforms), replace=True)
        else:
            pm.select(list(transforms), replace=True)
            pm.select(list(skin_clusters), add=True)
            pm.select(list(meshes), add=True)
            pm.select(list(joints), add=True)
            
        file_id = export_data.cscDataId.get()
        node_name = export_data.node().name().split(':')[-1]
        filename = '{}.{}.fbx'.format(node_name, file_id)
        fbx_file_path = export_folder.joinpath(filename)
        print('FBX file: {}'.format(fbx_file_path))
        
        prefs = preferences.get()
        bake = prefs.bake_animations == preferences.OptionEnum.ALWAYS
        if prefs.bake_animations == preferences.OptionEnum.ASK:
            result = pm.confirmDialog(title='Export Animations', message='Bake Animation?', messageAlign='center', button=['Yes', 'No'], defaultButton='Yes', cancelButton='No', dismissString='No')
            bake = result == 'Yes'
            
        fbx.export(fbx_file_path, bake_animations=bake, include_children=dynamic)

        pm.select(user_selection, replace=True)
        
        if export_rig and character_node:
            hik.set_character_source(character_node, current_source)

    if export_rig and character_node:
        qrig_file_path = ''
        filename = '{}.{}.qrigcasc'.format(node_name, file_id)
        qrig_file_path = export_folder.joinpath(filename)
        casc_qrt.export_qrig_file(character_node, qrig_data, qrig_file_path)
        
        
    return root_transforms


def _build_default_set():
    exportables = []
    selection = pm.ls(sl=True)
    if selection:
        exportables = selection
    else:
        assemblies = set(pm.ls(assemblies=True))
        cameras = set(pm.ls(type='camera'))
        for c in cameras:
            #camera's are shape data, so we need to get the tranform
            assemblies.discard(c.getParent())
            
        exportables = list(assemblies)

    if not exportables:
        return None
        
    export_node, data = CascExportData.create_node(nodeType='objectSet')
    if exportables:
        export_node.addMembers(exportables)
        
    pm.rename(export_node, 'CACS_EXPORT')
    pm.select(selection, replace=True)
    
    return export_node


def cascadeur_available():
    #start_time = time.time()
    result = wingcarrier.pigeons.CascadeurPigeon().can_dispatch()
    #print(f"Time to check Dispatch: {time.time() - start_time}")
    return result


def export(export_set=None, export_rig=False, cmd='', textures=True, only_textures=False):
    if cmd and not cascadeur_available():
        pm.displayError("Please make sure Cascadeur is running and try again.")
        #pm.confirmDialog(message="Please launch Cascadeur, then try again.",button=['Okay'])
        return False
    
    #remove any previous exports
    temp_dir = pathlib.Path(os.path.join(tempfile.gettempdir(), 'mayacasc'))
    print('Cascaduer Export Location {}'.format(temp_dir))
    if not temp_dir.exists():
        temp_dir.mkdir()

    #delete previous entries
    for child in temp_dir.iterdir():
        child.unlink() #missing_ok=True) #missing_ok=True) #missing_ok doens't work for maya 2022

    if export_set:
        export_nodes = [export_set]
    else:
        export_nodes = common.get_export_nodes()
        if not export_nodes:
            default_set = _build_default_set()
            if default_set:
                export_nodes = [default_set]
            else:
                pm.confirmDialog(message="Nothing was found to export. Select some items to export and try again.", button=['Okay'])
                return False                
             
    #export our data 
    export_roots = set()
    for node in export_nodes:
        roots = _export_data(node, temp_dir, export_rig, not only_textures)
        export_roots.update(roots)
        
    #Let's export our texture info
    texture_mappings = {}
    if textures or only_textures:
        print("Exporting textures")
        for root in export_roots:
            branch = pm.listRelatives(root, allDescendents=True)
            results = materials.get_textures(branch, export_nodes)
            texture_mappings.update(results)
            
        print(texture_mappings)
        texture_file = open(temp_dir.joinpath('texture_info.json'), 'w')
        formatted_str = json.dumps(texture_mappings, indent=4)
        texture_file.write(formatted_str)
        texture_file.close()

    if cmd:
        server.send_to_casc(cmd)

    return True
        

def update_animations():
    export(cmd=u"cg3dmaya.update_animations()", textures=False)
    
    
def update_models():
    export(cmd=u"cg3dmaya.update_models()")
    
    
def update_textures():
    export(cmd=u"cg3dmaya.update_textures()", only_textures=True)
    
    
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

    
