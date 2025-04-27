"""The udata module creates and manages Maya attributes in a pythonic way

Adding and managing custom attributes in Maya through Maya's standard low
level functions such as addAttr() has a few drawbacks that this higher-level
module attempts to overcome. These noteable improvements include:

1. udata handles all the back-end work of reading and writing
udata.BaseData class attributes to Maya attributes. Programmers and
Tech-artists can simply search for their Python classes inside of a Maya
scene or on a given node and work with the results.

2. Attributes in the attributes editor are organized under a compound
attribute, making it easy for end-users to understand how blocks of
attributes related to one another.

3. Built-in versioning support. Outdated attributes can easily be
identified and updated to match their Python equivalent as code evolves.

4. Less attribute flags and more automation. A number of addAttr() flags can
be determined automatically so you don't need to worry about things like -at
and -dt, parent or child count, or even making attributes for compounds where
the child size is predetermined.
"""

__author__ = "Nathaniel Albright"
__email__ = "developer@3dcg.guru"

VERSION = (0, 9, 0)
__version__ = '.'.join(map(str, VERSION))


import pymel.core as pm

#Don't change _RECORDS_NAME unless your project really desires an alternative
#name for the life of all scripts and tools that leverage the udata module
#(and remember to change it whenever getting an updated version of the module).
_RECORDS_NAME = 'DataRecords'
"""The name of the custom attr that tracks what data is on a node"""

DEFAULT_NODE_TYPE = 'network'
"""The nodeType that will be created when creating a node for storing data"""

AUTO_UPDATE = False
"""Should versioning attempt to auto update when there's a version mismatch?

Some studios may want outdated class data to automatically update. Setting
this to True will mean outdated data will attempt to update when it's
discovered. User's can decide this on a per-class instance by overriding
BaseData.pre_update_version().
"""

REPORT_WARNINGS = True
"""Should this module throw warnings?"""

class VersionUpdateException(Exception):
    """Thrown when BaseData.update_version() errors"""
    pass


class Attr(object):
    """A Wrapper for Maya's attribute arguements"""
    
    
    attr_types = set(['bool', 'long', 'short', 'byte', 'char', 'enum',
                      'float', 'double', 'doubleAngle', 'doubleLinear', 'message', 'time',
                      'fltMatrix'])
    """A list of attributeType names that use the -at flag"""    
    
    
    data_types = set(['string', 'stringArray', 'matrix',
                      'reflectanceRGB', 'spectrumRGB', 'float2', 'float3', 'double2',
                      'double3', 'long2', 'long3', 'short2', 'short3', 'doubleArray',\
                      'floatArray', 'Int32Array', 'vectorArray', 'nurbsCurve', 'nurbsSurface',\
                      'mesh', 'lattice', 'pointArray']
                     )
    """A list of attributeType names that use the -dt flag
    
    If an attr.attr_type is found in Attr.data_types then the 'dt' flag
    is automatically added to the args when creating the Maya attribute, else
    the 'at' flag is used.
    """
     
        
    def __init__(self, name, attr_type, *args, **kwargs):
        """The init func can take any arguments used in maya.cmds.addAttr()
                
        Users don't need to include the following flags:
        
        -longName or -ln : this is instead derived from the Attr.name.
        -attributeType or -at : this is determined by inspecting Attr.attr_type.
        -dataType or -dt : this is determined by inspecting Attr.attr_type.
        -parent or -p: Determined by the Compound class parent-child structure
        -numberOfChildren or -nc : Determined by the Compound class parent-child structure
        """
        super(Attr, self).__init__()
        
        self.name = name
        self.attr_type = attr_type
        self.args = args
                
        #combine any input flags with class defined flags
        flags = self.get_default_flags()
        flags.update( kwargs )
        self._clear_invalid_flags( flags )
        
        self._flags = flags
        

    @staticmethod
    def _clear_invalid_flags(flags):
        invalid = [ 'longName', 'ln', 'attributeType', 'at', 'dataType', 'dt', 'p', 'parent', 'numberOfchildren', 'nc']
        for key in invalid:
            if key in flags:
                flags.pop(key)
                
                
    @classmethod
    def get_default_flags(cls):
        """Defines class level flag arguments
        
        Sub-classes of Attr can override this function and return any
        flags used in maya.cmds.addAttr() so the class has a consistant
        look in Maya.        
        """
        return {}    
        
        
        
class Compound(Attr):
    """An attribute class that contains children attributes.
    
    For any -attributeType other than 'compound', users don't need to create
    the children attributes. For example: Compound("space", 'float3') will
    automatically create spaceX, spaceY, spaceZ.  If you don't want auto
    creation of child attributes then set make_elements=False on init.
    """
    
    compound_types = {'compound':0,
                     'reflectance':3, 'spectrum':3,
                     'float2':2, 'float3':3,
                     'double2':2, 'double3':3,
                     'long2':2, 'long3':3,
                     'short2':2, 'short3':3
                    }
    """A Dict of valid compound attr types and how many children to auto-create"""
    
    
    child_types = {'reflectance':'float', 'spectrum':'float',
                   'float2':'float', 'float3':'float', 'double2':'double',
                   'double3':'double', 'long2':'long', 'long3':'long', 'short2':'short',
                   'short3':'short'
                   }
    """What is the sub-element type that makes up this compound"""
    
    
    def __init__(self, name, attr_type, children = None, make_elements = True, *args, **kwargs):
        #reflectance and spectrum don't play nice with the color picker in the attr
        #so let's convert these to a float3 with a color flag
        if attr_type == 'reflectance' or attr_type == 'spectrum':
            attr_type = 'float3'
            kwargs['uac'] = True
                
        super(Compound, self).__init__(name, attr_type, *args, **kwargs)
        
        #don't make children = [] in the __init__ as it's persistant data
        #between class() calls.
        if children is None:
            children = []
        
        if attr_type not in Compound.compound_types:
            pm.error('udata Module: {0} is not a valid CompoundType.  Print Compound.CompoundTypes for valid list'.format(attr_type))
        
        self._target_size = Compound.compound_types[attr_type]
        self._children   = children
        
        if self._target_size and make_elements:
            if self._children:
                pm.error('udata Module: You supplied children, but also have make_elements = True.  Children will be erased')
            
            self._make_elements()

    
    def _make_elements(self):
        #define suffix for children
        xyz = ['X', 'Y', 'Z']
        rgb = ['R', 'G', 'B']
        
        suffix = xyz
        if 'usedAsColor' in self._flags or 'uac' in self._flags or \
           self.attr_type == 'spectrum' or self.attr_type == 'reflectance':
            suffix = rgb
            
        #determine child type
        type = Compound.child_types[self.attr_type]
            
        #add children to compound
        for i in range(0, self._target_size):
            attr = Attr(self.name + suffix[i], type)
            self.add_child(attr)
        
        
    def count(self):
        """How many children does this attribute have?"""
        return len(self._children)
    
    
    def add_child(self, child):
        """Add an attribute to this Compound as a child"""
        
        if self._target_size and len(self._children) > self._target_size:
            pm.error('udata Module: Compound instance has reached the max allowed children')
            
        self._children.append(child)
        
        
    def get_children(self):
        """Return the internal list of children"""
        return self._children
        
        
    def validate(self):
        """Confirm that the required number of children exist
        
        If the attr_type is 'compound' then one or more children must exist
        for this to be true. For all other attr_types the size of children
        must match the required count defined in Compound.compound_types
        """
        
        valid_size = False
        if not self._target_size:
            valid_size = len(self._children) > 0
        else:
            valid_size = self.count() == self._target_size
            
        if not valid_size:
            pm.error('udata module: {0} does not have the required number of children'.format(self.attr_type))



def create_attr(name, attr_type, *args, **kwargs):
    """A convience func returns an Attr() or Compound() based on the attr_type"""
    if attr_type in Compound.compound_types:
        return Compound(name, attr_type, *args, **kwargs)
    else:
        return Attr(name, attr_type, *args, **kwargs)
    


class Record(object):
    """The name of the class data found on a Maya node and its version info"""
    
    def __init__(self, attr):
        self._attr = attr
        self._name, str_version = attr.get().split(':')
        self._version = tuple(map(int, str_version.split('.')))
        

    @property
    def name(self):
        """The name of the class"""
        return self._name

        
    @property
    def version(self):
        """What version of the class is this record"""
        return self._version
    
    
    @version.setter
    def version(self, value):
        """Updates the version information for this record"""
        self.attr.unlock()
        self._version = value
        name = '{0}:{1}'.format( self.name, self._get_version_string() )
        self.attr.set( name )
        self.attr.lock()  
        
        
    @property
    def attr(self):
        """Returns the Maya attribute that represents this record"""
        return self._attr
    
    
    def _get_version_string(self):
        return '.'.join(map(str, self._version))
    
    
    
class BaseData(Attr):
    """Represents data that the user wants to store as Maya attributes
    
    Users should inherit from this class and at a minimum override
    get_atttributes(). get_attributes should either be declared as
    @classmethod or @staticmethod
    
    The python class names will become a compound attribute of the same name.
    Users can override cls.get_default_flags() to determine how this class
    looks as an attribute in Maya or pass the flags in on init().
    
    The BaseData class is responsible for reading and writing Maya attributes,
    creating and editing records, as well as class.version management.
    
    Any object that has a block of BaseData attributes stored on it will also
    contain a data block name that matches udata._RECORDS_NAME. Records are
    used for determing what version BaseData sub-classes are being stored on
    a given node. If a record for a given class is missing from the records
    then the udata module won't know that the data exists.
    """
    
    attributes = []
    """The attributes returned from get_atttributes()
    
    These attributes are stored at the class level so the data can be
    inspected and read without needing to create an instance of the class.
    Additionally, per instance attrs doesn't make sense in the scheme
    of how data is stored and used by this module.
    """

    _records = None
    _node = None
    _data_stack = []

    def __init__(self, *args, **kwargs):  
        super(BaseData, self).__init__(self.get_name(), 'compound', *args, **kwargs)
        
        self._init_class_attributes()

###----Versioning Methods----

    @classmethod
    def get_class_version(cls):
        return (0, 0, 0)
     

    @classmethod
    def get_version_string(cls):
        return '.'.join(map(str, cls.get_class_version()))

###----Record Methods-----

    @classmethod
    def _add_data_to_records(cls):
        if cls._records:

            indices = cls._records.getArrayIndices()
            if not indices:
                idx = 0
            else:
                idx = -1
                for i in range(0, indices[-1]):
                    if not i in indices:
                        idx = i
                        break
                    
                if idx == -1:
                    idx = indices[-1] + 1
            
            #concatenating the name and version is not as clean in code (vs
            #seperate attributes), but it makes end-user view from the
            #attribute editor clean while not taking up as much UI space
            name = '{0}:{1}'.format( cls.get_name(), cls.get_version_string() )
            cls._records[idx].set( name )
            cls._records[idx].lock()
            
                  
    @staticmethod
    def _create_records(node):
        global _RECORDS_NAME
        pm.addAttr(node, ln = _RECORDS_NAME,  dt = 'string', m= True)
                          
       
    @classmethod     
    def _get_records(cls, node, force_add ):
        if not node:
            pm.error('udata Module : Can\'t get records. node is None')
            
        has_records = pm.hasAttr(node, _RECORDS_NAME)
                
        if (not has_records) and force_add:
            cls._create_records( node )
            has_records = True
        
        if has_records:
            return node.attr(_RECORDS_NAME) #.records
        else:
            return None
        
 
    @classmethod
    def get_records(cls, node):
        """Sees if any records exists on the input node
        
        The records attributes will contain all list of all
        the records stored on the node.
        
        Returns the records attribute if found else None.
        """
        return cls._get_records(node, False)
 

    @classmethod
    def _get_record_by_name(cls, node, data_name):
        records = cls._get_records(node, False)
        found_record = None
        if records:
            for i in records.getArrayIndices():
                record = records[i]
                if not record.get():
                    continue
                
                name, version = record.get().split(':')
                if name == data_name:
                    found_record = Record(record)
                    break
                
        return found_record           

    
    #@classmethod
    #def get_record_by_name(cls, node, data_name):
        #"""Sees if a record by the input data_name exists on the input node
        
        #Returns the record if it exists, else None.
        #WARNING: This skips any class update checks.  It's better to use
        #class.get_data(node)
        #"""
        #return cls._get_record_by_name( node, data_name )
    
    
    @classmethod
    def get_record(cls, node):
        """see if a record matching the get_name() on the input node
        
        Returns the record if it exists, else None         
        """
        return cls._get_record_by_name( node, cls.get_name() )
    
                  
###----Attribute Methods----
 
    @classmethod
    def _find_attr_conflicts(cls):
        attr_names = cls.get_attribute_names()
        flags = cls.get_default_flags()
        cls._clear_invalid_flags(flags)
        
        if 'multi' in flags or 'm' in flags:
        #if 'multi' in cls._flags or 'm' in cls._flags:
            #I *believe* attributes that are part of a multi arg won't conflict.            
            attr_names = []       
        
        attr_names.append( cls.get_name() )
        
        conflicts = []
        for attr_name in attr_names:
            if pm.hasAttr(cls._node, attr_name):
                conflicts.append(attr_name)
                
        if conflicts:
            record_names = []
            for i in cls._records.getArrayIndices():
                record = Record(cls._records[i])
                record_names.append( record.name )            

            class_name = cls.__name__
            errorMessage = 'udata Attribute Conflict :: Attribute Name(s) : {0} from class "{1}" conflicts with one of these existing blocks of data : {2}'
            pm.error( errorMessage.format(conflicts, class_name, record_names) )
 
    @classmethod          
    def _add_attr(cls, attr, prefix, parent_name):
        attr_name = prefix + attr.name
        
        if parent_name:
            attr._flags['parent'] = parent_name
           
        if isinstance(attr, Compound):
            attr.validate()
            pm.addAttr(cls._node, ln = attr_name, at = attr.attr_type, nc = attr.count(), **attr._flags)
            for child in attr.get_children():
                cls._add_attr(child, '', attr_name)
            
        elif attr.attr_type in Attr.data_types:
            pm.addAttr(cls._node, ln = attr_name, dt = attr.attr_type, **attr._flags)             
        else:   
            pm.addAttr(cls._node, ln = attr_name, at = attr.attr_type, **attr._flags)     
           
           
    @classmethod                   
    def _get_attribute_names(cls, attr, name_list):
        name_list.append(attr.name)
        if isinstance(attr, Compound):
            for child in attr.get_children():
                cls._get_attribute_names(child, name_list)
            
            
    @classmethod        
    def get_attribute_names(cls):
        """returns a flat list of all the attribute names in class.attributes"""
        name_list = []
        cls._init_class_attributes()
            
        for attr in cls.attributes:
            cls._get_attribute_names(attr, name_list)
            
        return name_list

      
    @classmethod
    def _init_class_attributes(cls):
        if not cls.attributes:
            cls.attributes = cls.get_attributes()
        
        
    @classmethod
    def get_attributes(cls):
        """MUST IMPLEMENT : A list of udata.Attrs stored in this class.
        
        Sub-classes of BaseData must override this function and return
        the attributes they want to create and store in Maya. The function
        must also be declared as a class or static method.        
        """
        pm.error( 'udata Module: You\'re attempting to get attributes for class {0} that has no get_attributes() overridden'.format(cls.__name__) )       
       
       
###----Update Methods----
    
    @classmethod
    def pre_update_version(cls, old_data, old_version_number):
        """Determines if the update_version() should be called.
        
        Users can override this function if they wish to define their own
        logic. By default the function returns udata.AUTO_UPDATE, which
        is False by default.
        
        Args:
            old_data (pymel.general.Attr) : The data that's about to be updated.
            old_version_number (Tuple) : The version information of the old_data.
        
        Returns:
            Bool: True if update_version() should be called, else False.
        """
        global AUTO_UPDATE
        if not AUTO_UPDATE and REPORT_WARNINGS:
            pm.warning('cg3dguru.udata : Skip updating old data on "{}" of type "{}" because AUTO_UPDATE is False. Consider overriding pre_update_version(). Repress this warning with udata.REPORT_WARNINGS = False'
                       .format(old_data.node(), cls.__name__))
        
        return AUTO_UPDATE
     
    @classmethod  
    def update_version(cls, old_data, old_version_number):
        """Updates the data to the latest version of the Python defintion.
        
        The default implimentation of this happens in five steps.
        1. A temporary node is created with the latest class data
        2. The current data values are copied to the temp node using pymel.core.copyAttr
        3. The current data is deleted off the original node
        4. The new data is added to the original node.
        5. The data values are transferred back from the temp node to the original node.
        
        Failure of this process could occur during step #2. In this situation
        udata.VersionUpdateException is raised and the user will need to
        determine their own logic for how to update/replace their existing
        data with the new class version.
        
        Args:
            old_data (pymel.general.Attr) : the data of the outdated version.
            old_version_number (tuple) : The Max, min, patch value of the old data.
        
        Returns:
            Bool : True if the update was successful else False.
        """
        
        
        #Copy the attribute values to a temporary node
        #cls._node = old_data.node()
        
        temp_node, data = cls.create_node(name = 'TRASH', ss=True)
        name_list = cls.get_attribute_names()
        try:
            pm.copyAttr(cls._node, temp_node, at=name_list, ic=True, oc=True, values=True)
        except:
            #delete the tempNode
            pm.delete(temp_node)
            
            message = 'Please impliment custom update logic for class: {0}  oldVersion: {1}  newVersion: {2}'.format( cls.get_name(), old_version_number, cls.get_class_version())
            raise VersionUpdateException(message)
        
        #delete the attributes off the current node
        pm.deleteAttr( cls._node, at = cls.get_name() )
        
        #rebuild with the latest definition
        cls._create_data()

        #transfer attributes back to original node
        pm.copyAttr(temp_node, cls._node, at = name_list, ic = True, oc = True, values = True)  
        
        #delete the tempNode
        pm.delete(temp_node)
        
        return True

    @classmethod    
    def post_update_version(cls, data, update_successful):
        """Called after update_version()
        
        The default implimentation does nothing. Users can override
        this function if they want to do any post processing after
        the update_function has been run.
        
        args:
            data (pymel.general.Attr) : The newly updated data if successful
            else the old data.
            update_successful (bool) : Was the update successful.
        """        
        pass
    
    
###----Data Methods----
    
    @classmethod
    def get_name(cls):
        """The name of the class as it will appear in Maya's extra attributes
        
        By default the name is the same as the class.__name__ This should be
        determined upfront before using the name in production.  Once changed
        any existing records and associated data will be orphaned.  If users
        opt to override this, they must include a @classmethod declarator
        """
        return cls.__name__
    
    
    @classmethod
    def get_prefix(cls):
        """Retuns the prefix to append to all class attributes
        
        The deault prefix is an empty string. The prefix is designed to limit
        the potential of an attribute name collision between mutliple
        udata blocks assigned to the same maya node. Users can return ''
        if they don't want a prefix added to their attribute names. Any valid
        prefix will automaticallly be separated by '_'
        
        NOTE: If you decided to change the prefix once the data is production
        then you'll need to override update_version() with your own logic
        as old names and new names won't match when updating the data block.        
        """
        return ''
    
    
    @classmethod
    def get_attr_name(cls, attr_name):
        """return the input attribute name with an class prefix"""
        prefix = cls.get_prefix()
        if prefix:
            prefix += '_'
            
        return prefix + attr_name

            
    @classmethod
    def _create_data(cls):     
        attrs = cls.attributes
        long_name = cls.get_name()
        
        flags = cls.get_default_flags()
        cls._clear_invalid_flags(flags)        
        
        pm.addAttr(cls._node, ln = long_name, at = 'compound', nc = len( attrs ), **flags )

        prefix = cls.get_prefix()
        if prefix:
            prefix += '_'

        for attr in attrs:
            cls._add_attr(attr, prefix, long_name)       
         
        return cls._node.attr(long_name)
        
    @classmethod   
    def post_create(cls, data):
        """Called after the data has been created.
        
        This function doesn't do anything by default and exists purely
        for end-user convenience.  What a great place for adding your new
        data to an existing node network!
        
        Args:
            data (pymel.general.Attr) : The newly created data. 
        
        """        
        pass
              
    @classmethod
    def get_data(cls, node, force_add = False):
        """Attempts to return the class data stored on the input node.
        
        Args:
            node (pyNode) : The node you want to get/store data on
            force_add (bool) : Should the data be added if none exists?
            
        Returns:
            pymel.general.Attr : The data stored on the node or None.        
        """

        #We need to cache the current data, because get_data might be called
        #while doing an update. As this function gets deeper in scope, we
        #need to make sure we reset the data as we leave the scope. reseting
        #happens on exit.
        cls._data_stack.append((cls._records, cls._node))
        
        cls._records = None
        cls._node    = node
        
        record = cls.get_record(node)
        
        if not record and force_add:
            #lets make sure the records data exists
            cls._records = cls._get_records(node, force_add = True)
            
        #If found make sure the data block doesn't need updating.
        if record:
            data_name = cls.get_name() 
            record_version = record.version
            current_version = cls.get_class_version()
            
            #Attempt to updat the version
            if record_version < current_version:
                old_data = cls._node.attr(data_name)
                
                if cls.pre_update_version(old_data, record_version):
                    updated = cls.update_version(old_data, record_version)
                    if updated:
                        record.version = current_version
                                
                    data = cls._node.attr(data_name)
                    cls.post_update_version( data, updated )

            
            data = cls._node.attr(data_name)
                    
        #else, add the data to the node           
        elif force_add:
            cls._find_attr_conflicts()
            data = cls._create_data()
            cls._add_data_to_records()
            cls.post_create( data )
            
        else:
            data = None

        cls._records, cls._node = cls._data_stack.pop(-1)

        return data      
    
    @classmethod  
    def add_data(cls, node):
        """Add class attributes to the input node.
        
        If the input node already has data on it then versioning is run to
        ensure the data format is up-to-date.
        
        Args:
            node (pyNode) : The node to add the data to.
                
        Returns:
            pymel.general.Attr : The data added to the node.
        """
        return cls.get_data(node, force_add=True)
    

    @classmethod
    def delete_data(cls, node):
        """Remove the class attributes off of the input node

        Args:
            node (pyNode) : The node to remove the data from.        
        """
        record = cls.get_record(node)
        
        if record:
            record.attr.unlock()
            pm.removeMultiInstance(record.attr, b=True)
            pm.deleteAttr(node, at = cls.get_name() )   
            

###----Misc Methods----
    
    @classmethod
    def create_node(cls, nodeType = DEFAULT_NODE_TYPE, *args, **kwargs):
        """Creates a new node in Maya that also contains the Class attributes.
        
        The default node type that's created is driven by
        udata._DEFAULT_NODE_TYPE, but users can override this based on
        the input params.
        
        Args:
            nodeType (str, optional) : The name of the maya node to create.
            
        Returns:
            Tuple : The newly created pyNode as element zero and the data as
            element 1.
        """
        pynode = pm.general.createNode(nodeType, **kwargs)
    
        if pynode:
            #classInstance = cls()
            data = cls.get_data(pynode, force_add=True)
            
        return (pynode, data)   
    

    
class Utils(object):
    """Easy module and maya scene inspection
    
    The udata.Utils class provides a number of functions
    to inspect not only the active Maya scene, but also an inspection
    of Python classes that derive from udata.BaseData. Users
    can verify that there won't be any attribute naming conflicts between
    the various class defintions, search for data that's being used
    in the active scene, as well as verify verioning.    
    """
    def __init__(self, *args, **kwargs):
        super(Utils, self).__init__(*args, **kwargs)
    
    
    @staticmethod
    def get_classes():
        """Returns all BaseData subclass"""
        classes = BaseData.__subclasses__()
        return classes
    
    
    @staticmethod
    def get_class_names():
        """Returns a list of all BaseData subclass names."""
        sub_classes = Utils.get_classes()
        class_names = {}
        for subclass in sub_classes:
            class_names[ subclass.get_name() ] = subclass
            
        return class_names

    
    @staticmethod
    def find_attribute_conflicts(error_on_conflict = True):
        """Find any attribute naming conflicts between the BasData subclasses.
        
        Since the BaseData.attributes are written to Maya as basic attributes
        it's possible to have a naming conflict between to classes. For
        example myclass.startFrame and exportData.startFrame. Users can call
        this function after adding any new class definition to ensure there
        aren't any naming conflicts. In reality, if two classes do have a
        naming conflict but the production pipeline means those two blocks of
        data would never be stored on the same object, then the conflict
        should be a non-issue. this function will print any found conflicts
        in the output window and optionally raise an error if a conflict has
        been found.
        
        Args:
            error_on_conflict (bool) : Should an error be raised if a
            conflict is found?
        """
        
        conflicts = {}
        attrs = {}
        for subclass in Utils.get_classes():
            default_flags = subclass.get_default_flags()
            
            #if the Class is going to be added with a mutli flag, then
            #there shouldn't be any conflicts with its attributes
            if 'm' in default_flags or 'multi' in default_flags:
                continue
            
            attribute_names = subclass.get_attribute_names()
            for attr_name in attribute_names:
                if attr_name not in attrs:
                    attrs[attr_name] = [subclass.__name__]
                else:
                    attrs[attr_name].append(subclass.__name__)
                    
        for attr_name in attrs:
            classes = attrs[attr_name]
            
            if len(classes) > 1:
                conflicts[attr_name] = classes
                
        if conflicts:
            for attr_name in conflicts:
                classes = conflicts[attr_name]
                if REPORT_WARNINGS:
                    pm.warning( 'udata.Utils :: Attr conflict. : "{0}" exists in classes: {1}'.format(attr_name, classes))
                
            if error_on_conflict:
                pm.error( 'udata.Utils :: Found conflict between attribute names. See console for info.')
                
        return conflicts
    
    
    @staticmethod
    def get_nodes_with_data(nodes = None, data_class = None, *args, **kwargs):
        """Return a list of nodes that have any (or specific) data attached
        
        Users can pass in a list of nodes to examine or if no nodes are
        provided they can pass in the standard pymel.core.ls args to generate
        a list of node to inspect.
        
        Args:
            nodes (pyNode list, optional) : What nodes should the function
            search?
            data_class (BaseData sub-class, optional) : What class data
            are we looking for. If this is None then a node will be
            returned if it has any data attached to it.
            **kwargs (pymel.ls flags) : Only considered if node is None.
            
        Returns:
            list : A list of pyNodes that match the given search criteria. 
        """
        if not nodes:
            nodes = pm.ls(*args, **kwargs)
            nodes.sort()
        
        data_nodes = []
        for node in nodes:
            if data_class:
                records = data_class.get_data(node) #BaseData.get_record_by_name( node, data_class.get_name() )
            else:
                records = BaseData.get_records(node)
                
            if records:
                data_nodes.append(node)
                
        return data_nodes
    
    
    @staticmethod
    def validate_version(nodes = None, *args, **kwargs):
        """Force version validation on the given node conditions

        This function can be used to ensure current scene nodes have their
        data up-to-date. Users can pass in a list of nodes to examine or if
        no nodes are provided they can pass in the standard pymel.core.ls
        args to generate a list of node to inspect.
        
        Validating a scene might look something like this:
        
        #find all scene nodes that have any data on them
        nodes = Utils.get_nodes_with_data()
        
        #Update the nodes we found in our scene.
        Utils.validate_version(nodes = nodes)
        
        If you're feeling really lazy you can just examine every object in
        the scene against every potential class like this:
        
        Utils.validate_version()
            
        Args:
            nodes (pyNode list, optional) : What nodes should the function
            search?
            **kwargs (pymel.ls flags) : Only considered if nodes is None.
        """
        if not nodes:
            nodes = pm.ls(*args, **kwargs)        
                
        classes= Utils.get_classes()
        
        for data_class in classes:
            #instance = data_class()
            for node in nodes:
                #this forces a version check
                data_class.get_data(node)
                #instance.get_data(node)

        
            
    
    

