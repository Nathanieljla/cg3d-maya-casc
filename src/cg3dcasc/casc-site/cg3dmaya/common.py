


#import json
#import typing
#import tempfile
#import os
#import pathlib
#import uuid

#import common.hierarchy
#import rig_gen.add_support_info as rg_s_inf
#import commands.rig_info.add_joints as aj
import csc
#import rig_mode.on as rm_on
#import rig_mode.off as rm_off

#from . import server

#import pycsc as cg3dguru
#import pycsc.general.fbx as fbx




MAYA_BEHAVIOUR_NAME = 'Maya Data'
MAYA_ROOTS = 'Maya Roots'
BAKE_ANIMATION = 'Bake Animation'


ACTIVE_PORT_ID = 6000

        
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

     
