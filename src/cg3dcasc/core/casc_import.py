
#import json
import tempfile
import os
import pathlib
   
from maya import cmds
from . import hik

import wingcarrier.pigeons
import cg3dguru.udata
#import cg3dguru.animation.fbx
import cg3dguru.utils

from .udata import *
#from . import client
#from . import command_port
from . import server
from . import common
from . import fbx
from . import casc_qrt


def import_from_casc():
    cmd = f"cg3dmaya.export_maya_animation()"
    server.send_to_casc(cmd)
    

def get_import_files():
    files = {}

    temp_dir = pathlib.Path(os.path.join(tempfile.gettempdir(), 'mayacasc'))
    if not temp_dir.exists():
        cmds.error("Can't find Maya data")
        return files

    for child in temp_dir.iterdir():
        name, ext = child.name.rsplit('.', 1)
        if name not in files:
            files[name] = dict()
            
        files[name][ext.lower()] = str(child)
        
        
    return files


def _imported_joints(roots):
    roots = list(roots or [])
    joints = set(cmds.ls(roots, type='joint', long=True) or [])
    if roots:
        joints.update(
            cmds.listRelatives(
                roots,
                allDescendents=True,
                type='joint',
                fullPath=True,
            )
            or []
        )
    return sorted(joints or (cmds.ls(type='joint', long=True) or []))


def import_fbx():
    if not cmds.pluginInfo("fbxmaya", query=True, loaded=True):
        cmds.loadPlugin("fbxmaya")
    files = get_import_files()
    print(f"Importing:{files}")
    
    scene_sets = cmds.ls(type='objectSet') or []
    existing_exports = cg3dguru.udata.Utils.get_nodes_with_data(scene_sets, data_class=CascExportData)
    scene_roots = set(cmds.ls(assemblies=True, long=True) or [])

    for key, item in files.items():
        fbx_path = item.get('fbx', '')
        qrig_path = item.get('qrigcasc', '')
        hikmap_path = item.get('hikmap', '')

        set_name, maya_id = key.split('.')
        target_export_node = None
        new_roots = set()
        if fbx_path:
            matching_id_node = None
            for node in existing_exports:
                if node.cscDataId.get() == maya_id:
                    matching_id_node = node
                    break            
            
            #switch any hik character to None, so we can see the animation
            character_node = None
            if matching_id_node:
                character_node = common.get_character_node(matching_id_node)
            if character_node:
                hik.set_character_source(character_node, hik.SourceType.NONE)
            
            #Import the FBX data
            print('importing {}'.format(fbx_path))
            #cg3dguru.animation.fbx.import_fbx(fbx_path)
            fbx.import_fbx(fbx_path)
            current_roots = set(cmds.ls(assemblies=True, long=True) or [])

            #should we always update with the latest roots?
            new_roots = current_roots.difference(scene_roots)
            scene_roots = current_roots
            
            if matching_id_node is None:
                print("Adding new casc objects: {}".format(new_roots))
                new_node, data = CascExportData.create_node(nodeType='objectSet')
                new_node = cmds.rename(str(new_node), set_name)
                data = CascExportData.get_data(new_node)
                if new_roots:
                    cmds.sets(list(new_roots), addElement=new_node)

                data.cscDataId.unlock()
                data.cscDataId.set(maya_id)
                data.cscDataId.lock()
                target_export_node = new_node
            else:
                target_export_node = matching_id_node.node()
                
                
        if qrig_path:
            if target_export_node is None:
                cmds.warning("Can't create HIK definition without imported FBX data.")
                continue
            character = casc_qrt.import_qrig_character(
                qrig_path,
                hikmap_path,
                _imported_joints(new_roots),
                target_export_node,
            )
            print("Created HIK character definition: {}".format(character.name()))


def run():
    pass

    
