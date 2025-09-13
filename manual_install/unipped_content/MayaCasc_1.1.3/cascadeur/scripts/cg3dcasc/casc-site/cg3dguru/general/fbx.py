from enum import IntEnum
from enum import auto
import csc
from . import core


class FbxFilterType(IntEnum):
    SKIP = 0
    AUTO = 1
    SCENE = 2
    MODEL = 3
    ANIMATION = 4
    SELECTED = 5
    FRAMES = 6



def current_fbx_loader() -> csc.fbx.FbxLoader:
    """Returns the FbxLoader for the current scene
    
    Use the returning object to export and import data. See
    https://cascadeur.com/python-api/_generate/csc.fbx.FbxLoader.html for
    more info.
    """
    
    current_scene = core.get_current_scene()
    tools_manager = csc.app.get_application().get_tools_manager()
    fbx_scene_loader = tools_manager.get_tool("FbxSceneLoader").get_fbx_loader(current_scene.unwrap())
    
    return fbx_scene_loader

    
    
def import_fbx(file_path: str, import_filter: FbxFilterType, new_scene: bool=False):
    """Import the fbx file into Cascadeur.
    
    FbxFilterType.SELECTED will import animation to the selected objects.
    FbxFilterType.FRAMES will import animation to the active frames.    
    """
    
    if new_scene:
        core.new_scene()    
    
    loader = current_fbx_loader()
    method = None
    
    if import_filter == FbxFilterType.SCENE:
        method = loader.import_scene    
    elif import_filter == FbxFilterType.MODEL:
        method = loader.import_model
    elif import_filter == FbxFilterType.ANIMATION:
        method = loader.import_animation
    elif import_filter == FbxFilterType.SELECTED:
        method = loader.import_animation_to_selected_objects
    elif import_filter == FbxFilterType.FRAMES:
        method = loader.import_animation_to_selected_frames
    else:
        raise ValueError("Invalid import_filter value: {}".format(import_filter))
        
    method(file_path)
    
    
    
def export_fbx(file_path: str, export_filter: FbxFilterType):
    """Export an fbx file to the target file location
    
     FbxFilterType.SELECTED will export a scene with only the selected objects.
    """
    
    loader = current_fbx_loader()
    method = None

    if export_filter == FbxFilterType.SCENE:
        method = loader.export_all_objects
    elif export_filter == FbxFilterType.MODEL:
        method = loader.export_model
    elif export_filter == FbxFilterType.SELECTED:
        if hasattr(loader, 'export_scene_selected_objects'):
            method = loader.export_scene_selected_objects
        else:
            method = loader.export_scene_selected
    elif export_filter == FbxFilterType.ANIMATION:
        method = loader.export_joints
    else:
        raise ValueError("Invalid export_filter value: {}".format(export_filter))
        
    method(file_path)




