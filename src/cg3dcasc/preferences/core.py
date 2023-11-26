import pymel.core as pm
import enum
import pathlib
import pickle

_PREFS_INSTANCE = None


class OptionEnum(enum.Enum):
    NEVER = 'Never'
    ALWAYS = 'Always'
    ASK = 'Ask'


class _PreferenceData(object):
    def __init__(self):
        self.bake_animations = OptionEnum.ALWAYS
        

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
            _PREFS_INSTANCE = pickle.load(file)
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

    