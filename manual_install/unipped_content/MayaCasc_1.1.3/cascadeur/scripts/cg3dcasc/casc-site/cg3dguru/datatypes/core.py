from __future__ import annotations #used so I don't have to forward declare classes for type hints

# https://sphinxcontrib-napoleon.readthedocs.io/en/latest/example_google.html

from enum import Enum, Flag, auto
import typing

import csc

_GIT_COUNT = int(csc.SystemVariables.git_count())


################
###---Exceptions
################

class EditorError(Exception):
    """Thrown when someone attempts to access and editor at an invalid time
    
    The SceneElement properties 'mod_editor, 'beh_editor', 'dat_editor',
    'update_editor', scene_updater, and 'session' should only be accessed
    after SceneElement.edit has been called and inside of the assigned
    callback. Outside of this condition an error is raised.    
    """
    def __init__(self, editor_name, message=''):
        if not message:
            message = "{} can't be accessed outside of call to PyScene.edit".format(editor_name)
            
        super().__init__(message)
        
    

class BehaviourError(Exception):
    """Thrown when a PyObject doesn't have a behaviour of a given name
    
    If code uses the shorthand of object.behaviour_name and the behaviour
    doesn't exist, this error will be thrown.
    """
    
    def __init__(self, behaviour_name, message=''):
        if not message:
            message = "Can't find behaviour {}".format(behaviour_name)
            
        super().__init__(message)
        
        
        
class BehaviourSizeError(Exception):
    """Thrown when only one behaviour of a given type should exist
    
    If code uses the shorthand of object.behaviour_name and more than one
    behaviour of the given name exists, this error will be thrown.
    
    In these cases code should be refactored to call
    object.get_behaviours_by_name(behaviour_name) instead.
    """
    
    def __init__(self, object_name, behaviour_name, message=''):
        if not message:
            message = "{0}.{1} ERRORs, because more than one behaviour exists. Try {0}.get_behaviours_by_name('{1}')[0] instead.".format(object_name, behaviour_name)
            
        super().__init__(message)
        
        
        
#class PropertyTypeError(Exception):
    #"""Thrown when the csc api is out of sync with this wrapper"""
  
    #def __init__(self, behaviour_name, property_name, property_type, message=''):
        #if not message:
            #message = f"cant get property type for {behaviour_name}.{property_name} found as {property_type}"
            
        #super().__init__(message)    
    #prop = None
    
    
class MissingGroupError(Exception):
                #raise PropertyTypeError(self._name, name, property_type)
    def __init__(self, group_name, message=''):
        if not message:
            message = f"Can't create Update Group: {group_name}"
            
        super().__init__(message)    
        
        
        
class PropertyError(Exception):
    """Thrown when a PyBehaviour doesn't have a property of a given name
    
    If PyBehaviour.attribute_name doesn't exist, this will be thrown.
    """
    
    def __init__(self, behaviour_name, attr_name, message=''):
        if not message:
            message = "Can't find attribute named:{} in behaviour {}".format(attr_name, behaviour_name)
            
        super().__init__(message)


ERROR_ON_UNKNOWN_PROPS = False

#################
####---Enums---
#################
class PropertyType(Flag):
    UNKNOWN = auto()
    RANGE = auto()
    DATA = auto()
    DATA_RANGE = DATA | RANGE
    SETTING = auto()
    SETTING_RANGE = SETTING | RANGE
    REFERENCE = auto()
    REFERENCE_RANGE = REFERENCE | RANGE
    OBJECT = auto()
    OBJECT_RANGE = OBJECT | RANGE
    BEH_STRING = auto()



#################
####---Classes---
#################
class CscWrapper(object):
    _class_wrappers = None
    
    def __init__(self, data, creator, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        if isinstance(data, CscWrapper):
            data = data.unwrap()
        
        self.__data = data
        self.__creator = creator

         
    def __repr__(self):
        return f"Wrapped {self.__data.__class__}" #.format(self.__class__.__name__, self.__data.__class__.__name__)
    

    def __str__(self):
        return f"{self.__class__.__name__} wraps {self.__data.__class__.__name__} class {self.__data.__class__}"

    
    def __eq__(self, other):
        if isinstance(other, CscWrapper):
            return ((self.__data == other.__data))
        else:
            return False
        
        
    def __hash__(self):
        return self.__data.__hash__()
    
    
    def __call__(self, *args, **kwargs):
        return self.__data(*args, **kwargs)
    
    
    def __getattr__(self, attr):
        if hasattr(self.__data, attr):            
            def func_wrapper(*args, **kwargs):
                args = self.unwrap_list(args)
                CscWrapper.unwrap_dict(kwargs)
                
                func = getattr(self.__data, attr)
                result = func(*args, **kwargs)

                return self._wrap_result(result)
                
            if not callable(getattr(self.__data.__class__, attr)):
                #This must be a property, so let's return the wrapped results
                return self._wrap_result(getattr(self.__data, attr))
            else:
                return func_wrapper
        
        raise AttributeError(attr)
    
                
    @staticmethod
    def unwrap_list(in_list):
        """Replace all CscWrappers elements with their underlying data"""
        is_tuple = isinstance(in_list, tuple)
        is_set = isinstance(in_list, set)
        #if is_tuple or is_set:
            #in_list = list(in_list)
        
        results = []
        for value in in_list:
            if isinstance(value, CscWrapper):
                results.append(value.unwrap())
            elif isinstance(value, tuple) or isinstance(value, list) or isinstance(value, set):
                results.append(CscWrapper.unwrap_list(value))
            else:
                results.append(value)
                
        if is_tuple:
            results = tuple(results)
        elif is_set:
            results = set(results)
                
        return results

    
    @staticmethod
    def unwrap_dict(in_dict):
        """Replace all CscWrappers elements with their underlying data"""
        for key, value in in_dict.items():
            if isinstance(value, CscWrapper):
                in_dict[key] = value.unwrap()
            elif isinstance(value, tuple) or isinstance(value, list) or isinstance(value, set):
                in_dict[key] = CscWrapper.unwrap_list(value)

           
    @staticmethod
    def get_class_wrappers():
        if CscWrapper._class_wrappers is None:
            CscWrapper._class_wrappers = {
                csc.model.ObjectId: PyObject,
                csc.Guid: PyGuid, 
                csc.view.Scene: PyScene,
                csc.domain.Scene: DomainScene,
                csc.domain.Selector: SceneElement,
                csc.domain.SelectionChanger: SceneElement,
                csc.domain.Selection: SceneElement,
                csc.model.BehaviourViewer: BehaviourViewer,
                csc.model.ModelViewer: ModelViewer,
                csc.model.DataViewer: DataViewer,
                csc.layers.Viewer: LayersViewer,
                csc.update.ObjectGroup: SceneElement,
                csc.update.Object: PyUpdateObject,
            }
            
            if _GIT_COUNT >= 33075:
                CscWrapper._class_wrappers[csc.model.BehaviourId] = PyBehaviour
                CscWrapper._class_wrappers[csc.domain.AssetId] = PyGuid
            
            
        return CscWrapper._class_wrappers
    
        
    @staticmethod
    def wrap(data: object, creator: object) -> typing.Type[CscWrapper] | typing.Any | None: #, default_class = None) -> CscWrapper:
        """Takes the data and returns an instance of CscWrapper
                
        Args:
            data: The data to wrap
            creator: The owner of the data. Use None if there is no creator.
        """
        if hasattr(data, 'is_null') and data.is_null():
            return None
        
        class_wrappers = CscWrapper.get_class_wrappers()
                    
        wrapper = None
        if data.__class__ in class_wrappers:
            wrapper = class_wrappers[data.__class__]
            #print('found mapping')
            
        if wrapper and wrapper == PyGuid:
            if isinstance(creator, GuidMapper) and creator.guid_class is not None:
                wrapper = creator.guid_class
             
        #I want this code, but right now it's breaking stuff.
        #Specifically it doesn't play nice with DataId at a minimum
        ###If we haven't found anything by now and this is csc class
        ###we'll want a generic wrapper around it, so the getters and setters work
        ###don't use __class__.__name__ here, because it might not contain the csc.
        if not wrapper and str(data.__class__).startswith("<class 'csc."):
            if isinstance(creator, SceneElement):
                wrapper = SceneElement
            else:
                wrapper = CscWrapper
            
        #this must be a data that's not csc specific.
        if wrapper is None:
            return data

        #let's return the wrapped data
        return wrapper(data, creator)        

        
        
    @property
    def creator(self):
        """What object is responsible for this object's data"""
        return self.__creator
    

    def replace_data(self, data):
        """Directly replace the underlying content that is wrapped"""
        while isinstance(data, CscWrapper):
            data = data.unwrap()        
        
        self.__data = data
   
              
    def unwrap(self):
        """Return the underlying data that's wrapped"""
        
        return self.__data
        
        ###This shouldn't be a another wrapper, but wrapped model.DataId
        ###is coming out this way and I haven' tracke down why.  Probably
        ###due to how I'm handling all behaviour properties.
        #output = self.__data
        #while isinstance(output, CscWrapper):
            #output = output.unwrap()
        
        #return output
    
    
    @property
    def handle(self):
        """Direct access to the unwrapped csc data. An Alias for self.unwrap()"""
        return self.unwrap()    
                       
               
    def _wrap(self, csc_handle):
        return self.wrap(csc_handle, self)
    
    
    def _wrap_result(self, result: object):
        if result is None:
            return None
        
        if isinstance(result, list) or isinstance(result, tuple):
            return [CscWrapper.wrap(value, self) for value in result if value is not None]
        elif isinstance(result, set):
            result_list = list(result)
            return set([CscWrapper.wrap(value, self) for value in result_list if value is not None])
        else:
            return CscWrapper.wrap(result, self)



class SceneElement(CscWrapper):
    """Base class used to represent any wrapped data existing/related to a scene
    
    Used to share global scene access between scene data-specific classes.
    The csc viewers and editors need to be instanced in context to the
    current scene. Scene objects needing these viewers and editors is commmon
    among any datatypes.classes that represent scene data.
    """
    
    def __init__(self, *args, **kwargs):
        super(SceneElement, self).__init__(*args, **kwargs)
        
        self._scene: PyScene = None
        
        if self.creator is not None:
            if isinstance(self.creator, SceneElement):
                self._scene = self.creator.scene
            else:
                raise TypeError("{} is not an instance of SceneElement".format(self.creator.__class__.__name__))
            
            
    @property
    def scene(self):
        """Returns the view.Scene"""
        return self._scene
    
    
    @property
    def dom_scene(self):
        """Returns the domain.Scene"""
        #this property name is abbreviated to avoid conflicts with the csc
        #api function name domain_scene.        
        return self._scene.ds
    
    @property
    def mod_viewer(self):
        """Returns the ModelViewer"""
        #this property name is abbreviated to avoid conflicts with the csc
        #api function name model_viewer.
        
        return self._scene.mv
    
    @property
    def beh_viewer(self):
        """Returns the BehaviourViewer"""
        #this property name is abbreviated to avoid conflicts with the csc
        #api function name behaviour_viewer.        
        return self._scene.bv
    
    @property
    def dat_viewer(self):
        """Returns the DataViewer"""
        #this property name is abbreviated to avoid conflicts with the csc
        #api function name data_viewer.
        return self._scene.dv
    
    @property
    def lay_viewer(self):
        """Returns the LayersViewer"""
        return self._scene.lv
    
    @property
    def mod_editor(self):
        """Returns the active model editor
        
        This will only be valid during the call to self.scene.edit()
        """
        if not self._scene.editing:
            raise EditorError('Model Editor')
        return self._scene.me
    
    @property
    def beh_editor(self):
        """Returns the active behaviour editor
        
        This will only be valid during the call to self.scene.edit()
        """
        if not self._scene.editing:
            raise EditorError('Behaviour Editor') 
        return self._scene.be
    
    @property
    def dat_editor(self):
        """Returns the active data editor
        
        This will only be valid during the call to self.scene.edit()
        """
        if not self._scene.editing:
            raise EditorError('Data Editor')
        return self._scene.de
    
    @property
    def update_editor(self):
        """Returns the active update editor
        
        This will only be valid during the call to self.scene.edit()
        """
        if not self._scene.editing:
            raise EditorError('Update Editor')        
        return self._scene.ue
    
    @property
    def scene_updater(self):
        """Returns the active scene editor
        
        This will only be valid during the call to self.scene.edit()
        """
        if not self._scene.editing:
            raise EditorError('Scene Editor')        
        return self._scene.su
    
    @property
    def session(self):
        """Return the session associated with the current scene
        
        This will only be valid during the call to self.scene.edit()
        """
        if not self._scene.editing:
            raise EditorError('Session')        
        return self._scene.sess


    
class PyScene(SceneElement):
    """Represents a csc.view.Scene and all the scene's viewers and editors"""
    
    def __init__(self, *args, **kwargs):
        super(PyScene, self).__init__(*args, **kwargs)
        self._scene = self
        self.ds = self.domain_scene()
        
        self.mv = self.ds.model_viewer()
        self.bv = self.ds.behaviour_viewer()
        self.dv = self.ds.data_viewer()
        self.lv = self.ds.layers_viewer()
        
        self._editing = False
        self._update_accessed = False
        self.me = None
        self.be = None
        self.de = None
        self.le = None
        
        self.ue = None
        self.su = None        
        self.sess = None
        
        
    @property
    def editing(self):
        return self._editing
        
    def _start_editing(self, model_editor,
                       update_editor: csc.update.Update,
                       scene_updater: csc.domain.SceneUpdater,
                       session: csc.domain.Session
                       ):
        self._editing = True
        self._update_accessed = False
        
        self.me = SceneElement(model_editor, self) #model editor
        self.ue = UpdateEditor(update_editor, self) #update editor
        self.su = SceneElement(scene_updater, self) #scene updater
        self.sess = SceneElement(session, self) #session

        self.be = BehaviourEditor(model_editor.behaviour_editor(), self) #behaviour editor
        self.de = SceneElement(model_editor.data_editor(), self) #data editor
        self.le = LayersEditor(model_editor.layers_editor(), self) #layers editor
        
        
    @SceneElement.update_editor.getter
    def update_editor(self):
        self._update_accessed = True
        return super().update_editor
        

    def _stop_editing(self):
        self._editing = False
        self._update_accessed = False
        self.me = self.be = self.de = self.le = None
        self.ue = self.su = self.sess = None
          
        
    def edit(self, title: str, callback: typing.Callable, *callback_args, _internal_edit=False, **callback_kwargs):
        """Used to allow proper editing of scene content.
        
        Provides access to the domain_scene.editors and updaters. If an edit
        isn't in process then a modify operation is started. Any arguments
        that you need to pass into your func can be included when calling
        edit(). For Example:
        
        edit('making some changes', myFunc, param1, param2=True)
        Args:
            title: The title of the modify operation
            callback: the function/method to run after the editors are
            initialized
        """
        def _scene_edit(model_editor, update_editor, scene_updater, session):
            self._start_editing(model_editor, update_editor, scene_updater, session)        
            callback(*callback_args, **callback_kwargs)          
            scene_updater.generate_update()
            self._stop_editing()
            
            
        if not _internal_edit:
            #external callbacks should have a handle to the PyScene so the editors can be accessed
            callback_args = list(callback_args)
            callback_args.insert(0, self)
    
        if self._editing:
            callback(*callback_args, **callback_kwargs)
        else:
            if _internal_edit:
                self.dom_scene.warning("Scene edits should be made through PyScene.edit")
             
            #try:
            self.ds.modify_update_with_session(title, _scene_edit)
            #except Exception as e:
                #print(e)
            
        
    def select(self, to_select, *args, **kwargs):
        if isinstance(to_select, list):
            to_select = set(to_select)
        
        def _select():
            self.session.take_selector().select(to_select, *args, **kwargs)
        
        self.edit('Select Object(s)', _select, _internal_edit=True)

            
    def create_object(self, name: str='') -> PyObject:
        """Creates a new scene object"""
        new_object = None
        
        def _create_object():
            nonlocal new_object
            new_object = self.update_editor.create_object_node(name)

            
        self.edit('Create Object', _create_object, _internal_edit=True)
        return new_object.object_id()
    
    
    def get_current_frame(self, clamp_to_animation =True):
        return self.ds.get_current_frame(clamp_animation=clamp_to_animation)
    
    
    def set_current_frame(self, frame):
        def _set_current_frame():
            self.ds.set_current_frame(frame)
            
        self.edit('Set Current Frame', _set_current_frame, _internal_edit=True)
        
      
    def get_animation_size(self):
        return self.dv.get_animation_size()
    
    
    def select_frame_range(self, start_end: tuple[int, int]|None = None, clamp_to_animation=True):
        """Select a time interval.  All layers will be selected.
        
        Args:
            start_end: When no tuple is supplied the entire animation range
            is selected
            clamp_to_animation:When True the interval end won't extend past
            the animation
        """
        
        a_len = self.dv.get_animation_size() - 1
        if start_end is None:
            start_end = (0, a_len)
            
        if clamp_to_animation:
            if start_end[0] > a_len:
                start_end = (a_len, start_end[1])
            if  start_end[1] > a_len:
                start_end = (start_end[0], a_len)
        
        #this will crash Cascadeur        
        if start_end[1] < start_end[0]:
            start_end = (start_end[0], start_end[0])
            
        def _select_frame_range():     
            layer_selector = self.session.take_layers_selector()
        
            l_s_with_ids = self.me.layers_selector()
            selected_layer_ids = l_s_with_ids.all_included_layer_ids()
            layer_selector.set_full_selection_by_parts(selected_layer_ids, *start_end)
            
        self.edit('Select frame range', _select_frame_range, _internal_edit=True)
        

    
    def get_scene_objects(self, names = [], selected = False, of_type = '', only_roots = False) -> typing.List[PyObject]:
        """return a list of scene objects based on the input filters
        
        Args:
            names: what are the specific names you're looking for
            select: only consider selected object
            of_type: only consider objects of type (type listed in the outliner)
            only_roots: only consider objects with no parents
        """
        
        def _get_by_name():
            found_guids = []
            for name in names:
                result = self.mod_viewer.get_objects(name)
                if result:
                    found_guids.append(result[0])
                        
            return found_guids
        
        name_list = []
        if selected:
            found_objects = self.dom_scene.selector().selected().ids
            if names:
                name_list = _get_by_name()
        elif names:
            found_objects = _get_by_name()
        else:
            found_objects = self.mod_viewer.get_objects()
    
        
        if name_list:
            set_a = set(name_list)
            set_b = set(found_objects)
            
            set_b.intersection_update(set_a)
            found_objects = list(set_b)
            
            
        if of_type:
            found_objects = [obj for obj in found_objects if self.mod_viewer.get_object_type_name(obj) == of_type]
            
        if only_roots:
            found_objects = [obj for obj in found_objects if obj.parent is None]
            
        return found_objects
    
         
                  
class PyGuid(SceneElement):
    """Base class for wrappping csc.Guid and all Ids"""

    def __init__(self, *args, **kwargs):
        super(PyGuid, self).__init__(*args, **kwargs)
        
        
        
class PyUpdateObject(SceneElement):
    """Represents an object within the node graph"""
    pass
    #def object_id(self):
        #return self.unwrap().object_id()
        


#class PyDataId(PyGuid):
    #pass


#class PySettingId(PyGuid):
    #pass


class PyObject(PyGuid):
    """Wrapper around ccs.model.ObjectId"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self._behaviours_cache = {}
        
        
    def __str__(self):
        guid = ''
        if self.unwrap():
            guid = self.unwrap().to_string()
        
        return "{}->{}->{}".format(self.__class__.__name__, self.name, guid)
        

    def __getattr__(self, attr):
        return getattr(self.unwrap(), attr)

    
    @property
    def name(self):
        """The name of the object"""
        return self.mod_viewer.get_object_name(self)
    
    
    @name.setter
    def name(self, value):
        """Set the name of the object"""
        def _set():
            self.mod_editor.set_object_name(self, value)
        
        title = "Set name".format(value)
        self.scene.edit(title, _set, _internal_edit=True)
        
        
    @property
    def children(self):
        """Returns a list of children parented to the current model"""
        #return self.beh_viewer.get_children(self)
        pass
    
    
    @property
    def parent(self):
        """Get's the 'Basic' behaviour parent property value"""
        return self.Basic.parent.get()
    
    
    @parent.setter
    def parent(self, value):
        self.Basic.parent.set(value)
        
        
    def get_dynamic_behaviours(self):
        self._cache_behaviours()
        dynamic_behs = []
        for key, beh_list in self._behaviours_cache.items():
            for beh in beh_list:
                if beh.is_dynamic:
                    dynamic_behs.append(beh)
            
        return dynamic_behs


    def get_behaviours_by_name(self, behaviour_name) -> list:
        """Returns a list of all the behaviours that match the given name"""
        
        if self.has_behaviour(behaviour_name):
            return self._behaviours_cache[behaviour_name]
        
        return []
    
    
    def get_behaviour_by_name(self, name) -> PyBehaviour | None:
        """Returns the PyBehaviour that matches the given input name
        
        raises:
            BehaviourSizeError: If more than one behaviour of the given name
            exists.
        """
        behaviours = self.get_behaviours_by_name(name)
        if not behaviours:
            return None
        
        elif len(behaviours) > 1:
            raise BehaviourSizeError(self.name, name)
        
        return behaviours[0] 
      
        
    def __getattr__(self, attr):
        result = self.get_behaviour_by_name(attr)
        if result:
            return result
        else:
            raise BehaviourError(attr)
    
    
    def _cache_behaviours(self):
        self.flush_cache()
        
        behaviours = self.get_behaviours() #beh_viewer.get_behaviours(self)
        #try:
            
        for behaviour in behaviours:
            if behaviour.name in self._behaviours_cache:
                self._behaviours_cache[behaviour.name].append(behaviour)
            else:
                self._behaviours_cache[behaviour.name] = [behaviour]
                
        #except Exception as e:
            #print(e)
            
            
    def flush_cache(self):
        """PyBehaviours are cached. This invalidates the cache
        
        This should be called anytime a behaviour has been deleted, so that
        the object data doesn't hold an invalid reference. 
        """
        
        #ToDo: Really, I should probably not do the caching thing in general.
        #as I'm not sure it's really a performance hit and risks having wrappers
        #become out of sync with the underlying data.
        self._behaviours_cache = {}

            
    def has_behaviour(self, behaviour_name) -> bool:
        """Returns True if a behaviour of the given name exists else False"""
        
        #If a requested behaviour is missing the internal behaviour cache is
        #rebuild to make sure the data is up to date.
        if behaviour_name not in self._behaviours_cache:
            self._cache_behaviours()
            
        return behaviour_name in self._behaviours_cache
 
 
    def add_behaviour(self, name: str, dynamic_name=None):
        add_dynamic = name.startswith('Dynamic')
        output = None
        def _add_behaviour():
            nonlocal output
            output = self.beh_editor.add_behaviour(self, name)
            if add_dynamic:
                name_prop = output.get_property('behaviourName')
                if isinstance(name_prop, DataProperty):
                    name_prop.create_data('behaviour_name', csc.model.DataMode.Static, dynamic_name, group_name='{} update'.format(dynamic_name))
                elif isinstance(name_prop, StringProperty):
                    name_prop.set(dynamic_name)
                else:
                    raise(Exception("Can't determine behaviourName type for {}".format(self._name)))
                    
            
        if add_dynamic and dynamic_name is None:
            raise KeyError("add_behaviour optional arg 'dynamic_name' is missing.")
            
        self.scene.edit(f"Add Behaviour {name}", _add_behaviour, _internal_edit=True)
        return output
    
#---wrapped behaviour viewer functions----    

    def get_behaviours(self) -> typing.List[PyBehaviour]:
        """Returns a flat list of all the behaviours attached to the object"""
        return self.beh_viewer.get_behaviours(self)
    
        
#---wrapped data editor functions
    def create_data(self, data_name: str, mode: csc.model.DataMode, value, data_id=None, group_name: str=None) -> csc.model.Data:
        """Wrapper DataEditor.add_data
        
        Args:
            data_name:user readable name of the data
            mode:Details of how the data will be stored
            value:The default value of the data.
            data_id (optional): an existing data_id to associate the data
            with. For testing/internal use.
            group_name (optional): If a group_name is defined, then the data
            will be added to a UpdateGroup of the given name. If the name
            doesn't exist, then one will be made.
            
        Returns:
            csc.model.Data            
        """
        result = None
        def _object_add_data():
            nonlocal result
            if not group_name:
                if data_id:
                    result = self.dat_editor.add_data(self, data_name, mode, value, data_id)
                else:
                    result = self.dat_editor.add_data(self, data_name, mode, value)
                
            if group_name:
                update_node = self.update_editor.get_node_by_id(self)
                root_group = update_node.root_group()
                target_group = None
                if not root_group.has_node(group_name):
                    target_group = root_group.create_sub_update_group(group_name)
                    self.scene_updater.generate_update()
                else:
                    for node in root_group.nodes():
                        if isinstance(node.handle, csc.update.UpdateGroup) and node.name() == group_name:
                            target_group = node
                            break
                        
                if target_group:
                    update_data = target_group.create_regular_data(data_name, value, mode)
                    result = self.dat_viewer.get_data(update_data.data_id())
                else:
                    raise MissingGroupError(group_name)
             
                        
        self.scene.edit("Add data to {}".format(self.name), _object_add_data, _internal_edit=True)
        return result
    
    
    def create_setting(self, setting_name: str, mode: csc.model.SettingMode, value, setting_id=None) -> csc.model.Setting:
        result = None
        def _object_add_setting():
            nonlocal result
            if setting_id:
                result = self.dat_editor.add_setting(self, setting_name, mode, value, setting_id)
            else:
                result = self.dat_editor.add_setting(self, setting_name, mode, value)
                
        self.scene.edit("Add setting to {}".format(self.name), _object_add_setting, _internal_edit=True)
        return result
        



class PyBehaviour(PyGuid):
    """A wrapper for Cascadeur Behaviours"""
    
    def __init__(self, *args, **kwargs):
        super(PyBehaviour, self).__init__(*args, **kwargs)
        self._init = False
        self._name = self.get_name()
        self.is_dynamic = self._name.startswith('Dynamic')
        self._property_types = {name:self._get_property_type(name) for name in self.get_property_names()}
        self._init = True

         
    @property
    def name(self):
        """The name of the behaviour
        
        Dynamic behaviours will return the behaviourName property
        """
        return self._get_dynamic_name()

            
    @property
    def object(self):
        """Returns the object the behaviour is a part of"""
        return self.get_owner()
    
    
    def _get_dynamic_name(self):
        if not self.is_dynamic:
            return self._name
        else:
            data_prop = self.get_property('behaviourName')
            if data_prop:
                return data_prop.get()

            return ''
                    
            
            #data_prop = self.get_property('behaviourName')
            #if data_prop:
                #name = data_prop.get()
            #else:
                #name = self.get_string('behaviourName')
            ##newly created behaviour's won't have a name assigned yet.
            #if name is None:
                #return ''
            
            #return name
        
            
    def _get_data(self, prop_name, is_range):
        if is_range:
            return DataRange(prop_name, self)

        return DataProperty(prop_name, self)
    
        
        
    def _get_setting(self, prop_name, is_range):
        if is_range:
            return SettingRange(prop_name, self)

        return SettingProperty(prop_name, self)
                
   
         
    def _get_object(self, prop_name, is_range):
        if is_range:
            return ObjectRange(prop_name, self)

        return ObjectProperty(prop_name, self )

  
        
    def _get_reference(self, prop_name, is_range):
        if is_range:
            return ReferenceRange(prop_name, self)

        return ReferenceProperty(prop_name, self)
                


    def __getattr__(self, attr):
        prop = self.get_property(attr)
        if prop is None:
            raise PropertyError(self.name, attr)
        
        return prop
        
        
    def get_property(self, name) -> DataProperty | ObjectProperty |\
        ReferenceProperty | SettingProperty | None:
        """Returns a property sub-class instance based on the property name
        
        This method will determine the correct getter method to call based on
        the type content the property name represents.
        
        Returns:
            DataProperty: For data properties
            ObjectProperty: For properties that hold object references
            ReferenceProperty: For propetries that hold behaviour references
            SettingProperty: For setting properties
            None: When a property by that name doesn't exist.        
        """
        
        property_type = self.get_property_type(name)         
        if property_type is None:
            return None
        
        if PropertyType.DATA in property_type:
            prop = self._get_data(name, PropertyType.RANGE in property_type)
            
        elif PropertyType.SETTING in property_type:
            prop = self._get_setting(name, PropertyType.RANGE in property_type)
            
        elif PropertyType.REFERENCE in property_type:
            prop = self._get_reference(name, PropertyType.RANGE in property_type)
            
        elif PropertyType.OBJECT in property_type:
            prop = self._get_object(name, PropertyType.RANGE in property_type)
            
        elif PropertyType.BEH_STRING in property_type:
            prop = StringProperty(name, self)
        else:
            #don't put self.name here, as that could loop on itself if the bad property drives the name            
            #print("cant get property type for {}.{} found as {}".format(self._name, name, property_type))
            
            #don't raise an exepction here, obj.name will raise an expection.  Users and this package
            #use this as a faster process than a try: or a new has_property()
            prop = None
            
        
        return prop
    
    
    def _get_property_type(self, name):
        """Used to build the internal self._property_types mapping"""
        try:
            self.get_data(name)
            return PropertyType.DATA
        except:
            pass
        
        try:
            self.get_data_range(name)
            return PropertyType.DATA_RANGE
        except:
            pass
        
        try:
            self.get_setting(name)
            return PropertyType.SETTING
        except:
            pass
        
        try:
            self.get_settings_range(name)
            return PropertyType.SETTING_RANGE
        except:
            pass
        
        try:
            self.get_object(name)
            return PropertyType.OBJECT
        except:
            pass
        
        try:
            self.get_objects_range(name)
            return PropertyType.OBJECT_RANGE
        except:
            pass
        
        try:
            self.get_reference(name)
            return PropertyType.REFERENCE
        except:
            pass
        
        try:
            self.get_reference_range(name)
            return PropertyType.REFERENCE_RANGE
        except:
            pass
        
        try:
            self.get_string(name)
            return PropertyType.BEH_STRING
        except:
            pass
        
        if ERROR_ON_UNKNOWN_PROPS:
            raise PropertyError(self.name, name)
        else:
            return PropertyType.UNKNOWN
    
        
    
    def get_property_type(self, name) -> PropertyType | None:
        """Return the type of data a behaviour property maps to"""
        
        if name not in self._property_types:
            return None
        
        return self._property_types[name]
    
    
    def get_siblings_by_name(self, behaviour_name: str):
        """alias for self.object.get_behaviours_by_name"""
        return self.object.get_behaviours_by_name(behaviour_name)
        

#----wrapped behaviour viewer functions----------------------        
    def get_name(self) -> str:
        """Returns the name of the behaviour
        
        For Dynamic behaviours this will return 'Dynamic'. Rather than using
        this method consider using PyBehaviour.name property if you want the
        display name of a Dynamic behaviour.
        """
        return self.beh_viewer.get_behaviour_name(self)
        
    def get_owner(self) -> PyObject | None:
        """Returns the object that holds the current behaviour"""
        return self.beh_viewer.get_behaviour_owner(self)

    def get_data(self, name) -> csc.model.DatatId:
        """Returns a csc.model.DatatId instance for the given property name"""
        return self.beh_viewer.get_behaviour_data(self, name)
    
    def get_data_range(self, name) -> typing.List[csc.model.DatatId]:
        """Returns a csc.model.DatatId list for the given property name"""
        return self.beh_viewer.get_behaviour_data_range(self, name)
    
    def get_setting(self, name) -> csc.model.SettingId:
        """Returns a csc.model.SettingId instance for the given property name"""
        return self.beh_viewer.get_behaviour_setting(self, name)
    
    def get_settings_range(self, name) -> typing.List[csc.model.SettingId]:
        """Returns a csc.model.SettingId list for the given property name"""
        return self.beh_viewer.get_behaviour_settings_range(self, name)

    def get_string(self, prop_name) -> str:
        return self.beh_viewer.get_behaviour_string(self, prop_name)

    def get_object(self, name) -> PyObject:
        """Returns a PyObject instance for the given property name"""
        return self.beh_viewer.get_behaviour_object(self, name)
    
    def get_objects_range(self, name) -> typing.List[PyObject]:
        """Returns a ObjectProperty list for the given property name"""
        return self.beh_viewer.get_behaviour_objects_range(self, name)
        
    def get_reference(self, name) -> PyBehaviour:
        """Returns a PyBehaviour for the given property name"""
        return self.beh_viewer.get_behaviour_reference(self, name)
    
    def get_reference_range(self, name) -> typing.List[PyBehaviour]:
        """Returns a PyBehaviour list for the given property name"""
        return self.beh_viewer.get_behaviour_reference_range(self, name)
    
    def is_hidden(self) -> bool:
        return self.beh_viewer.is_hidden(self)
    
    def get_property_names(self):
        """Returns a list of all the property names for this behaviour"""
        return self.beh_viewer.get_behaviour_property_names(self)
    
#----wrapped behaviour editor functions----------------------
    def _run_edit(self, func: str, *args, **kwargs):
        result = None
        def _behaviour_edit():
            nonlocal result, func, self
            
            #editor methods can't be accessed ahead of the edit(), so we need
            #to convert a string representation into the real func, now that
            #the editor is accessible.
            func = eval(func)

            result = func(*args, **kwargs)
            
        self.scene.edit('behaviour edit', _behaviour_edit, _internal_edit=True) #func.__name__
        return result

    def add_data_to_range(self, prop_name, data_id):
        func =  'self.beh_editor.add_behaviour_data_to_range'
        return self._run_edit(func, self, prop_name, data_id)
    
    def add_model_object_to_range(self, prop_name, model_id):
        func =  'self.beh_editor.add_behaviour_model_object_to_range'
        return self._run_edit(func, self, prop_name, model_id)
  
    def add_reference_to_range(self, prop_name, ref_id):
        func =  'self.beh_editor.add_behaviour_reference_to_range'
        return self._run_edit(func, self, prop_name, ref_id)
    
    def add_setting_to_range(self, prop_name, setting_id):
        func =  'self.beh_editor.add_behaviour_setting_to_range'
        return self._run_edit(func, self, prop_name, setting_id)
    
    def delete_self(self):
        func = 'self.beh_editor.delete_behaviour'
        result = self._run_edit(func, self)
        self.object.flush_cache()
        return result
        
    def erase_data_from_range(self, prop_name, data_id):
        func =  'self.beh_editor.erase_behaviour_data_from_range'
        return self._run_edit(func, self, prop_name, data_id)
    
    def erase_model_object_from_range(self, prop_name, model_id):
        func =  'self.beh_editor.erase_behaviour_model_object_from_range'
        return self._run_edit(func, self, prop_name, model_id)
  
    def erase_reference_from_range(self, prop_name, ref_id):
        func =  'self.beh_editor.erase_behaviour_reference_from_range'
        return self._run_edit(func, self, prop_name, ref_id)
    
    def erase_setting_from_range(self, prop_name, setting_id):
        func =  'self.beh_editor.erase_behaviour_setting_from_range'
        return self._run_edit(func, self, prop_name, setting_id)
    
    def hide(self, hidden=True):
        func =  'self.beh_editor.hide_behaviour'
        return self._run_edit(func, self, hidden)
    
    def set_data(self, prop_name, data_id):
        func =  'self.beh_editor.set_behaviour_data'
        return self._run_edit(func, self, prop_name, data_id)
    
    def set_data_to_range(self, prop_name, inserted_ids: typing.List[csc.model.DataId]):
        func =  'self.beh_editor.set_behaviour_data_to_range'
        return self._run_edit(func, self, prop_name, inserted_ids) 
    
    def set_model_object(self, prop_name, model_id):
        func =  'self.beh_editor.set_behaviour_model_object'
        return self._run_edit(func, self, prop_name, model_id)
    
    def set_model_objects_to_range(self, prop_name, inserted_ids: typing.List[csc.model.ObjectId]):
        func =  'self.beh_editor.set_behaviour_model_objects_to_range'
        return self._run_edit(func, self, prop_name, inserted_ids)  
  
    def set_reference(self, prop_name, ref_id):
        func =  'self.beh_editor.set_behaviour_reference'
        return self._run_edit(func, self, prop_name, ref_id)
    
    def set_references_to_range(self, prop_name, inserted_ids: typing.List[csc.model.Guid]):
        func =  'self.beh_editor.set_behaviour_references_to_range'
        return self._run_edit(func, self, prop_name, inserted_ids)
    
    def set_setting(self, prop_name, setting_id):
        func =  'self.beh_editor.set_behaviour_setting'
        return self._run_edit(func, self, prop_name, setting_id)
    
    def set_settings_to_range(self, prop_name, setting_id):
        func =  'self.beh_editor.set_behaviour_settings_to_range'
        return self._run_edit(func, self, prop_name, setting_id)
    
    def set_string(self, prop_name: str, value: str):
        func =  'self.beh_editor.set_behaviour_string'
        return self._run_edit(func, self, prop_name, value)
    
    def set_field_value(self, prop_name: str, value: str):
        func = 'self.beh_editor.set_behaviour_field_value'
        return self._run_edit(func, self, prop_name, value)
        


class PyLayer(PyGuid):
    def __init__(self, *args, **kwargs):
        super(PyLayer, self).__init__(*args, **kwargs)
        
    
    
class Property(PyGuid):
    """Base class for any Behaviour properties"""
    
    def __init__(self, name, behaviour, csc_object=None):
        super(Property, self).__init__(csc_object, behaviour)
        
        self._name = name
           
        
    def get(self):
        """get the data associated with the attribute"""
        
        raise NotImplementedError
    
    
    def set(self):
        """set the data associated with the atttribute"""
        
        raise NotImplementedError
    

    @property
    def name(self):
        return self._name
    
    @name.setter
    def name(self, name):
        self._name = name

    @property
    def behaviour(self) -> PyBehaviour:
        return self.creator
    
    
    
class StringProperty(Property):
    def get(self):
        return self.behaviour.get_string(self.name)
    
    def set(self, value):
        self.behaviour.set_string(self.name, value)
    
  
  
class DataProperty(Property):
    """Represents behaviour.properties that == csc.model.DataId(s)"""

                
    def _is_animateable(self, data_id):
        if data_id is None:
            raise (Exception("{}.{} has no data assigned").format(self.behaviour.name, self.name))
        
        return self.dat_viewer.get_data(data_id).mode == csc.model.DataMode.Animation
        
        
    def _get_id(self):
        data_id = self.unwrap()
        if data_id is None:
            data_id = self.behaviour.get_data(self.name)
            
        return data_id

             
    def is_animateable(self):
        data_id = self._get_id()
        return self._is_animateable(data_id)
        #return self.__data is not None and self.__data.mode == csc.model.DataMode.Animation
    
    
    def get(self, frame = None):
        """Return the value of the data block"""
        
        data_id = self._get_id()
        if data_id is None:
            return None            
        
        elif self._is_animateable(data_id):
            if frame is None:
                frame = self.domain_scene.get_current_frame()
                
            return self.dat_viewer.get_data_value(data_id, frame) 
        else:
            return self.dat_viewer.get_data_value(data_id)
        
        
    def set(self, value, frame=None, frames=None):
        #unwrap will be valid when the DataProperty was created from a DataRange
        data_id = self._get_id()
        if data_id is None:
            return            
        
        def _set_data():   
            if self._is_animateable(data_id):
                if frame is None and frames is None:
                    frame = self.domain_scene.get_current_frame()
                    
                if frame:
                    self.dat_editor.set_data_value (data_id, frame, value)
                else:
                    self.dat_editor.set_data_value(data_id, frames, value)
            else:
                self.dat_editor.set_data_value(data_id, value)
            
        self.scene.edit('Set Data', _set_data, _internal_edit=True)
        
        
    def get_default_value(self):
        return self.dat_viewer.get_behaviour_default_data_value(self.behaviour, self.name)
    
    
    def create_data(self, name: str, mode: csc.model.DataMode, value, data_id=None, group_name=None):
        """Creates a new csc.model.Data and assign it to the property"""
        added = False
        def _property_create_data():
            nonlocal added
            self._data = self.behaviour.object.create_data(name, mode, value, data_id=data_id, group_name=group_name)
            self.replace_data(self._data.id)
            added = self.behaviour.set_data(self.name, self)
           
        self.scene.edit("Add data to {}".format(self.name), _property_create_data, _internal_edit=True)
        return added
    

        
        
class SettingProperty(Property):
    """Represents behaviour.properties that == csc.model.SettingId(s)"""
             
    def _is_animateable(self, setting_id):
        if setting_id is None:
            raise (Exception("{}.{} has no settings data assigned").format(self.behaviour.name, self.name))
        
        return self.dat_viewer.get_setting(setting_id).mode == csc.model.SettingMode.Animation
        
        
    def _get_id(self):
        #unwrap will be valid when the SettingProperty was created from a
        #SettingRange
        setting_id = self.unwrap()
        if setting_id is None:
            setting_id = self.behaviour.get_setting(self.name)
            
        return setting_id
  
  
    def is_animateable(self):
        setting_id = self._get_id()
        return self._is_animateable(setting_id)          
            

    def get(self, frame = None):
        setting_id = self._get_id()
        if setting_id is None:
            return None        
        
        if self._is_animateable(setting_id):
            if frame is None:
                frame = self.domain_scene.get_current_frame()
                
            return self.dat_viewer.get_setting_value(self, frame) 
        else:
            return self.dat_viewer.get_setting_value(self)
        
        
    def set(self, value, frame=None, frames=typing.Set[int] | None):
        setting_id = self._get_id()
        if setting_id is None:
            return            
        
        def _set_setting():
            if self._is_animateable(setting_id):
                if frame is None and frames is None:
                    frame = self.domain_scene.get_current_frame()
                    
                if frame:
                    self.dat_editor.set_setting_value(setting_id, frame, value)
                else:
                    self.dat_editor.set_setting_value(setting_id, frames, value)
            else:
                self.dat_editor.set_setting_value(setting_id, value)
                
        self.scene.edit('Set Setting', _set_setting, _internal_edit=True)
        
        
        
class ObjectProperty(Property):
    """Represents behaviour.properties that maps to object(s)"""


    def get(self) -> PyObject |  None:
        """returns the PyObject stored by the property"""
        
        object_id = self.behaviour.get_object(self.name)
        if object_id is None:
            return None  
        else:
            return PyObject(object_id, self.scene) 
        

    def set(self, value: PyObject|None):
        if value is None:
            value = PyObject(csc.model.ObjectId.null(), self.scene)
            
        self.behaviour.set_model_object(self.name, value)
    
    
    
class ReferenceProperty(Property):
    """Represents behaviour.properties that map to other behaviour(s)"""    

    def get(self) -> PyBehaviour | None:
        """returns the PyBehaviour stored by the property
        
        When self.is_range() returns True, a list of results is returned.       
        """
        
        behaviour_id = self.behaviour.get_reference(self.name)
        if behaviour_id is None:
            return None
        #elif isinstance(content, list):
            #return [self.__get(value) for value in content]
        else:
            behaviour_owner = self.behaviour.beh_viewer.get_behaviour_owner(behaviour_id)
            return PyBehaviour(behaviour_id, behaviour_owner)
        

    def set(self, value: PyBehaviour|None):
        if value is None:
            value = csc.Guid.null()
            
        self.behaviour.set_reference(self.name, value)


    
class PropertyRange(Property):
    """Base class for any propeties that store an list of properties"""

    def _get_unwrapped_range(self):
        raise NotImplementedError
        
        
    def _wrap_item(self, item):
        """Wrap the input item"""
        
        raise NotImplementedError
    
    
    def set(self, item_list: list):
        """Set property to the input list"""
        
        raise NotImplementedError
    
    def add(self, element):
        """add the element to the range"""
        
        raise NotImplementedError
    
    
    def remove(self, element):
        """remove the element from the list"""
        
        raise NotImplementedError  
    
    
    def unwrap(self):
        return self._get_unwrapped_range()
        

    def _wrap_list(self, entries):
        return [self._wrap_item(item) for item in entries]  
        
        
    def get(self):
        """Returns the results of the range property wrapped"""
        return self._wrap_list( self._get_unwrapped_range() )

    
    def get_by_name(self, name : str, case_sensitive=False):
        """Returns a list of data properties that match the input name"""
        entries = self.get()
        if not case_sensitive:
            return [element for element in entries if element.name.lower() == name.lower()]
        else:
            return [element for element in entries if element.name == name]
        
    
    
class DataRange(PropertyRange):        
    def _get_unwrapped_range(self):
        """returns the unwrapped data.id list"""
        return self.behaviour.get_data_range(self.name)
    
    def _wrap_item(self, item) -> DataProperty:
        name =  self.behaviour.dat_viewer.get_data(item).name
        return DataProperty(name, self.behaviour, csc_object=item)

    def set(self, data_list: typing.List[csc.model.DataId]):
        self.behaviour.set_data_to_range(self.name, data_list)
    
    def add(self, element: csc.model.DataId):
        self.behaviour.add_data_to_range(self.name, element)

    def remove(self, element: csc.model.DataId):
        self.behaviour.erase_data_from_range(self.name, element)
    
    def create_data(self, name: str, mode: csc.model.DataMode, value, data_id=None, group_name=None):
        """Creates a new csc.model.Data and assign it to the property"""
        added = False
        def _create_data():
            nonlocal added
            new_data = self.behaviour.object.create_data(name, mode, value, data_id=data_id, group_name=group_name)
            if new_data is not None:
                added = self.add(new_data.id)
            else:
                print('failed to create and add data to {}.{}'.format(self.behaviour.object, self.name))
           
        self.scene.edit("Add data to {}".format(self.name), _create_data, _internal_edit=True)
        return added

  

class SettingRange(PropertyRange):        
    def _get_unwrapped_range(self):
        """returns the unwrapped data.id list"""
        return self.behaviour.get_settings_range(self.name)
    
    def _wrap_item(self, item) -> DataProperty:
        name =  self.behaviour.dat_viewer.get_setting(item).name
        return SettingProperty(name, self.behaviour, csc_object=item)

    def set(self, item_list: typing.List[csc.model.SettingId]):
        self.behaviour.set_settings_to_range(self.name, item_list)
    
    def add(self, element: csc.model.SettingId):
        self.behaviour.add_setting_to_range(self.name, element)

    def remove(self, element: csc.model.SettingId):
        self.behaviour.erase_setting_from_range(self.name, element)
    
    def create_setting(self, name: str, mode: csc.model.SettingMode, value, setting_id=None, group_name=None):
        """Creates a new csc.model.Data and assign it to the property"""
        added = False
        def _create_data():
            nonlocal added
            new_setting = self.behaviour.object.create_setting(name, mode, value, setting_id=setting_id, group_name=group_name)
            if new_setting is not None:
                added = self.add(new_setting.id)
            else:
                print('failed to create and add setting to {}.{}'.format(self.behaviour.object, self.name))
           
        self.scene.edit("Add data to {}".format(self.name), _create_data, _internal_edit=True)
        return added



class ReferenceRange(PropertyRange):
    def _get_unwrapped_range(self):
        return self.behaviour.get_reference_range(self.name)
    
    def _wrap_item(self, item) -> PyBehaviour:
        behaviour_owner = self.beh_viewer.get_behaviour_owner(item)
        return PyBehaviour(item, behaviour_owner)
    
    def set(self, item_list: list):
        self.behaviour.set_references_to_range(self.name, item_list)
    
    def add(self, element: PyBehaviour):
        self.behaviour.add_reference_to_range(self.name, element)
    
    def remove(self, element: PyBehaviour): 
        self.behaviour.erase_reference_from_range(self.name, element)
        
        
        
class ObjectRange(PropertyRange):
    def _get_unwrapped_range(self):
        return self.behaviour.get_objects_range(self.name)
    
    def _wrap_item(self, item) -> PyBehaviour:
        return PyObject(item, self.scene)
    
    def set(self, item_list: typing.List[PyObject]):
        self.behaviour.set_model_objects_to_range(self.name, item_list)
    
    def add(self, element: PyObject):
        self.behaviour.add_model_object_to_range(self.name, element)
    
    def remove(self, element: PyObject): 
        self.behaviour.erase_model_object_from_range(self.name, element)



class GuidMapper(SceneElement):
    """Used to wrap a generic csc.Guid to a specific class
    
    This is a really stupid class that makes assumptions that any
    generic csc.Guid is actually a specific guid under a given
    context    
    """
    guid_class = None    

          
class LayersViewer(GuidMapper):
    guid_class = PyLayer
    
    
class LayersEditor(GuidMapper):
    guid_class = PyLayer
    
    
class BehaviourViewer(GuidMapper):
    guid_class = PyBehaviour
    
    
class BehaviourEditor(GuidMapper):
    guid_class = PyBehaviour
       
           
class ModelViewer(GuidMapper):
    guid_class = None
          
        
class DataViewer(GuidMapper):
    guid_class = None
        

class DomainScene(GuidMapper):
    guid_class = None
    
    
class UpdateEditor(SceneElement):
    def create_object_node(self, name) -> PyUpdateObject:
        root_group = self.update_editor.root()
        new_object = root_group.create_object(name)

        return new_object
    
        
        
if __name__ == '__main__':
    scene_manager = csc.app.get_application().get_scene_manager()
    scene = scene_manager.current_scene()
    current_scene: PyScene = PyScene.wrap(scene, None)
    current_scene.create_object('MyObject')
    
