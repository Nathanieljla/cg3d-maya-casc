"""Serialize Maya materials for Cascadeur's official Material behaviour."""

from __future__ import annotations

import os
import pathlib
import shutil

from maya import cmds
from maya.api import OpenMaya as om

from cg3dguru.maya import node_name

from cg3dcasc.material_data import FilamentMaterialData, MaterialConverter

from .maya import set_members
from .maya_material_data import MayaMaterialData


MATERIAL_INFO_FILE = "material_info.json"
MATERIAL_INFO_VERSION = 1
SUPPORTED_TEXTURE_EXTENSIONS = {".jpg", ".jpeg", ".png"}


_CASCADEUR_PROPERTIES = {
    "baseColor": ("base_color", "base_color_map"),
    "emissive": ("emissive_color", "emissive_color_map"),
    "roughness": ("roughness", "roughness_map"),
    "metallic": ("metallic", "metallic_map"),
    "reflectance": ("reflectance", "reflectance_map"),
    "ambientOcclusion": ("ambient_occlusion", "ambient_occlusion_map"),
    "normal": (None, "normal_map"),
    "clearCoat": ("clear_coat", None),
    "clearCoatRoughness": ("clear_coat_roughness", None),
}

_MAP_DEFAULTS = {
    "base_color_map": {"base_color": [1.0, 1.0, 1.0]},
    "emissive_color_map": {"emissive_color": [1.0, 1.0, 1.0]},
    "roughness_map": {"roughness": 1.0, "roughness_channel": 0},
    "metallic_map": {"metallic": 1.0, "metallic_channel": 0},
    "reflectance_map": {"reflectance": 1.0, "reflectance_channel": 0},
    "ambient_occlusion_map": {
        "ambient_occlusion": 1.0,
        "ambient_occlusion_channel": 0,
    },
}

_MAP_CHANNEL_PROPERTIES = {
    "roughness_map": "roughness_channel",
    "metallic_map": "metallic_channel",
    "reflectance_map": "reflectance_channel",
    "ambient_occlusion_map": "ambient_occlusion_channel",
}


def _slash(path):
    return str(path).replace("\\", "/")


def _leaf(path):
    return str(path).rsplit("|", 1)[-1]


def _resolved_texture_path(filepath):
    expanded = os.path.expandvars(os.path.expanduser(str(filepath)))
    path = pathlib.Path(expanded)

    # Maya commonly stores project-relative file nodes with a leading slash,
    # for example /sourceimages/albedo.png. On Windows pathlib considers that
    # drive-rooted, even though Maya means "relative to the current project".
    project_relative = not path.is_absolute()
    if os.name == "nt":
        windows_path = pathlib.PureWindowsPath(expanded)
        project_relative = project_relative or (
            bool(windows_path.root) and not bool(windows_path.drive)
        )

    if project_relative:
        relative_path = expanded.lstrip("/\\")
        try:
            path = pathlib.Path(cmds.workspace(expandName=relative_path))
            if not path.is_absolute():
                workspace_root = pathlib.Path(
                    cmds.workspace(query=True, rootDirectory=True)
                )
                path = workspace_root.joinpath(relative_path)
        except RuntimeError:
            path = pathlib.Path(relative_path)
    return path


def convert_texture(source, destination=None):
    """Convert an image to PNG with Maya's own image/Qt support."""
    source = pathlib.Path(source)
    destination = (
        pathlib.Path(destination) if destination else source.with_suffix(".png")
    )
    try:
        from maya import OpenMayaUI as omui

        if int(cmds.about(version=True)) < 2025:
            from PySide2.QtGui import QPixmap
            from shiboken2 import wrapInstance
        else:
            from PySide6.QtGui import QPixmap
            from shiboken6 import wrapInstance

        pointer = omui.MQtUtil.createPixmap(str(source))
        if not pointer:
            raise ValueError("Maya could not read '{}'".format(source))
        pixmap = wrapInstance(int(pointer), QPixmap)
        if pixmap.isNull() or not pixmap.toImage().save(str(destination), "PNG"):
            raise ValueError("Maya could not convert '{}'".format(source))
        return destination
    except (ImportError, OSError, RuntimeError, ValueError) as error:
        cmds.warning(str(error))
        return None


def prepare_texture_path(filepath, texture_location=""):
    """Resolve, optionally copy, and optionally convert a referenced image."""
    source = _resolved_texture_path(filepath)
    if not source.is_file():
        cmds.warning("Texture file does not exist: '{}'".format(source))
        return _slash(source.resolve())

    if not texture_location:
        return _slash(source.resolve())

    destination_directory = _resolved_texture_path(texture_location)
    try:
        destination_directory.mkdir(parents=True, exist_ok=True)
        if not destination_directory.is_dir():
            raise OSError("The texture location is not a directory")
    except OSError as error:
        cmds.warning(
            "Invalid Cascadeur texture location '{}': {}. Using the source "
            "texture instead.".format(destination_directory, error)
        )
        return _slash(source.resolve())

    if source.suffix.lower() in SUPPORTED_TEXTURE_EXTENSIONS:
        destination = destination_directory.joinpath(source.name)
        try:
            if not destination.exists() and source.resolve() != destination.resolve():
                shutil.copy2(str(source), str(destination))
        except OSError as error:
            cmds.warning(
                "Could not copy texture '{}' to '{}': {}".format(
                    source, destination, error
                )
            )
            return _slash(source.resolve())
    else:
        destination = destination_directory.joinpath(source.stem + ".png")
        if not destination.exists() and convert_texture(source, destination) is None:
            return _slash(source.resolve())

    return _slash(destination.resolve())


def _mesh_shapes(objs):
    shapes = set()
    for obj in objs or []:
        name = node_name(obj)
        if not cmds.objExists(name):
            continue
        if cmds.nodeType(name) == "mesh":
            candidates = [name]
        else:
            candidates = cmds.listRelatives(
                name,
                allDescendents=True,
                shapes=True,
                noIntermediate=True,
                type="mesh",
                fullPath=True,
            ) or []
            candidates.extend(
                cmds.listRelatives(
                    name,
                    shapes=True,
                    noIntermediate=True,
                    type="mesh",
                    fullPath=True,
                )
                or []
            )
        for shape in candidates:
            try:
                selection = om.MSelectionList()
                selection.add(shape)
                dag_node = om.MFnDagNode(selection.getDependNode(0))
                shapes.update(path.fullPathName() for path in dag_node.getAllPaths())
            except RuntimeError:
                shapes.update(cmds.ls(shape, long=True, allPaths=True) or [shape])
    return sorted(shapes)


def _constant(value, property_name):
    if isinstance(value, (tuple, list)):
        values = [float(item) for item in value]
        if property_name in {"reflectance", "ambient_occlusion"}:
            return sum(values[:3]) / min(len(values), 3) if values else 0.0
        if len(values) >= 3:
            return values[:3]
        return values[0] if values else 0.0
    return float(value)


def _cascadeur_material(attributes, texture_location):
    result = {}
    for source_name, entry in attributes.items():
        cascadeur_names = _CASCADEUR_PROPERTIES.get(source_name)
        if not cascadeur_names:
            continue
        value_name, map_name = cascadeur_names
        entry_type = entry.get("type")
        entry_value = entry.get("value")
        if entry_type == "texture" and map_name and entry_value:
            texture_path = entry_value[0] if isinstance(entry_value, list) else entry_value
            result[map_name] = prepare_texture_path(
                texture_path, texture_location
            )
            result.update(_MAP_DEFAULTS.get(map_name, {}))
            channel_property = _MAP_CHANNEL_PROPERTIES.get(map_name)
            if channel_property:
                result[channel_property] = int(entry.get("channel", 0))
        elif entry_type in {"scalar", "vector"} and value_name:
            result[value_name] = _constant(entry_value, value_name)
    return result


def build_export_data(export_data, objs):
    """Build one Reference-mode material payload for an export set."""
    converter = MaterialConverter.get(MayaMaterialData, FilamentMaterialData)
    if converter is None:
        raise RuntimeError("Maya-to-Cascadeur material converter is not registered")

    texture_location = export_data.textureLocation.get() or ""
    meshes = {}
    for shape in _mesh_shapes(objs):
        parents = cmds.listRelatives(shape, parent=True, fullPath=True) or []
        if not parents:
            continue
        transform = parents[0]
        mesh_entry = meshes.setdefault(
            transform,
            {
                "path": transform,
                "name": _leaf(transform),
                "shapes": [],
                "materials": [],
            },
        )
        mesh_entry["shapes"].append(_leaf(shape))

        maya_data = MayaMaterialData.from_mesh(shape)
        cascadeur_data, report = converter.convert(maya_data)
        for warning in report.warnings:
            cmds.warning(warning)
        known_materials = {item["name"] for item in mesh_entry["materials"]}
        for material_name, attributes in cascadeur_data.materials.items():
            if material_name in known_materials:
                continue
            mesh_entry["materials"].append(
                {
                    "slot": len(mesh_entry["materials"]),
                    "name": material_name,
                    "properties": _cascadeur_material(
                        attributes, texture_location
                    ),
                }
            )
            known_materials.add(material_name)

    object_set = export_data.node()
    return {
        "id": str(export_data.cscDataId.get()),
        "set_name": object_set.name().split(":")[-1],
        "meshes": [meshes[key] for key in sorted(meshes)],
    }


def material_document(exports):
    """Return the versioned JSON document consumed by Cascadeur."""
    return {"version": MATERIAL_INFO_VERSION, "exports": exports}


# Kept for the Utils > Convert Textures command. The bridge export itself uses
# build_export_data(), which records official materials and their mesh slots.
def _file_nodes_upstream(plug):
    direct = cmds.listConnections(
        plug, source=True, destination=False, skipConversionNodes=False
    ) or []
    found = {node for node in direct if cmds.nodeType(node) == "file"}
    for node in direct:
        found.update(
            history_node
            for history_node in (cmds.listHistory(node, pruneDagObjects=True) or [])
            if cmds.nodeType(history_node) == "file"
        )
    return sorted(found)


def get_textures(objs, export_nodes=None):
    """Return legacy mesh-to-base-color paths for the conversion utility."""
    export_nodes = export_nodes or []
    preferred_files = set()
    for export_data in export_nodes:
        object_set = export_data.node() if hasattr(export_data, "node") else export_data
        preferred_files.update(
            member.name()
            for member in set_members(object_set)
            if cmds.nodeType(member.name()) == "file"
        )

    found = {}
    for shape in _mesh_shapes(objs):
        for shading_group in cmds.listConnections(shape, type="shadingEngine") or []:
            shaders = cmds.listConnections(
                shading_group + ".surfaceShader", source=True, destination=False
            ) or []
            for shader in shaders:
                color_attribute = next(
                    (
                        attribute
                        for attribute in ("color", "diffuse", "baseColor")
                        if cmds.attributeQuery(attribute, node=shader, exists=True)
                    ),
                    None,
                )
                if not color_attribute:
                    continue
                plug = "{}.{}".format(shader, color_attribute)
                file_nodes = _file_nodes_upstream(plug)
                preferred = [item for item in file_nodes if item in preferred_files]
                if preferred:
                    file_nodes = preferred
                if len(file_nodes) != 1:
                    continue
                filepath = cmds.getAttr(file_nodes[0] + ".fileTextureName")
                parents = cmds.listRelatives(shape, parent=True, fullPath=True) or []
                if filepath and parents:
                    found.setdefault(parents[0], set()).add(filepath)
    return {key: sorted(value) for key, value in found.items()}
