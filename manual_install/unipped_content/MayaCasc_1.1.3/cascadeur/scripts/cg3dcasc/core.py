
import json
import tempfile
import os
#import typing
import uuid
#import winreg
#import psutil
import pathlib

import pymel.core as pm
from . import hik
from . import preferences

import wingcarrier.pigeons
import cg3dguru.udata
import cg3dguru.animation.fbx
import cg3dguru.utils



class SpineException(Exception):
    """Thrown when an export is attempted without an upper spine bone defined"""
    pass

#https://forums.autodesk.com/t5/maya-programming/python-hik/td-p/4262564
#https://mayastation.typepad.com/maya-station/2011/04/maya-2012-hik-menus-and-mel-commands-part-1.html
#https://github.com/bungnoid/glTools/blob/master/utils/hik.py

HIK_ATTRS = {
    'Reference': None, 
    'Hips': 'pelvis',
    'HipsTranslation' : None, 
    'Spine': 'stomach',
    #anyone of the spine1-9 could be the chest bone.
    #which is based on the user_data selection
    'Spine1': 'chest', 
    'Spine2': 'chest',
    'Spine3': 'chest',
    'Spine4': 'chest',
    'Spine5': 'chest',
    'Spine6': 'chest',
    'Spine7': 'chest',
    'Spine8': 'chest',
    'Spine9': 'chest',
    'Neck': 'neck',
    'Neck1': None,
    'Neck2': None,
    'Neck3': None,
    'Neck4': None,
    'Neck5': None,
    'Neck6': None,
    'Neck7': None,
    'Neck8': None,
    'Neck9': None, 
    'Head': 'head',
    'LeftUpLeg': 'thigh_l',
    'LeftLeg': 'calf_l',
    'LeftFoot': 'foot_l',
    'LeftToeBase': 'toe_l',
    'LeftShoulder': 'clavicle_l',
    'LeftShoulderExtra': None, 
    'LeftArm': 'arm_l',
    'LeftForeArm': 'forearm_l',
    'LeftHand': 'hand_l',
    'LeftFingerBase': None,
    'LeftHandThumb1': 'thumb_l_1', 
    'LeftHandThumb2': 'thumb_l_2',
    'LeftHandThumb3': 'thumb_l_3',
    'LeftHandThumb4': None,
    'LeftHandIndex1': 'index_finger_l_1',
    'LeftHandIndex2': 'index_finger_l_2',
    'LeftHandIndex3': 'index_finger_l_3',
    'LeftHandIndex4': None,
    'LeftHandMiddle1':'middle_finger_l_1',
    'LeftHandMiddle2': 'middle_finger_l_2',
    'LeftHandMiddle3': 'middle_finger_l_3',
    'LeftHandMiddle4': None,
    'LeftHandRing1':'ring_finger_l_1',
    'LeftHandRing2':'ring_finger_l_2',
    'LeftHandRing3':'ring_finger_l_3',
    'LeftHandRing4': None,
    'LeftHandPinky1':'pinky_l_1', #pinky_finger_l_1 (finger isn't in the name 2023.2)
    'LeftHandPinky2':'pinky_l_2', 
    'LeftHandPinky3':'pinky_l_3',
    'LeftHandPinky4': None,
    'LeftHandExtraFinger1': None,
    'LeftHandExtraFinger2': None, 
    'LeftHandExtraFinger3': None, 
    'LeftHandExtraFinger4': None,
    'LeftInHandThumb': None,
    'LeftInHandIndex': None,
    'LeftInHandMiddle': None,
    'LeftInHandRing': None,
    'LeftInHandPinky': None,
    'LeftInHandExtraFinger': None,
    'LeftFootThumb1': None, 
    'LeftFootThumb2': None,
    'LeftFootThumb3': None,
    'LeftFootThumb4': None,
    'LeftFootIndex1': None,
    'LeftFootIndex2': None,
    'LeftFootIndex3': None,
    'LeftFootIndex4': None,
    'LeftFootMiddle1': None,
    'LeftFootMiddle2': None,
    'LeftFootMiddle3': None,
    'LeftFootMiddle4': None,
    'LeftFootRing1': None,
    'LeftFootRing2': None,
    'LeftFootRing3': None,
    'LeftFootRing4': None,
    'LeftFootPinky1': None,
    'LeftFootPinky2': None,
    'LeftFootPinky3': None,
    'LeftFootPinky4': None,
    'LeftFootExtraFinger1': None,
    'LeftFootExtraFinger2': None, 
    'LeftFootExtraFinger3': None, 
    'LeftFootExtraFinger4': None,
    'LeftInFootThumb': None,
    'LeftInFootIndex': None,
    'LeftInFootMiddle': None,
    'LeftInFootRing': None,
    'LeftInFootPinky': None, 
    'LeftInFootExtraFinger': None,
    'LeftUpLegRoll' : None, #this isn't in the HIK UI
    'LeftLegRoll': None, #this isn't in the HIK UI
    'LeftArmRoll': None, #this isn't in the HIK UI
    'LeftForeArmRoll': None, #this isn't in the HIK UI
    'LeafLeftUpLegRoll1': 'thigh_l',
    'LeafLeftUpLegRoll2': 'thigh_l', #new in 2023.2
    'LeafLeftUpLegRoll3': 'thigh_l', #new in 2023.2
    'LeafLeftUpLegRoll4': 'thigh_l', #new in 2023.2
    'LeafLeftUpLegRoll5': 'thigh_l', #new in 2023.2
    'LeafLeftLegRoll1': 'calf_l',
    'LeafLeftLegRoll2': 'calf_l', #new in 2023.2
    'LeafLeftLegRoll3': 'calf_l', #new in 2023.2
    'LeafLeftLegRoll4': 'calf_l', #new in 2023.2
    'LeafLeftLegRoll5': 'calf_l', #new in 2023.2
    'LeafLeftArmRoll1': 'arm_l',
    'LeafLeftArmRoll2': 'arm_l', #new in 2023.2
    'LeafLeftArmRoll3': 'arm_l', #new in 2023.2
    'LeafLeftArmRoll4': 'arm_l', #new in 2023.2
    'LeafLeftArmRoll5': 'arm_l', #new in 2023.2
    'LeafLeftForeArmRoll1': 'forearm_l',
    'LeafLeftForeArmRoll2': 'forearm_l', #new in 2023.2
    'LeafLeftForeArmRoll3': 'forearm_l', #new in 2023.2
    'LeafLeftForeArmRoll4': 'forearm_l', #new in 2023.2
    'LeafLeftForeArmRoll5': 'forearm_l', #new in 2023.2
    'RightUpLeg': 'thigh_r',
    'RightLeg': 'calf_r',
    'RightFoot': 'foot_r',
    'RightToeBase': 'toe_r',
    'RightShoulder': 'clavicle_r',
    'RightShoulderExtra': None, 
    'RightArm': 'arm_r',
    'RightForeArm': 'forearm_r',
    'RightHand': 'hand_r',
    'RightFingerBase': None,
    'RightHandThumb1': 'thumb_r_1', 
    'RightHandThumb2': 'thumb_r_2',
    'RightHandThumb3': 'thumb_r_3',
    'RightHandThumb4': None,
    'RightHandIndex1': 'index_finger_r_1',
    'RightHandIndex2': 'index_finger_r_2',
    'RightHandIndex3': 'index_finger_r_3',
    'RightHandIndex4': None,
    'RightHandMiddle1':'middle_finger_r_1',
    'RightHandMiddle2': 'middle_finger_r_2',
    'RightHandMiddle3': 'middle_finger_r_3',
    'RightHandMiddle4': None,
    'RightHandRing1':'ring_finger_r_1',
    'RightHandRing2':'ring_finger_r_2',
    'RightHandRing3':'ring_finger_r_3',
    'RightHandRing4': None,
    'RightHandPinky1':'pinky_r_1', #pinky_finger_r_1 (the finger isn't part of the pink name?)
    'RightHandPinky2':'pinky_r_2', 
    'RightHandPinky3':'pinky_r_3',
    'RightHandPinky4': None,
    'RightHandExtraFinger1': None,
    'RightHandExtraFinger2': None, 
    'RightHandExtraFinger3': None, 
    'RightHandExtraFinger4': None,
    'RightInHandThumb': None,
    'RightInHandIndex': None,
    'RightInHandMiddle': None,
    'RightInHandRing': None,
    'RightInHandPinky': None,
    'RightInHandExtraFinger': None,
    'RightFootThumb1': None, 
    'RightFootThumb2': None,
    'RightFootThumb3': None,
    'RightFootThumb4': None,
    'RightFootIndex1': None,
    'RightFootIndex2': None,
    'RightFootIndex3': None,
    'RightFootIndex4': None,
    'RightFootMiddle1': None,
    'RightFootMiddle2': None,
    'RightFootMiddle3': None,
    'RightFootMiddle4': None,
    'RightFootRing1': None,
    'RightFootRing2': None,
    'RightFootRing3': None,
    'RightFootRing4': None,
    'RightFootPinky1': None,
    'RightFootPinky2': None,
    'RightFootPinky3': None,
    'RightFootPinky4': None,
    'RightFootExtraFinger1': None,
    'RightFootExtraFinger2': None, 
    'RightFootExtraFinger3': None, 
    'RightFootExtraFinger4': None,
    'RightInFootThumb': None,
    'RightInFootIndex': None,
    'RightInFootMiddle': None,
    'RightInFootRing': None,
    'RightInFootPinky': None, 
    'RightInFootExtraFinger': None,
    'RightUpLegRoll' : None, #this isn't in the HIK UI
    'RightLegRoll': None, #this isn't in the HIK UI
    'RightArmRoll': None, #this isn't in the HIK UI
    'RightForeArmRoll': None, #this isn't in the HIK UI
    'LeafRightUpLegRoll1': 'thigh_r',
    'LeafRightUpLegRoll2': 'thigh_r', #new in 2023.2
    'LeafRightUpLegRoll3': 'thigh_r', #new in 2023.2
    'LeafRightUpLegRoll4': 'thigh_r', #new in 2023.2
    'LeafRightUpLegRoll5': 'thigh_r', #new in 2023.2 
    'LeafRightLegRoll1': 'calf_r',
    'LeafRightLegRoll2': 'calf_r', #new in 2023.2
    'LeafRightLegRoll3': 'calf_r', #new in 2023.2
    'LeafRightLegRoll4': 'calf_r', #new in 2023.2
    'LeafRightLegRoll5': 'calf_r', #new in 2023.2 
    'LeafRightArmRoll1': 'arm_r',
    'LeafRightArmRoll2': 'arm_r', #new in 2023.2
    'LeafRightArmRoll3': 'arm_r', #new in 2023.2
    'LeafRightArmRoll4': 'arm_r', #new in 2023.2
    'LeafRightArmRoll5': 'arm_r', #new in 2023.2 
    'LeafRightForeArmRoll1': 'forearm_r',
    'LeafRightForeArmRoll2': 'forearm_r', #new in 2023.2
    'LeafRightForeArmRoll3': 'forearm_r', #new in 2023.2
    'LeafRightForeArmRoll4': 'forearm_r', #new in 2023.2
    'LeafRightForeArmRoll5': 'forearm_r', #new in 2023.2
}


TWIST_PERCENTS = {
    'LeafLeftUpLegRoll1': 'ParamLeafLeftUpLegRoll1',
    'LeafLeftUpLegRoll2': 'ParamLeafLeftUpLegRoll2', 
    'LeafLeftUpLegRoll3': 'ParamLeafLeftUpLegRoll3', 
    'LeafLeftUpLegRoll4': 'ParamLeafLeftUpLegRoll4', 
    'LeafLeftUpLegRoll5': 'ParamLeafLeftUpLegRoll5',
    'LeafLeftLegRoll1': 'ParamLeafLeftLegRoll1',
    'LeafLeftLegRoll2': 'ParamLeafLeftLegRoll2', 
    'LeafLeftLegRoll3': 'ParamLeafLeftLegRoll3', 
    'LeafLeftLegRoll4': 'ParamLeafLeftLegRoll4', 
    'LeafLeftLegRoll5': 'ParamLeafLeftLegRoll5',
    
    'LeafLeftArmRoll1': 'ParamLeafLeftArmRoll1',
    'LeafLeftArmRoll2': 'ParamLeafLeftArmRoll2', 
    'LeafLeftArmRoll3': 'ParamLeafLeftArmRoll3', 
    'LeafLeftArmRoll4': 'ParamLeafLeftArmRoll4', 
    'LeafLeftArmRoll5': 'ParamLeafLeftArmRoll5',
    'LeafLeftForeArmRoll1': 'ParamLeafLeftForeArmRoll1',
    'LeafLeftForeArmRoll2': 'ParamLeafLeftForeArmRoll2',
    'LeafLeftForeArmRoll3': 'ParamLeafLeftForeArmRoll3',
    'LeafLeftForeArmRoll4': 'ParamLeafLeftForeArmRoll4',
    'LeafLeftForeArmRoll5': 'ParamLeafLeftForeArmRoll5',
    
    'LeafRightUpLegRoll1': 'ParamLeafRightUpLegRoll1',
    'LeafRightUpLegRoll2': 'ParamLeafRightUpLegRoll2',
    'LeafRightUpLegRoll3': 'ParamLeafRightUpLegRoll3',
    'LeafRightUpLegRoll4': 'ParamLeafRightUpLegRoll4',
    'LeafRightUpLegRoll5': 'ParamLeafRightUpLegRoll5',
    'LeafRightLegRoll1': 'ParamLeafRightLegRoll1',
    'LeafRightLegRoll2': 'ParamLeafRightLegRoll2',
    'LeafRightLegRoll3': 'ParamLeafRightLegRoll3',
    'LeafRightLegRoll4': 'ParamLeafRightLegRoll4',
    'LeafRightLegRoll5': 'ParamLeafRightLegRoll5',
    
    'LeafRightArmRoll1': 'ParamLeafRightArmRoll1',
    'LeafRightArmRoll2': 'ParamLeafRightArmRoll2',
    'LeafRightArmRoll3': 'ParamLeafRightArmRoll3',
    'LeafRightArmRoll4': 'ParamLeafRightArmRoll4',
    'LeafRightArmRoll5': 'ParamLeafRightArmRoll5',
    'LeafRightForeArmRoll1': 'ParamLeafRightForeArmRoll1',
    'LeafRightForeArmRoll2': 'ParamLeafRightForeArmRoll2',
    'LeafRightForeArmRoll3': 'ParamLeafRightForeArmRoll3',
    'LeafRightForeArmRoll4': 'ParamLeafRightForeArmRoll4',
    'LeafRightForeArmRoll5': 'ParamLeafRightForeArmRoll5',
}


TWIST_AXES = {
    'LeafLeftUpLegRoll1': 'leftUpperLegTwist',
    'LeafLeftUpLegRoll2': 'leftUpperLegTwist', 
    'LeafLeftUpLegRoll3': 'leftUpperLegTwist', 
    'LeafLeftUpLegRoll4': 'leftUpperLegTwist', 
    'LeafLeftUpLegRoll5': 'leftUpperLegTwist',
    'LeafLeftLegRoll1': 'leftLegTwist',
    'LeafLeftLegRoll2': 'leftLegTwist', 
    'LeafLeftLegRoll3': 'leftLegTwist', 
    'LeafLeftLegRoll4': 'leftLegTwist', 
    'LeafLeftLegRoll5': 'leftLegTwist',
    
    'LeafLeftArmRoll1': 'leftArmTwist',
    'LeafLeftArmRoll2': 'leftArmTwist', 
    'LeafLeftArmRoll3': 'leftArmTwist', 
    'LeafLeftArmRoll4': 'leftArmTwist', 
    'LeafLeftArmRoll5': 'leftArmTwist',
    'LeafLeftForeArmRoll1': 'leftForearmTwist',
    'LeafLeftForeArmRoll2': 'leftForearmTwist',
    'LeafLeftForeArmRoll3': 'leftForearmTwist',
    'LeafLeftForeArmRoll4': 'leftForearmTwist',
    'LeafLeftForeArmRoll5': 'leftForearmTwist',
    
    'LeafRightUpLegRoll1': 'rightUpperLegTwist',
    'LeafRightUpLegRoll2': 'rightUpperLegTwist',
    'LeafRightUpLegRoll3': 'rightUpperLegTwist',
    'LeafRightUpLegRoll4': 'rightUpperLegTwist',
    'LeafRightUpLegRoll5': 'rightUpperLegTwist',
    'LeafRightLegRoll1': 'rightLegTwist',
    'LeafRightLegRoll2': 'rightLegTwist',
    'LeafRightLegRoll3': 'rightLegTwist',
    'LeafRightLegRoll4': 'rightLegTwist',
    'LeafRightLegRoll5': 'rightLegTwist',
    
    'LeafRightArmRoll1': 'rightArmTwist',
    'LeafRightArmRoll2': 'rightArmTwist',
    'LeafRightArmRoll3': 'rightArmTwist',
    'LeafRightArmRoll4': 'rightArmTwist',
    'LeafRightArmRoll5': 'rightArmTwist',
    'LeafRightForeArmRoll1': 'rightForearmTwist',
    'LeafRightForeArmRoll2': 'rightForearmTwist',
    'LeafRightForeArmRoll3': 'rightForearmTwist',
    'LeafRightForeArmRoll4': 'rightForearmTwist',
    'LeafRightForeArmRoll5': 'rightForearmTwist',
}


_ACTIVE_CHARACTER_NODE = None
_ACTIVE_USER_DATA = None


class QRigData(cg3dguru.udata.BaseData):
    """A block of data to help convert an HIK character to Cascaduer's quick rig"""


    @staticmethod
    def get_attributes():
        attrs = [
            cg3dguru.udata.create_attr('characterNode', 'message'),
            cg3dguru.udata.create_attr('chestJoint', 'message'),
            cg3dguru.udata.create_attr('leftWeapon', 'message'),
            cg3dguru.udata.create_attr('rightWeapon', 'message'),
            cg3dguru.udata.create_attr('alignPelvis', 'bool'),
            cg3dguru.udata.create_attr('createLayers', 'bool'),
            
            cg3dguru.udata.Attr('leftArmTwist', 'enum', enumName='X:Y:Z'),
            cg3dguru.udata.Attr('leftForearmTwist', 'enum', enumName='X:Y:Z'),
            
            cg3dguru.udata.Attr('leftUpperLegTwist', 'enum', enumName='X:Y:Z'),
            cg3dguru.udata.Attr('leftLegTwist', 'enum', enumName='X:Y:Z'),
            
            cg3dguru.udata.Attr('rightArmTwist', 'enum', enumName='X:Y:Z'),
            cg3dguru.udata.Attr('rightForearmTwist', 'enum', enumName='X:Y:Z'),
            
            cg3dguru.udata.Attr('rightUpperLegTwist', 'enum', enumName='X:Y:Z'),
            cg3dguru.udata.Attr('rightLegTwist', 'enum', enumName='X:Y:Z'), 
            
            #cg3dguru.udata.Compound('twistAxes', 'compound', children =[
                #cg3dguru.udata.Attr('leftArm', 'enum', enumName='X:Y:Z'),
                #cg3dguru.udata.Attr('leftForearm', 'enum', enumName='X:Y:Z'),
                #cg3dguru.udata.Attr('leftUpLeg', 'enum', enumName='X:Y:Z'),
                #cg3dguru.udata.Attr('leftLeg', 'enum', enumName='X:Y:Z'),
                #cg3dguru.udata.Attr('rightArm', 'enum', enumName='X:Y:Z'),
                #cg3dguru.udata.Attr('rightForearm', 'enum', enumName='X:Y:Z'),
                #cg3dguru.udata.Attr('rightUpLeg', 'enum', enumName='X:Y:Z'),
                #cg3dguru.udata.Attr('rightLeg', 'enum', enumName='X:Y:Z'), 
            #])
            
        ]
        
        return attrs
    
    @classmethod
    def post_create(cls, data):
        data.createLayers.set(1)
        
    
    
class CascExportData(cg3dguru.udata.BaseData):
    """A list for nodes that should always be sent to cascadeur
    
    The CascExportData.exportNodes attribute can store meshes, joints, and
    skinClusters. Meshes, joints and skinClusters will be inspected to find
    all dependent joints and meshes. E.g. add a skinCluster and all joints
    will be exported (as well as the meshes they deform).
    """
    
    @staticmethod
    def get_attributes():
        attrs = [
            cg3dguru.udata.create_attr('cscDataId', 'string'),
            cg3dguru.udata.create_attr('dynamicSet', 'bool')
        ]
        
        return attrs
    
    @classmethod
    def post_create(cls, data):
        unique_id = uuid.uuid1()
        data.cscDataId.set(str(unique_id))
        data.cscDataId.lock()
        data.dynamicSet.set(1)



def _get_list_of_parents(transform, input_list):
    parent = transform.getParent()
    if parent is not None:
        input_list.append(parent.name())
        _get_list_of_parents(parent, input_list)
        
    else:
        input_list.reverse()
    


def _get_input_joint(key):
    global _ACTIVE_CHARACTER_NODE    

    attr = _ACTIVE_CHARACTER_NODE.attr(key)
    inputs = attr.inputs()
    if not inputs:
        return None
    
    return inputs[0]



def _joint_struct():
    #Just an alternative to joint_struct.copy()
    joint_struct = {
        'Bone name': '',
        'Joint name': '',
        'Joint path': [],
    }
    
    return joint_struct


def _get_joint_entry(hik_key, joint_struct = None, joint=None):
    if joint_struct is None:
        joint_struct = _joint_struct()
        joint_struct['Bone name'] = HIK_ATTRS[hik_key]
        
    if joint is None: 
        joint = _get_input_joint(hik_key)
        if joint is None:
            return joint_struct
    
    parent_list = []
    _get_list_of_parents(joint, parent_list)
    
    joint_struct['Joint name'] = joint.name().lstrip('|')
    joint_struct['Joint path'] = parent_list
    return joint_struct
    

def _get_section(section_name, keys, twist_data = False, user_data=None):
    names_list = []
    #This should always exist
    hik_properties = _ACTIVE_CHARACTER_NODE.propertyState.get()
    
    for key in keys:
        joint_struct = _get_joint_entry(key)
        ##let's skip invalid results
        if joint_struct['Joint name']:
            if twist_data:
                joint_struct['Strength'] = hik_properties.attr(TWIST_PERCENTS[key]).get()
                joint_struct['Axis'] = user_data.attr(TWIST_AXES[key]).get()         
            
            names_list.append(joint_struct)        
    
    output = {
        'Section': section_name,
        'Names' : names_list
    }
    
    return output


def _get_settings_values(user_data):
    if user_data is None:
        return (False, True)
    
    return (user_data.alignPelvis.get(), user_data.createLayers.get())



def _add_weapon_entry(section, bone_name, joint):
    weapon_struct = _joint_struct()
    weapon_struct['Bone name'] = bone_name
    _get_joint_entry('', weapon_struct, joint)
    section['Names'].append(weapon_struct)    



def get_qrig_struct(user_data = None):
    default_spine = 'Spine1'
    left_weapon = ''
    right_weapon = ''
    if user_data:
        left_weapon = user_data.leftWeapon.inputs()
        right_weapon = user_data.rightWeapon.inputs()
        if left_weapon:
            left_weapon = left_weapon[0]
            
        if right_weapon:
            right_weapon = right_weapon[0]
        
        
        spine_joints = get_spine_joints(_ACTIVE_CHARACTER_NODE)
        if len(spine_joints) > 2:
            if not user_data.chestJoint.inputs():
                raise SpineException()
            
            selected_chest_joint = user_data.chestJoint.inputs()[0]
            for spine_name, joint in spine_joints:
                if joint == selected_chest_joint:
                    default_spine = spine_name
                    print('spine name {}'.format(spine_name))
    
    
    l_arm_section = _get_section('Left arm', ['LeftShoulder', 'LeftArm', 'LeftForeArm', 'LeftHand'])
    r_arm_section =  _get_section('Right arm', ['RightShoulder', 'RightArm', 'RightForeArm', 'RightHand'])
    
    if left_weapon:
        _add_weapon_entry(l_arm_section, 'weapon_l', left_weapon)

    if right_weapon:
        _add_weapon_entry(r_arm_section, 'weapon_r', right_weapon)
        
    body_title = {
        'Title' : 'Body',
        'Sections' :  [
            _get_section('Body', ['Hips', 'Spine', default_spine, 'Neck', 'Head']),
            l_arm_section, #_get_section('Left arm', ['LeftShoulder', 'LeftArm', 'LeftForeArm', 'LeftHand']),
            r_arm_section, #_get_section('Right arm', ['RightShoulder', 'RightArm', 'RightForeArm', 'RightHand']),
            _get_section('Left leg', ['LeftUpLeg', 'LeftLeg', 'LeftFoot', 'LeftToeBase']),
            _get_section('Right leg', ['RightUpLeg', 'RightLeg', 'RightFoot', 'RightToeBase']),
            ]
    }
    
    l_hand_title = {
        'Title' : 'Left hand',
        'Sections' :  [
            _get_section('Thumb', ['LeftHandThumb1', 'LeftHandThumb2', 'LeftHandThumb3']),
            _get_section('Index finger', ['LeftHandIndex1', 'LeftHandIndex2', 'LeftHandIndex3']),
            _get_section('Middle finger', ['LeftHandMiddle1', 'LeftHandMiddle2', 'LeftHandMiddle3']),
            _get_section('Ring finger', ['LeftHandRing1', 'LeftHandRing2', 'LeftHandRing3']),
            _get_section('Pinky', ['LeftHandPinky1', 'LeftHandPinky2', 'LeftHandPinky3']),
    
            ]
    }
    
    r_hand_title = {
        'Title' : 'Right hand',
        'Sections' :  [
            _get_section('Thumb', ['RightHandThumb1', 'RightHandThumb2', 'RightHandThumb3']),
            _get_section('Index finger', ['RightHandIndex1', 'RightHandIndex2', 'RightHandIndex3']),
            _get_section('Middle finger', ['RightHandMiddle1', 'RightHandMiddle2', 'RightHandMiddle3']),
            _get_section('Ring finger', ['RightHandRing1', 'RightHandRing2', 'RightHandRing3']),
            _get_section('Pinky', ['RightHandPinky1', 'RightHandPinky2', 'RightHandPinky3']),
            ]
    }
    
    twists_title = {
        'Title' : 'Twist bones',
        'Sections' :  [
            _get_section('Left arm',
                         ['LeafLeftArmRoll1', 'LeafLeftArmRoll2',
                          'LeafLeftArmRoll3', 'LeafLeftArmRoll4',
                          'LeafLeftArmRoll5',
                          'LeafLeftForeArmRoll1', 'LeafLeftForeArmRoll2',
                          'LeafLeftForeArmRoll3', 'LeafLeftForeArmRoll4',
                          'LeafLeftForeArmRoll5'],
                         twist_data=True, user_data=user_data),
            
            _get_section('Right arm', ['LeafRightArmRoll1', 'LeafRightArmRoll2',
                          'LeafRightArmRoll3', 'LeafRightArmRoll4',
                          'LeafRightArmRoll5',
                          'LeafRightForeArmRoll1', 'LeafRightForeArmRoll2',
                          'LeafRightForeArmRoll3', 'LeafRightForeArmRoll4',
                          'LeafRightForeArmRoll5'],
                         twist_data=True, user_data=user_data),
            
            _get_section('Left leg', ['LeafLeftUpLegRoll1', 'LeafLeftUpLegRoll2',
                          'LeafLeftUpLegRoll3', 'LeafLeftUpLegRoll4',
                          'LeafLeftUpLegRoll5',
                          'LeafLeftLegRoll1', 'LeafLeftLegRoll2',
                          'LeafLeftLegRoll3', 'LeafLeftLegRoll4',
                          'LeafLeftLegRoll5'],
                         twist_data=True, user_data=user_data),
            _get_section('Right leg', ['LeafRightUpLegRoll1', 'LeafRightUpLegRoll2',
                          'LeafRightUpLegRoll3', 'LeafRightUpLegRoll4',
                          'LeafRightUpLegRoll5',
                          'LeafRightLegRoll1', 'LeafRightLegRoll2',
                          'LeafRightLegRoll3', 'LeafRightLegRoll4',
                          'LeafRightLegRoll5'],
                         twist_data=True, user_data=user_data),
            ]
    } 
    
    root = {}
    root['Document'] = [body_title, l_hand_title, r_hand_title, twists_title]
    
    align_pelvis, create_layers = _get_settings_values(user_data)
    root['Settings'] = {
        'Is align pelvis': align_pelvis,
        'Is create layers' : create_layers,
    }
    
    return root



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
            
            
            
def has_twist(character_node, twist_names = None):
    """Returns true if the twist(roll) attribute names are connected to a joint
    
    When no name(s) are provided all twist attributes are checked.
    """
    if twist_names is None:
        twist_names = [key for key, value in TWIST_AXES.items()]
        
    if isinstance(twist_names, str):
        twist_names = [twist_names]
        
    has_twist = False
    for name in twist_names:
        if character_node.attr(name).inputs():
            has_twist = True
            
    return has_twist
            


def get_skinned_meshes(character_node):
    """return a list of meshes that are deformed by the hik character joints"""
    global _ACTIVE_CHARACTER_NODE
    _ACTIVE_CHARACTER_NODE = character_node
    
    joints = []
    for key in HIK_ATTRS:
        joint = _get_input_joint(key)
        if joint:
            joints.append(joint)
            
    skin_clusters = {}
    for joint in joints:
        world_matrix = joint.attr('worldMatrix')
        outputs = world_matrix.outputs()
        for output in outputs:
            if output.type() == 'skinCluster':
                skin_clusters[output.name()] = output
                
    print(skin_clusters)
    results = []
    for key, skin_cluster in skin_clusters.items():
        output_geo = skin_cluster.attr('outputGeometry')
        for geo in output_geo.outputs():
            if geo not in results:
                results.append(geo)
                
    return results


def get_joint_skin_clusters(joints):
    """Given a list of joints, return a set of associated skinClusters"""
    
    clusters = set()
    for joint in joints:
        world_matrix = joint.attr('worldMatrix')
        outputs = world_matrix.outputs()
        for output in outputs:
            if output.type() == 'skinCluster' and output not in clusters:
                clusters.add(output)
                
    return clusters
                
                
def get_skin_cluster_joints(skin_clusters):
    """Given a list of skinClusters, return a set of associated joints"""
    joint_set = set()
    for skin_cluster in skin_clusters:
        temp_set = set(skin_cluster.matrix.inputs())
        joint_set.update(temp_set)
        
    return joint_set


def get_mesh_skin_clusters(meshes):
    """Given a list of meshes, return a set of associated skinClusters"""
    clusters = set()
    for m in meshes:
        inputs = m.inMesh.inputs()
        if inputs and isinstance(inputs[0], pm.nodetypes.SkinCluster):
            clusters.add(inputs[0])
            
    return clusters


def get_skin_cluster_meshes(skin_clusters):
    """Given a list of skinClusters, return a set of associated meshes"""
    meshes = set()
    for cluster in skin_clusters:
        output_geo = cluster.attr('outputGeometry')
        
        results = output_geo.outputs()
        for result in results:
            is_group_part = isinstance(result, pm.nodetypes.GroupParts)
            while is_group_part:
                result = result.outputGeometry.outputs()[0]
                is_group_part = isinstance(result, pm.nodetypes.GroupParts)
                
            if result not in meshes:
                meshes.add(result)            
        
        
        #for geo in output_geo.outputs():
            #if geo not in meshes:
                #meshes.add(geo)
                
    return meshes
    
    
def get_hik_joints(character_node):
    """Returns a set containing all the joints used by a character"""
    
    global _ACTIVE_CHARACTER_NODE
    _ACTIVE_CHARACTER_NODE = character_node
    
    joints = []
    for key in HIK_ATTRS:
        joint = _get_input_joint(key)
        if joint:
            joints.append(joint)
            
    return set(joints)



def get_spine_joints(character_node):
    """returns a list of tuples (spine_name, joint) that define the HIK spine"""

    spine_joints = []
    spine_names = ['Spine', 'Spine1', 'Spine2', 'Spine3', 'Spine4', 'Spine5',
                  'Spine6', 'Spine7', 'Spine8', 'Spine9']

    for spine_name in spine_names:
        attr = character_node.attr(spine_name)
        inputs = attr.inputs()
        if not inputs:
            return spine_joints
        else:
            spine_joints.append((spine_name, inputs[0]))

    return spine_joints


def export_qrig_file(character_node, qrig_data, filename):
    """Exports the character definition to a qrig file"""
    global _ACTIVE_CHARACTER_NODE

    _ACTIVE_CHARACTER_NODE = character_node
    result = get_qrig_struct(qrig_data)

    result_string = json.dumps(result, indent=4)

    print('QRig File: {}'.format(filename))
    f = open(filename, "w")
    f.write(result_string)
    f.close()

    return filename


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


def get_character_node(export_data):
    """Return any HIK character node associated with the export_data"""
    
    qrig_data = QRigData.get_data(export_data.node())
    character_node = None
    if qrig_data:
        inputs = qrig_data.characterNode.inputs()
        if not qrig_data.characterNode.inputs():
            pm.error("ERROR: cascadeur.core.export: qrig_data wasn't provided with HIK Character node")
        else:
            character_node = inputs[0]
            
    return character_node



def get_exportable_content(export_data):
    """Return a list of objects to export based on the ObjectSet elements
    
    When the CscExportData.dynamicSet is False then on the objects that are
    part of the ObjectSet will be returned.
    
    When the CscExportData.dynamicSet is True, then the function will look
    for any joints or meshes in the list and find their associated
    skinClusters. Then use these skinClusters to find a list of meshes and
    joints to include for export.    
    """
    
    if not export_data.dynamicSet.get():
        return set(export_data.node().flattened())
                
    character_node = get_character_node(export_data)
    joints = set()
    meshes = set()
    skin_clusters = set()
    transforms = set()

    #organize our exportExtra nodes into types
    for node in export_data.node().flattened():
        if isinstance(node, pm.nodetypes.Joint):
            joints.add(node)
        elif isinstance(node, pm.nodetypes.Mesh):
            meshes.add(node)
        elif isinstance(node, pm.nodetypes.SkinCluster):
            skin_clusters.add(node)
        elif isinstance(node, pm.nodetypes.Transform):
            transforms.add(node)
        else:
            pm.warning('Cascaduer Export: Ignoring object {}'.format(node.name()))

    #We need to combine all joints and skinned meshes into a set of
    #skin_clusters, which can then be used to build a complete list
    #of joints and meshes that need exporting.
    if character_node:
        hik_joints = get_hik_joints(character_node)
        joints.update(hik_joints)

    mesh_clusters = get_mesh_skin_clusters(meshes)
    skin_clusters.update(mesh_clusters)

    joint_skin_clusters = get_joint_skin_clusters(joints)
    skin_clusters.update(joint_skin_clusters)

    skinned_joints = get_skin_cluster_joints(skin_clusters)
    joints.update(skinned_joints)

    skinned_meshes = get_skin_cluster_meshes(skin_clusters)
    meshes.update(skinned_meshes)

    root_transforms = set()
    add_transform_roots(joints, root_transforms)
    add_transform_roots(meshes, root_transforms)
    add_transform_roots(transforms, root_transforms)
    
    return root_transforms
    
    

def _export_data(export_data, export_folder: pathlib.Path, export_rig: bool, export_fbx: bool):    
    #When export_fbx and export_rig are both false
    #then this function is still useful as it will
    #still returns a list of exportable_content
    qrig_data = QRigData.get_data(export_data.node())
    character_node = get_character_node(export_data)
    root_transforms =  get_exportable_content(export_data)
    
    if export_fbx:
        #Hik should be exported from the stand position only when
        #exporting a rig
        current_source = None
        if export_rig and character_node:
            current_source = hik.get_character_source(character_node)
            hik.set_character_source(character_node, hik.SourceType.STANCE)
        
        user_selection = pm.ls(sl=True)
        pm.select(list(root_transforms), replace=True)
        
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
        
        cg3dguru.animation.fbx.export(fbx_file_path, bake_animations=bake)
        
        pm.select(user_selection, replace=True)
        
        if export_rig and character_node:
            hik.set_character_source(character_node, current_source)

    if export_rig and character_node:
        qrig_file_path = ''
        filename = '{}.{}.qrigcasc'.format(node_name, file_id)
        qrig_file_path = export_folder.joinpath(filename)
        export_qrig_file(character_node, qrig_data, qrig_file_path)
        
        
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
        
    export_node, data = CascExportData.create_node(nodeType='objectSet')
    if exportables:
        export_node.addMembers(exportables)
        
    pm.rename(export_node, 'CACS_EXPORT')
    pm.select(selection, replace=True)
    
    return export_node



def get_textures(objs):
    materials = {}
    
    shapes = pm.listRelatives(objs, s=True)
    shapes += pm.ls(objs, shapes=True)
    for shape in shapes:
        sgs = pm.listConnections(shape, type='shadingEngine' )
        for sg in sgs:
            shaders = pm.listConnections("%s.surfaceShader" % sg, s=True)
            for shader in shaders:
                color_attr = None
                if hasattr(shader, 'color'):
                    color_attr = getattr(shader, 'color')
                elif hasattr(shader, 'diffuse'):
                    color_attr = getattr(shader, 'diffuse')
                elif hasattr(shader, 'baseColor'):
                    color_attr = getattr(shader, 'baseColor')
                    
                if not color_attr:
                    continue
                
                color_input = pm.listConnections(color_attr, s=True, d=False)
                if not color_input:
                    continue
                
                color_input = color_input[0]
                if pm.nodeType(color_input) == 'file':
                    filepath = color_input.fileTextureName.get()
                    if filepath:
                        materials[shape.getParent().name()] = filepath
                        
    return materials



def export(export_set=None, export_rig=False, cmd_string='', textures=True, only_textures=False):
    if cmd_string and not wingcarrier.pigeons.CascadeurPigeon().can_dispatch():
        pm.confirmDialog(message="Please launch Cascadeur, then try again.",button=['Okay'])
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
        scene_sets = pm.ls(sl=True, type='objectSet')
        if not scene_sets:
            scene_sets = pm.ls(type='objectSet')
        
        export_nodes = cg3dguru.udata.Utils.get_nodes_with_data(scene_sets, data_class=CascExportData)
        if not export_nodes:
            #There's nothing to export in the scene, so let's build a default set.
            export_nodes = [_build_default_set()]
             
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
            results = get_textures(branch)
            texture_mappings.update(results)
            
        print(texture_mappings)
        texture_file = open(temp_dir.joinpath('texture_info.json'), 'w')
        formatted_str = json.dumps(texture_mappings, indent=4)
        texture_file.write(formatted_str)
        texture_file.close()

    if cmd_string:
        casc = wingcarrier.pigeons.CascadeurPigeon()
        casc.send_python_command(cmd_string)
        
    return True
        
        

def update_animations():
    export(cmd_string=u"import cg3dmaya; cg3dmaya.update_animations()", textures=False)
    
    
def update_models():
    export(cmd_string=u"import cg3dmaya; cg3dmaya.update_models()")
    
    
def update_textures():
    export(cmd_string=u"import cg3dmaya; cg3dmaya.update_textures()", only_textures=True)    
    
    
def export_scene(new_scene):
    cmd = u"import cg3dmaya; cg3dmaya.import_scene({})".format(new_scene)
    export(cmd_string=cmd)
    

def export_rig(new_scene, export_set):
    cmd = u"import cg3dmaya; cg3dmaya.import_rig({})".format(new_scene)
    export(export_set, True, cmd_string=cmd)
    
    
def smart_export():
    cmd = u"import cg3dmaya; cg3dmaya.smart_import({})".format(False)
    export(cmd_string=cmd)


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
    print('Casc import called')
    files = get_import_files()
    
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
                character_node = get_character_node(matching_id_node.cscDataId)
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
    #get_textures(pm.ls(sl=True))
    #import_fbx()
    
