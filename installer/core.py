
import os
import pathlib
import re


bridge_package_dependencies = {
    '1.1.2': {
        'maya': ['wing-carrier>=1.1.1', 'cg3d-maya-core>=0.6.2', 'cg3d-maya-casc>=1.1.2'],
        'casc': ['wing-carrier>=1.1.1', 'cg3d-casc-core>=0.6.0'],
    },
}


class ModuleDefinition(object):
    """A .mod file can have multiple entries. Each definition equates to one entry"""
    
    MODULE_EXPRESSION = r"(?P<action>\+|\-)\s*(MAYAVERSION:(?P<maya_version>\d{4}))?\s*(PLATFORM:(?P<platform>\w+))?\s*(?P<module_name>\w+)\s*(?P<module_version>\d+\.?\d*.?\d*)\s+(?P<module_path>.*)\n(?P<defines>(?P<define>.+(\n?))+)?"
        
    def __init__(self, module_name, module_version,
                 maya_version = '', platform = '',
                 action = '+', module_path = '',
                 defines = [],
                 *args, **kwargs):
        
        self.action = action
        self.module_name = module_name
        self.module_version = module_version
        
        self.module_path = r'.\{0}'.format(self.module_name)
        if module_path:
            self.module_path = module_path

        self.maya_version = maya_version
        if self.maya_version is None:
            self.maya_version = ''
        
        self.platform = platform
        if self.platform is None:
            self.platform = ''
        
        self.defines = defines
        if not self.defines:
            self.defines = []
        
    def __str__(self):
        return_string = '{0} '.format(self.action)
        if self.maya_version:
            return_string += 'MAYAVERSION:{0} '.format(self.maya_version)
            
        if self.platform:
            return_string += 'PLATFORM:{0} '.format(self.platform)
            
        return_string += '{0} {1} {2}\n'.format(self.module_name, self.module_version, self.module_path)
        for define in self.defines:
            if define:
                return_string += '{0}\n'.format(define.rstrip('\n'))
         
        return_string += '\n'    
        return return_string



class ModuleEditor(object):
    """Used to make modules and edit .mod files quickly and easily."""
    
    def __init__(self):
        self._path = None
        self._module_definitions = []
        
    
    def get_install_paths(self, include_missing_paths=False) -> dict:
        """Return a dict of install locations where the key is the entry index"""
        if self._path is None:
            raise FileNotFoundError()
        
        out_paths = {}
        for idx, entry in enumerate(self._module_definitions):
            install_path = pathlib.Path(entry.module_path)
            if install_path.is_absolute():
                out_paths.append(install_path)
            else:
                abs_path = self._path.parent.joinpath(install_path)
                if abs_path.exists() or include_missing_paths:
                    out_paths[idx] = abs_path
                else:
                    print(f"can't find location:{abs_path}")
            
        return out_paths
    
    
    def read_module_definitions(self, path):
        self._module_definitions = []
        read_result = False
        if (os.path.exists(path)):
            self._path = path
            file = open(path, 'r')
            text = file.read()
            file.close()
          
            for result in re.finditer(ModuleDefinition.MODULE_EXPRESSION, text):
                resultDict = result.groupdict()
                if resultDict['defines']:
                    resultDict['defines'] = resultDict['defines'].split("\n")
                    
                definition = ModuleDefinition(**resultDict)
                self._module_definitions.append(definition)
                
            read_result = True
            
        return read_result
      
                        
    def write_module_definitions(self, path=None, relative_paths=True):
        if path is None:
            path = self._path
            
        if path is None:
            raise KeyError("Can't write without a supplied path or reading first")
            
        if relative_paths:
            for entry in self._module_definitions:     
                install_path = pathlib.Path(entry.module_path)
                if not install_path.is_absolute():
                    continue
                
                #OS works better than pathlib, because it
                #lets you get relative in parent locations
                rel_path = os.path.relpath(install_path, path.parent)
                if not rel_path.startswith('.'):
                    rel_path = f".\\{rel_path}"
                    
                entry.module_path = rel_path
                    
        
        file = open(path, 'w')
        for entry in self._module_definitions:
            file.write(str(entry))
        
        file.close()

                           
    def _find_definitions(self, search_list, key, value):
        results = []
        for item in search_list:
            if item.__dict__[key] == value:
                results.append(item)
                
        return results
        
          
    def find_definitions(self, *args, **kwargs):
        result_list = self._module_definitions
        for i in kwargs:
            result_list = self._find_definitions(result_list, i, kwargs[i])
        return result_list
    
    
    def get_definitions(self):
        return tuple(self._module_definitions)
    
    
    def get_definition_by_idx(self, idx):
        return self._module_definitions[idx]
    
    
    def remove_definitions(self, *args, **kwargs):
        """
        removes all definitions that match the input argument values
        example : module_manager_instance.remove_definitions(module_name='generic', platform='win', maya_version='2023')
        
        Returns:
        --------
        list
            the results that were removed from the manager.
        
        """ 
        results = self.find_definitions(**kwargs)
        for result in results:
            self._module_definitions.pop(self._module_definitions.index(result))
            
        return results
    
    
    def remove_definition(self, entry):
        if entry in self._module_definitions:
            self._module_definitions.remove(entry)
                              
                                
    def is_empty(self):
        return len(self._module_definitions) == 0
    
    
    def add_definition(self, definition):
        """

        """
        #TODO: Add some checks to make sure the definition doesn't conflict with an existing definition
        self._module_definitions.append(definition)
        
        
    def get_entry_by_path(self, target_path):
        if self._path is None:
            raise FileNotFoundError("please read modules definitions before getting entry")

        install_paths = self.get_install_paths()
        mod_entry = None
        for idx, mod_path in install_paths.items():
            if mod_path == target_path:
                mod_entry = self.get_definition_by_idx(idx)
                break
            
        return mod_entry