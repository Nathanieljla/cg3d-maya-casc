"""Collect texture paths from Maya shading networks."""

import pathlib

from maya import cmds

from cg3dguru.maya import node_name

from .maya import set_members


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
    export_nodes = export_nodes or []
    materials = {}

    preferred_files = set()
    for export_data in export_nodes:
        object_set = export_data.node() if hasattr(export_data, "node") else export_data
        preferred_files.update(
            member.name()
            for member in set_members(object_set)
            if cmds.nodeType(member.name()) == "file"
        )

    shapes = set()
    for obj in objs or []:
        name = node_name(obj)
        if cmds.nodeType(name) == "mesh":
            shapes.add(name)
        shapes.update(
            cmds.listRelatives(
                name,
                shapes=True,
                noIntermediate=True,
                type="mesh",
                fullPath=True,
            )
            or []
        )

    for shape in shapes:
        shading_groups = cmds.listConnections(shape, type="shadingEngine") or []
        for shading_group in shading_groups:
            shaders = cmds.listConnections(
                shading_group + ".surfaceShader",
                source=True,
                destination=False,
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
                if len(file_nodes) > 1:
                    preferred = [node for node in file_nodes if node in preferred_files]
                    if preferred:
                        file_nodes = preferred

                if len(file_nodes) != 1:
                    cmds.warning(
                        "Found multiple textures for '{}'; skipping it. Add the "
                        "preferred file node to the export set to disambiguate.".format(
                            plug
                        )
                    )
                    continue

                filepath = cmds.getAttr(file_nodes[0] + ".fileTextureName")
                if not filepath:
                    continue
                texture_path = pathlib.Path(filepath)
                if texture_path.suffix.lower() != ".png":
                    png_path = texture_path.with_suffix(".png")
                    if png_path.exists():
                        filepath = str(png_path).replace("\\", "/")

                parents = cmds.listRelatives(shape, parent=True, fullPath=True) or []
                if parents:
                    materials.setdefault(parents[0], set()).add(filepath)

    return {key: sorted(value) for key, value in materials.items()}
