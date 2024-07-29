import pymel.core as pm
import enum
import pathlib
import pickle

_PREFS_INSTANCE = None


class OptionEnum(enum.Enum):
    NEVER = 'Never'
    ALWAYS = 'Always'
    ASK = 'Ask'


class TextureConversionType(enum.Enum):
    NEVER = 'Never'
    CURRENT_PATH = 'Current'
    """Puts the texture next to the original file"""
    
    PROJECT_RELATIVE = 'Project'
    """Use the project's custom cascadeur_textures rule"""
    
    CUSTOM = 'Custom'
    """Texture location is stored on each export node"""


class _PreferenceData(object):
    version = (0, 1, 0)
    
    def __init__(self, old_prefs = None):
        self.bake_animations = OptionEnum.ALWAYS
        self.texture_conversion = TextureConversionType.NEVER
        
        if old_prefs is not None:
            _PreferenceData.clone(self, old_prefs)
                  
    @staticmethod
    def clone(new, old):
        new.bake_animations = getattr(old, 'bake_animations') if hasattr(old, 'bake_animations') else new.bake_animations
        new.texture_conversion = getattr(old, 'texture_conversion') if hasattr(old, 'texture_conversion') else new.texture_conversion
        
        

def _get_save_path():
    saved_data = pathlib.Path(__file__)
    saved_data = saved_data.parent
    saved_data = saved_data.joinpath('prefs.pickle')
    
    return saved_data


def new():
    return _PreferenceData()
        
        
def get():
    global _PREFS_INSTANCE
    
    if _PREFS_INSTANCE is not None:
        return _PREFS_INSTANCE

    saved_data = _get_save_path()
    if saved_data.exists():
        try:       
            file = open(saved_data, 'rb')
            _PREFS_INSTANCE = _PreferenceData(pickle.load(file))
            file.close()
        except:
            pm.warning("Cascadeur: Preferences are reset due to corrupt data!")
            set(_PreferenceData())
    else:
        set(_PreferenceData())
        
    return _PREFS_INSTANCE
        

def set(data: _PreferenceData):
    global _PREFS_INSTANCE
    _PREFS_INSTANCE = data
    saved_data = _get_save_path()
    
    file = open(saved_data, "wb")
    pickle.dump(data, file)
    file.close()

    