import pymel.core as pm
from enum import Enum


class SourceType(Enum):
    NONE = 0
    STANCE = 1
    CONTROL_RIG = 2
    
    
def _get_hik_windows():
    hik_options = pm.lsUI(l=True, type="optionMenuGrp")
    character_list = None
    source_list = None
    
    for window in hik_options:
        if 'hikCharacterList' in window.name():
            character_list = window
        elif 'hikSourceList' in window.name():
            source_list = window
            
    return (character_list, source_list)


def _get_character_name(character):
    if isinstance(character, str):
        return character
    elif isinstance(character, pm.nodetypes.HIKCharacterNode):
        return character.name()
    elif character is None:
        return 'None'
    else:
        pm.error("Can't get character name from: {}".format(character))
        
        
def get_current_character():
    """Returns the name of the active hik character"""
    character_list, source_list = _get_hik_windows()
    return pm.optionMenuGrp(character_list, query=True, value=True)


def get_current_source():
    """Returns the name of the active hik source"""
    character_list, source_list = _get_hik_windows()
    source = pm.optionMenuGrp(source_list, query=True, value=True)
    
    if source == ' None':
        return SourceType.NONE
    elif source == ' Stance':
        return SourceType.STANCE
    elif source == ' Control Rig':
        return SourceType.CONTROL_RIG
    else:
        return source

    
def get_character_source(character):
    """Returns the source for a specific character"""
    character_list, source_list = _get_hik_windows()        
    character_name = _get_character_name(character)    

    current_character = pm.optionMenuGrp(character_list, query=True, value=True)
    if current_character != character_name:
        pm.optionMenuGrp(character_list, edit=True, value=character_name)
        pm.mel.eval('hikUpdateCurrentCharacterFromUI()')
        pm.mel.eval('hikUpdateContextualUI()')
        
    return pm.optionMenuGrp(source_list, query=True, value=True)


def set_character(character):
    """Set the HIK UI to a specific character"""
    character_list, source_list = _get_hik_windows()        
    character_name = _get_character_name(character)

    current_character = pm.optionMenuGrp(character_list, query=True, value=True)
    if current_character != character_name:
        pm.optionMenuGrp(character_list, edit=True, value=character_name)
        pm.mel.eval('hikUpdateCurrentCharacterFromUI()')
        pm.mel.eval('hikUpdateContextualUI()')    
    

def set_character_source(character, source: SourceType):
    """Set the HIK UI to a specific character and source"""
    character_list, source_list = _get_hik_windows()        
    character_name = _get_character_name(character)

    current_character = pm.optionMenuGrp(character_list, query=True, value=True)
    if current_character != character_name:
        pm.optionMenuGrp(character_list, edit=True, value=character_name)
        pm.mel.eval('hikUpdateCurrentCharacterFromUI()')
        pm.mel.eval('hikUpdateContextualUI()')
           
    #I can't believe there's a prefix of ' ', but here we are  
    source_name = ''
    if source == SourceType.NONE:
        source_name = ' None'
    elif source == SourceType.STANCE:
        source_name = ' Stance'
    elif source == SourceType.CONTROL_RIG:
        source_name = ' Control Rig'
    elif isinstance(source, str):
        source_name = _get_character_name(source)
        if not source_name.startswith(' '):
            source_name = ' {}'.format(source_name)
    else:
        pm.error('invalid source type: {}'.format(source))
        
    if character and source_list:
        current_source = pm.optionMenuGrp(source_list, query=True, value=True)
        if current_source != source_name:
            pm.optionMenuGrp(source_list, edit=True, value=source_name)
            pm.mel.eval('hikUpdateCurrentSourceFromUI()')
            pm.mel.eval('hikUpdateContextualUI()')
        
    
    
#The command that runs when the character changes.
#hikUpdateCurrentCharacterFromUI(); hikUpdateContextualUI();

#the command that runs when the source changes
#hikUpdateCurrentSourceFromUI(); hikUpdateContextualUI();