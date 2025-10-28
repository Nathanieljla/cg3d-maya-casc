
import json

class SpineException(Exception):
    """Thrown when an export is attempted without an upper spine bone defined"""
    pass

#https://forums.autodesk.com/t5/maya-programming/python-hik/td-p/4262564
#https://mayastation.typepad.com/maya-station/2011/04/maya-2012-hik-menus-and-mel-commands-part-1.html
#https://github.com/bungnoid/glTools/blob/master/utils/hik.py

HIK_ATTRS = {
    'Reference': None,
    'Hips': 'pelvis',
    'HipsTranslation': None,
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
    'LeftHandMiddle1': 'middle_finger_l_1',
    'LeftHandMiddle2': 'middle_finger_l_2',
    'LeftHandMiddle3': 'middle_finger_l_3',
    'LeftHandMiddle4': None,
    'LeftHandRing1': 'ring_finger_l_1',
    'LeftHandRing2': 'ring_finger_l_2',
    'LeftHandRing3': 'ring_finger_l_3',
    'LeftHandRing4': None,
    'LeftHandPinky1': 'pinky_l_1', #pinky_finger_l_1 (finger isn't in the name 2023.2)
    'LeftHandPinky2': 'pinky_l_2',
    'LeftHandPinky3': 'pinky_l_3',
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
    'LeftUpLegRoll': None, #this isn't in the HIK UI
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
    'RightHandMiddle1': 'middle_finger_r_1',
    'RightHandMiddle2': 'middle_finger_r_2',
    'RightHandMiddle3': 'middle_finger_r_3',
    'RightHandMiddle4': None,
    'RightHandRing1': 'ring_finger_r_1',
    'RightHandRing2': 'ring_finger_r_2',
    'RightHandRing3': 'ring_finger_r_3',
    'RightHandRing4': None,
    'RightHandPinky1': 'pinky_r_1', #pinky_finger_r_1 (the finger isn't part of the pink name?)
    'RightHandPinky2': 'pinky_r_2',
    'RightHandPinky3': 'pinky_r_3',
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
    'RightUpLegRoll': None, #this isn't in the HIK UI
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



def has_twist(character_node, twist_names=None):
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