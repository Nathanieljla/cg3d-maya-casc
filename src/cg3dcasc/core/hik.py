from enum import Enum

from maya import cmds, mel

from cg3dguru.maya import Node, node_name


_node_index = {}


class SourceType(Enum):
    NONE = 0
    STANCE = 1
    CONTROL_RIG = 2
    
    
def load_hik():
    try:
        mel.eval('if (!`pluginInfo -q -l "mayaHIK"`){ loadPlugin "mayaHIK"; } if (!`pluginInfo -q -l "mayaCharacterization"`) { loadPlugin "mayaCharacterization"; } if (!`pluginInfo -q -l "OneClick"`){ loadPlugin "OneClick"; } hikToggleWidget();')
    except RuntimeError:
        pass
    
    
def _get_hik_windows():
    load_hik()
    hik_options = cmds.lsUI(long=True, type="optionMenuGrp") or []
    character_list = None
    source_list = None
    
    for window in hik_options:
        if 'hikCharacterList' in window:
            character_list = window
        elif 'hikSourceList' in window:
            source_list = window
            
    return (character_list, source_list)


def _get_character_name(character):
    if isinstance(character, str):
        return character
    elif isinstance(character, Node):
        if cmds.nodeType(character.name()) == "HIKCharacterNode":
            return character.name()
        cmds.error("Can't get character name from: {}".format(character))
    elif character is None:
        return 'None'
    else:
        cmds.error("Can't get character name from: {}".format(character))
        

def _set_list(list_control, value, update_method_name):
    menu_items = cmds.optionMenuGrp(list_control, query=True, itemListLong=True) or []
    menu_items_names = {cmds.menuItem(menu_item, query=True, label=True).lower().strip(): menu_item
                        for menu_item in menu_items}
    value = value.lower().strip()
    
    menu_item = None
    if value in menu_items_names:
        menu_item = menu_items_names[value]
        
    else:
        matches = 0
        for name, current_item in menu_items_names.items():
            if name.find(value) != -1:
                matches += 1
                menu_item = current_item
                
        if matches == 0:
            raise KeyError(f"HIK: Couldn't find {value}")
        elif matches > 1:
            raise KeyError(f"HIK: Too many options match {value}")

    value = cmds.menuItem(menu_item, query=True, label=True)

    cmds.optionMenuGrp(list_control, edit=True, value=value)
    mel.eval(update_method_name)
    mel.eval('hikUpdateContextualUI()')
        
        
def get_current_character():
    """Returns the name of the active hik character"""
    character_list, source_list = _get_hik_windows()
    return cmds.optionMenuGrp(character_list, query=True, value=True)


def get_current_source():
    """Returns the name of the active hik source"""
    character_list, source_list = _get_hik_windows()
    source = cmds.optionMenuGrp(source_list, query=True, value=True)
    
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

    current_character = cmds.optionMenuGrp(character_list, query=True, value=True)
    if current_character != character_name:
        _set_list(character_list, character_name, 'hikUpdateCurrentCharacterFromUI()')

        
    return cmds.optionMenuGrp(source_list, query=True, value=True)


def set_character(character):
    """Set the HIK UI to a specific character"""
    character_list, source_list = _get_hik_windows()        
    character_name = _get_character_name(character)

    current_character = cmds.optionMenuGrp(character_list, query=True, value=True)
    if current_character != character_name:
        _set_list(character_list, character_name, 'hikUpdateCurrentCharacterFromUI()')


def set_character_source(character, source: SourceType):
    """Set the HIK UI to a specific character and source"""
    character_list, source_list = _get_hik_windows()        
    character_name = _get_character_name(character)

    current_character = cmds.optionMenuGrp(character_list, query=True, value=True)
    if current_character != character_name:
        _set_list(character_list, character_name, 'hikUpdateCurrentCharacterFromUI()')

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
        cmds.error('invalid source type: {}'.format(source))
        
    if character and source_list:
        current_source = cmds.optionMenuGrp(source_list, query=True, value=True)
        if current_source != source_name:
            _set_list(source_list, source_name, 'hikUpdateCurrentSourceFromUI()')
            
            

def get_node_index_mapping():
    global _node_index
    if not _node_index:
        for idx in range(0, 250): #right now HIK goes to 211
            name = mel.eval(f'GetHIKNodeName {idx}')
            if name:
                _node_index[name] = idx
                
    return _node_index.copy()


    
#The command that runs when the character changes.
#hikUpdateCurrentCharacterFromUI(); hikUpdateContextualUI();

#the command that runs when the source changes
#hikUpdateCurrentSourceFromUI(); hikUpdateContextualUI();
