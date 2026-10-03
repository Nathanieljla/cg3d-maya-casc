"""Extract canonical material data from Maya shading networks."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set, Tuple

from maya import cmds

from cg3dguru.maya import node_name

from cg3dcasc_v2.material_data import (
    BaseMaterialData,
    FilamentMaterialData,
    MaterialConverter,
)


_SHADER_ATTR_MAP: Dict[str, List[Tuple[str, str]]] = {
    "aiStandardSurface": [
        ("baseColor", "BaseColor"),
        ("metalness", "Metallic"),
        ("specularColor", "Specular"),
        ("specularRoughness", "Roughness"),
        ("normalCamera", "Normal"),
        ("emissionColor", "EmissiveColor"),
        ("opacity", "Opacity"),
        ("coat", "Coat"),
        ("coatRoughness", "CoatRoughness"),
    ],
    "lambert": [
        ("color", "BaseColor"),
        ("transparency", "Transparency"),
        ("ambientColor", "AmbientOcclusion"),
        ("incandescence", "EmissiveColor"),
        ("normalCamera", "Normal"),
    ],
    "blinn": [
        ("color", "BaseColor"),
        ("transparency", "Transparency"),
        ("ambientColor", "AmbientOcclusion"),
        ("incandescence", "EmissiveColor"),
        ("normalCamera", "Normal"),
        ("specularColor", "Specular"),
        ("eccentricity", "Roughness"),
        ("specularRollOff", "SpecularRollOff"),
    ],
    "phong": [
        ("color", "BaseColor"),
        ("transparency", "Transparency"),
        ("ambientColor", "AmbientOcclusion"),
        ("incandescence", "EmissiveColor"),
        ("normalCamera", "Normal"),
        ("specularColor", "Specular"),
        ("cosinePower", "Roughness"),
    ],
    "phongE": [
        ("color", "BaseColor"),
        ("transparency", "Transparency"),
        ("ambientColor", "AmbientOcclusion"),
        ("incandescence", "EmissiveColor"),
        ("normalCamera", "Normal"),
        ("highlightSize", "Roughness"),
        ("roughness", "SpecularRollOff"),
    ],
}


class MayaMaterialData(BaseMaterialData):
    """Canonical material values extracted from Maya mesh nodes."""

    SHADER_ATTR_MAP = _SHADER_ATTR_MAP

    @classmethod
    def from_mesh(cls, mesh_objs: Any) -> "MayaMaterialData":
        if not isinstance(mesh_objs, (list, tuple, set)):
            mesh_objs = [mesh_objs]

        data = cls()
        shapes = []
        for obj in mesh_objs:
            obj_name = node_name(obj)
            if cmds.nodeType(obj_name) == "mesh":
                shapes.append(obj_name)
            else:
                shapes.extend(
                    cmds.listRelatives(
                        obj_name,
                        shapes=True,
                        noIntermediate=True,
                        type="mesh",
                        fullPath=True,
                    )
                    or []
                )

        shapes = sorted(set(shapes))
        if not shapes:
            cmds.warning("MayaMaterialData: no mesh shapes were found.")
            return data

        parents = {
            parent
            for shape in shapes
            for parent in (cmds.listRelatives(shape, parent=True, fullPath=True) or [])
        }
        data.mesh_name = (
            next(iter(parents)) if len(parents) == 1 else "|".join(sorted(parents))
        )

        seen_shaders: Set[str] = set()
        for shape in shapes:
            for shading_group in cmds.listConnections(
                shape, type="shadingEngine"
            ) or []:
                shaders = cmds.listConnections(
                    shading_group + ".surfaceShader",
                    source=True,
                    destination=False,
                ) or []
                for shader in shaders:
                    if shader in seen_shaders:
                        continue
                    seen_shaders.add(shader)
                    attributes = cls._extract_shader(shader)
                    if attributes:
                        data.materials[shader] = attributes
        return data

    @classmethod
    def _extract_shader(
        cls, shader: str
    ) -> Optional[Dict[str, Dict[str, Any]]]:
        shader_type = cmds.nodeType(shader)
        attribute_map = cls.SHADER_ATTR_MAP.get(shader_type)
        if attribute_map is None:
            cmds.warning(
                "MayaMaterialData: unsupported shader type '{}' on '{}'.".format(
                    shader_type, shader
                )
            )
            return None

        attributes = {}
        for maya_attribute, canonical_name in attribute_map:
            if not cmds.attributeQuery(maya_attribute, node=shader, exists=True):
                continue
            entry = cls._read_attribute(shader, maya_attribute)
            if entry is not None:
                attributes[canonical_name] = entry
        return attributes

    @classmethod
    def _read_attribute(
        cls, shader: str, maya_attribute: str
    ) -> Optional[Dict[str, Any]]:
        plug = "{}.{}".format(shader, maya_attribute)
        texture_path = cls._find_texture(plug)
        if texture_path:
            return {"type": "texture", "value": [texture_path]}
        try:
            return cls._constant_entry(cmds.getAttr(plug))
        except (RuntimeError, ValueError, TypeError):
            return None

    @staticmethod
    def _find_texture(plug: str) -> Optional[str]:
        connections = cmds.listConnections(
            plug, source=True, destination=False
        ) or []
        file_nodes = {node for node in connections if cmds.nodeType(node) == "file"}
        for connection in connections:
            file_nodes.update(
                node
                for node in (cmds.listHistory(connection, pruneDagObjects=True) or [])
                if cmds.nodeType(node) == "file"
            )
        if not file_nodes:
            return None
        filepath = cmds.getAttr(sorted(file_nodes)[0] + ".fileTextureName")
        return filepath.replace("\\", "/") if filepath else None

    @staticmethod
    def _constant_entry(raw: Any) -> Optional[Dict[str, Any]]:
        if raw is None:
            return None
        if (
            isinstance(raw, (tuple, list))
            and len(raw) == 1
            and isinstance(raw[0], (tuple, list))
        ):
            raw = raw[0]
        if isinstance(raw, bool):
            return {"type": "scalar", "value": 1.0 if raw else 0.0}
        if isinstance(raw, (tuple, list)):
            values = [float(value) for value in raw]
            if len(values) == 1:
                return {"type": "scalar", "value": values[0]}
            return {"type": "vector", "value": values}
        if isinstance(raw, (int, float)):
            return {"type": "scalar", "value": float(raw)}
        return None


MaterialConverter.register(
    MayaMaterialData,
    FilamentMaterialData,
    dict(FilamentMaterialData.CANONICAL_TO_FILAMENT),
)
