from __future__ import annotations #used so type hints are resolved after all content is read
import typing

import csc

import cg3dguru.datatypes

def new_scene() -> cg3dguru.datatypes.PyScene:
    """Creates a new scene and makes it the active scene
    
    Returns:
        csc.View.Scene
    """
    scene_manager = csc.app.get_application().get_scene_manager()    
    application_scene = scene_manager.create_application_scene()
    scene_manager.set_current_scene(application_scene)
    
    return cg3dguru.datatypes.PyScene.wrap(application_scene, None)



def get_current_scene() -> cg3dguru.datatypes.PyScene:
    """Get the current scene"""
    scene_manager = csc.app.get_application().get_scene_manager()
    scene = scene_manager.current_scene()
    
    return cg3dguru.datatypes.PyScene.wrap(scene, None)



def get_scene_objects(names = [], selected = False, of_type = '', only_roots = False) -> typing.List[cg3dguru.datatypes.PyObject]:
    current_scene = get_current_scene()
    return current_scene.get_scene_objects(names, selected, of_type, only_roots)
    