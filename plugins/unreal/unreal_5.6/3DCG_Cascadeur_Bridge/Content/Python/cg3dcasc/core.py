import unreal
import json

class MaterialData:
    """
    Utility class to extract and store material logic from a skeletal mesh,
    including traversing down material graph attributes (BaseColor, Roughness, etc.)
    and correctly querying localized parameters for Material Instances.
    """
    def __init__(self, mesh_name):
        self.mesh_name = mesh_name
        self.materials = {}

    @classmethod
    def from_skel_mesh(cls, skel_mesh):
        if not skel_mesh or not isinstance(skel_mesh, unreal.SkeletalMesh):
            unreal.log_error("Invalid skeletal mesh provided to MaterialData")
            return None
            
        data = cls(skel_mesh.get_name())
        
        # In skeletal meshes, materials are stored in the 'materials' array 
        # (list of SkeletalMaterial objects)
        for skel_mat in skel_mesh.materials:
            mat_interface = skel_mat.material_interface
            if mat_interface:
                mat_name = mat_interface.get_name()
                data.materials[mat_name] = cls._extract_attributes(mat_interface)
                
        return data

    @classmethod
    def _extract_attributes(cls, material_interface):
        attributes = {}
        
        properties_to_check = {
            "BaseColor": unreal.MaterialProperty.MP_BASE_COLOR,
            "Metallic": unreal.MaterialProperty.MP_METALLIC,
            "Specular": unreal.MaterialProperty.MP_SPECULAR,
            "Roughness": unreal.MaterialProperty.MP_ROUGHNESS,
            "Normal": unreal.MaterialProperty.MP_NORMAL,
            "EmissiveColor": unreal.MaterialProperty.MP_EMISSIVE_COLOR,
            "Opacity": unreal.MaterialProperty.MP_OPACITY,
            "AmbientOcclusion": unreal.MaterialProperty.MP_AMBIENT_OCCLUSION,
        }
        
        base_mat = material_interface.get_base_material()
        if not base_mat:
            return attributes
            
        for attr_name, mat_prop in properties_to_check.items():
            input_node = unreal.MaterialEditingLibrary.get_material_property_input_node(base_mat, mat_prop)
            if not input_node:
                continue
                
            # Traverse graph for textures and constants
            textures, constants = cls._traverse_node(input_node, material_interface, set())
            
            # Formatting as requested: list of textures if available. Else single constant if available.
            if textures:
                attributes[attr_name] = list(textures)
            elif constants:
                attributes[attr_name] = constants[0]
                
        return attributes

    @classmethod
    def _traverse_node(cls, node, mat_interface, visited):
        textures = set()
        constants = []
        
        if not node or node in visited:
            return textures, constants
            
        visited.add(node)
        
        classname = type(node).__name__
        
        # 1. Is it a Parameter Override node?
        if hasattr(node, 'parameter_name'):
            if "Texture" in classname:
                tex_val = cls._get_texture_val(mat_interface, node)
                if tex_val: textures.add(tex_val)
            elif "Vector" in classname:
                constants.append(cls._get_vector_val(mat_interface, node))
            elif "Scalar" in classname:
                constants.append(cls._get_scalar_val(mat_interface, node))
                
        # 2. Or is it a hardcoded Texture sample?
        elif "Texture" in classname and hasattr(node, 'texture'):
            if node.texture:
                textures.add(node.texture.get_path_name())
                
        # 3. Or a hardcoded Constant?
        elif "Constant4Vector" in classname and hasattr(node, 'constant'):
            constants.append([node.constant.r, node.constant.g, node.constant.b, node.constant.a])
        elif "Constant3Vector" in classname and hasattr(node, 'constant'):
            constants.append([node.constant.r, node.constant.g, node.constant.b])
        elif "Constant2Vector" in classname:
            constants.append([getattr(node, 'r', 0.0), getattr(node, 'g', 0.0)])
        elif "Constant" == classname or "Constant" in classname:
            if hasattr(node, 'r'): constants.append(node.r)
            
        # 4. Recurse backwards up the node chain
        # Look for any ExpressionInput properties to traverse backwards
        try:
            for prop_name in dir(node):
                if prop_name.startswith("__"): continue
                
                try:
                    prop_val = getattr(node, prop_name)
                    # ExpressionInput is a built-in struct that contains an expression node
                    if "ExpressionInput" in type(prop_val).__name__ or hasattr(prop_val, "expression"):
                        if hasattr(prop_val, "expression") and prop_val.expression:
                            sub_tex, sub_const = cls._traverse_node(prop_val.expression, mat_interface, visited)
                            textures.update(sub_tex)
                            constants.extend(sub_const)
                except Exception:
                    pass
        except Exception:
            pass
            
        return textures, constants

    @classmethod
    def _get_scalar_val(cls, mat_inst, node):
        if isinstance(mat_inst, unreal.MaterialInstance):
            try:
                return unreal.MaterialEditingLibrary.get_material_instance_scalar_parameter_value(mat_inst, node.parameter_name)
            except Exception:
                pass
        return node.default_value

    @classmethod
    def _get_vector_val(cls, mat_inst, node):
        if isinstance(mat_inst, unreal.MaterialInstance):
            try:
                val = unreal.MaterialEditingLibrary.get_material_instance_vector_parameter_value(mat_inst, node.parameter_name)
                return [val.r, val.g, val.b, val.a]
            except Exception:
                pass
        val = node.default_value
        return [val.r, val.g, val.b, val.a]

    @classmethod
    def _get_texture_val(cls, mat_inst, node):
        if isinstance(mat_inst, unreal.MaterialInstance):
            try:
                tex = unreal.MaterialEditingLibrary.get_material_instance_texture_parameter_value(mat_inst, node.parameter_name)
                if tex: return tex.get_path_name()
            except Exception:
                pass
        if node.texture:
            return node.texture.get_path_name()
        return None

    def to_json(self):
        """Returns the collected material attributes data as formatted json."""
        return json.dumps({
            "mesh_name": self.mesh_name,
            "materials": self.materials
        }, indent=4)
