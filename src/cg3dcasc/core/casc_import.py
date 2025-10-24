
#import json
import tempfile
import os
import pathlib
   
import pymel.core as pm
from . import hik

#from cg3dcasc import preferences

import wingcarrier.pigeons
import cg3dguru.udata
import cg3dguru.animation.fbx
import cg3dguru.utils

from .udata import *
#from . import client
#from . import command_port
from . import server
from . import common


def import_from_casc():
    cmd = f"cg3dmaya.export_maya_animation()"
    server.send_to_casc(cmd)
    

def get_import_files():
    files = {}

    temp_dir = pathlib.Path(os.path.join(tempfile.gettempdir(), 'mayacasc'))
    if not temp_dir.exists():
        pm.error("Can't find Maya data")
        return files

    for child in temp_dir.iterdir():
        name, ext = child.name.rsplit('.', 1)
        if name not in files:
            files[name] = dict()
            
        files[name][ext.lower()] = str(child)
        
        
    return files


def import_fbx():
    files = get_import_files()
    print(f"Importing:{files}")
    
    scene_sets = pm.ls(type='objectSet')
    existing_exports = cg3dguru.udata.Utils.get_nodes_with_data(scene_sets, data_class=CascExportData)
    scene_roots = set(pm.ls(assemblies=True))

    for key, item in files.items():
        fbx_path = item.get('fbx', '')
        qrig_path = item.get('qrigcasc', '')    

        set_name, maya_id = key.split('.')
        if fbx_path:
            matching_id_node = None
            for node in existing_exports:
                if node.cscDataId.get() == maya_id:
                    matching_id_node = node
                    break            
            
            #switch any hik character to None, so we can see the animation
            character_node = None
            if matching_id_node:
                character_node = common.get_character_node(matching_id_node.cscDataId)
            if character_node:
                hik.set_character_source(character_node, hik.SourceType.NONE)
            
            #Import the FBX data
            print('importing {}'.format(fbx_path))
            cg3dguru.animation.fbx.import_fbx(fbx_path)
            current_roots = set(pm.ls(assemblies=True))

            #should we always update with the latest roots?
            new_roots = current_roots.difference(scene_roots)
            scene_roots = current_roots
            
            if matching_id_node is None:
                print("Adding new casc objects: {}".format(new_roots))
                new_node, data = CascExportData.create_node(nodeType='objectSet')
                pm.rename(new_node, set_name)
                if new_roots:
                    new_node.addMembers(new_roots)

                data.cscDataId.unlock()
                data.cscDataId.set(maya_id)
                data.cscDataId.lock()                
                
                
        if qrig_path:
            print("Can't import rigs at the moment")


def run():
    pass

    
