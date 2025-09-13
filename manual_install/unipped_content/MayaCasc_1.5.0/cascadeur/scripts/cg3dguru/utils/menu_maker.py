import sys
import os
import pymel.core as pm
import pkgutil
import importlib
from pathlib import Path

    
class MenuItem(object):
    """Base class for creating menu items, including menus and radio groups
    """
    def __init__(self, name, path, relative_path, is_menu):
        self.name = name
        self.parent = None
        self.children = {}
        self.path = path
        self.relative_path = relative_path
        
        #menu item info
        self.menu_instance = None
        self.divider = None
        self.params = {}
        self.order = []
        self.is_menu = is_menu
        self.is_radio_group = False
        self.is_options_box = False
        self.is_root_menu = False
        self.show = True
        
        #parsed functions
        self.command = None
        self.ddc_command = None
        self.dmc_command = None
        self.pmc_command = None
        
        
    def get_variable_name(self):
        item_name = 'MENU_ITEM'
        if self.is_options_box:
            item_name = 'OPTIONS_ITEM'
            
        return item_name
        
        
    def __set_args(self, module, attr_name, alt_name):
        """maps a function (if it exists) to its menu_item argument"""
        if not hasattr(module, attr_name):
            if attr_name in self.params:
                return self.params[attr_name]
            elif alt_name in self.params:
                return self.params[attr_name]
            else:
                return None
        
        attr = getattr(module, attr_name)
        
        if alt_name in self.params:
            self.params.pop(alt_name)
            
        self.params[attr_name] = attr
        
        return attr
        
        
    def parse_module(self):
        """Loads the python module associated with this object and parses it
        
        """
        #DONT try to parse on __init__, because this fuction creates an option box
        #with the same path info, which causes recursion.
        try:
            #only import if the modules isn't already imported
            module = sys.modules[self.relative_path]
        except:
            importlib.import_module(self.relative_path)
            module = sys.modules[self.relative_path]

        if hasattr(module, 'PARAMS'):
            self.params = module.PARAMS
        if hasattr(module, 'DIVIDER'):
            self.divider = module.DIVIDER
        if hasattr(module, 'ORDER'):
            self.order =  module.ORDER
        if hasattr(module, 'IS_RADIO_GROUP'):
            self.is_radio_group = module.IS_RADIO_GROUP
        if hasattr(module, 'SHOW'):
            self.show = module.show()
        if hasattr(module, 'OPTIONS'):
            options_name = "{}_{}".format(self.name, 'options')
            child_item =  MenuItem(options_name, self.path, self.relative_path, False)
            self.children[options_name] = child_item
            
            child_item.is_options_box = True
            child_item.params = module.OPTIONS
            if not 'optionBox' in child_item.params and not 'ob' in child_item.params:
                child_item.params['optionBox'] = True
                
                
        #lets finalize some of the kwargs
        self.command = self.__set_args(module, 'command', 'c')
        self.ddc_command = self.__set_args(module, 'dragDoubleClickCommand', 'ddc') 
        self.dmc_command = self.__set_args(module, 'dragMenuCommand', 'dmc')
        self.pmc_command =  self.__set_args(module, 'postMenuCommand', 'pmc') 
        
        
        if not 'label' in self.params and not 'l' in self.params:
            self.params['label'] = self.name
            
        key = 'label'
        if 'l' in self.params:
            key = 'l'
        self.params[key] =  self.params[key].replace("_", " ").capitalize()
        
        
        #flush any previous menu instances
        var_name = self.get_variable_name()
        menu_item = None
        if hasattr(module, var_name):
            menu_item = getattr(module, var_name)
            
        if hasattr(module, "IS_ROOT_MENU") and menu_item is not None:
            #If we're rebuiding this, we'll want to nuke the old object,
            try:
                print('deleting : {}'.format(menu_item.menu_instance))
                pm.deleteUI(menu_item.menu_instance)
                print('delete successful')
            except:
                pass
            
        setattr(module, var_name, None)
                

         
    def get_sorted_keys(self):
        """Returns the order to add menu items
        
        If the package contains a user defined order list in the __init__
        This is order is used, with any missing items added to the bottom
        of the list.
        
        If the user didn't define an order, then the order is based the module
        names.
        """
        sorted_children = list(self.children.keys())
        sorted_children.sort()
        if not self.order:   
            return sorted_children
        
        reordered = []
        for name in self.order:
            if name in sorted_children:
                sorted_children.pop(sorted_children.index(name))
                reordered.append(name)
                
        #Items might be missing from the order list, so let's add them to the end of the menu
        if sorted_children:
            item = self.children[sorted_children[0]]
            if not item.is_sub_menu: 
                item.divider = 'Needs Ordering'
            
        return reordered + sorted_children
            
    
    @property
    def is_sub_menu(self):
        return self.is_menu and not self.is_radio_group and self.divider is None
        
  
            
def _build_menu(menu_item, parent):
    """Walks the menu_item structure and builds the maya menu items"""                 
    if menu_item.is_root_menu:
        menu_item.params['parent'] = parent
        if 'p' in menu_item.params:
            menu_item.params.pop('p')
            
        if 'tearOff' not in menu_item.params and 'to' not in menu_item.params:    
            menu_item.params['tearOff'] = True
            
        menu_item.menu_instance = pm.menu(**menu_item.params)  
    else:
        if menu_item.divider is not None:
            pm.menuItem(divider = True, label = menu_item.divider)

        if menu_item.is_menu and not menu_item.is_radio_group and menu_item.divider is not None:
            #sub-folder with dividers don't get any menu item
            pass
        
        elif menu_item.is_radio_group:
            pm.radioMenuItemCollection()
            menu_item.menu_instance = parent
        else:
            if menu_item.is_sub_menu:
                menu_item.params['subMenu'] = True
            menu_item.menu_instance = pm.menuItem(**menu_item.params)
    
    
    ##I attempted to cache each module from MenuItem.parse_module() to a var called "menu_item.module"
    ##but the variable seems to lose scope(?totally bizarre), so I dropped the class variable and opted
    ##to make a local var instead.    
    module = sys.modules[menu_item.relative_path]   
    var_name = menu_item.get_variable_name()

    #Store the menu item in the module, so if we re-run this script we can
    #find the original menu_item.instance and delete it.
    setattr(module, var_name, menu_item)
    
    if menu_item.is_root_menu:
        setattr(module, 'IS_ROOT_MENU', True)        
    
        
    #Build the children items
    invalid_names = []
    for key in menu_item.get_sorted_keys():
        child_item =  menu_item.children[key]
        child_item.parent = menu_item
        if child_item.show:
            _build_menu(child_item, menu_item.menu_instance)
            
            if child_item.is_sub_menu:
                pm.setParent( '..', menu = True )
        else:
            invalid_names.append(key)
            
    #Let's clear out any objects that don't have menu items created for them
    for key in invalid_names:
        menu_item.children.pop(key)
        

    
def _walk_module(parent):
    """Creates a Menu Item Instance for each file/folder found under the parent path"""
    #https://stackoverflow.com/questions/1707709/list-all-the-modules-that-are-part-of-a-python-package
    for importer, modname, ispkg in pkgutil.iter_modules(path=[parent.path]):
        path = r'{}\{}'.format(parent.path, modname)
        relative_path = "{}.{}".format(parent.relative_path, modname)
        menu_item =  MenuItem(modname, path, relative_path, ispkg)
        parent.children[modname] = menu_item
        menu_item.parse_module()
            
    for key in parent.children:
        if parent.children[key].is_menu:
            _walk_module(parent.children[key])
             
        

def get_package_namespace(absolute_path):
    """returns the module name of the given py file."""
    def __Add_Parent_Module(name, path):
        found = False
        parent_module = os.path.join(path.parent, '__init__.py')
    
        if os.path.exists(parent_module):
            path = path.parent
            name = os.path.basename(path) + "." + name
            found = True
    
        return (found, name, path)    

    name = os.path.basename(absolute_path).split('.')[0]
    path = Path(absolute_path)
    loop = True
    count = 0
    while loop and count < 128:
        count += 1
        loop, name, path = __Add_Parent_Module(name, path)
    if count >= 128:
        pm.error('make menu found a bad module path:{}'.format(absolute_path))

    #special case for when someone's getting the path of an __init__ file
    if (name.endswith(".__init__")):
        name = name.removesuffix(".__init__")

    return name
         
        
    
    
def run(menu_bar = None, menu_namespace = ''):
    """Builds a menu based on a python package structure
    
    """
    if not menu_bar:
        menu_bar =  pm.language.melGlobals['gMainWindow']    
    
    if menu_namespace:
        if menu_namespace not in sys.modules:
            try:
                importlib.import_module(menu_namespace)  
            except:
                pm.error("Failed to find menu namespace")
            
        module = sys.modules[menu_namespace]
        path = module.__path__[0]
        
    else:
        try:
            from . import menu
            path = menu.__path__[0]
        except:
            pm.error("Failed to find menu namespace")

    menu_namespace = get_package_namespace(path)    

    package_name = menu_namespace.split('.')[0]
    main_menu = MenuItem(package_name, path, menu_namespace, True)
    main_menu.is_root_menu = True
    main_menu.parse_module()
    main_menu.is_root_menu = True
    
    _walk_module(main_menu)  
    _build_menu(main_menu, menu_bar)
    
    return main_menu