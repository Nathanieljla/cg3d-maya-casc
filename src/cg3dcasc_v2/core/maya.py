"""Small Maya helpers shared by the native Maya Cascadeur bridge."""

from maya import cmds
from maya.api import OpenMaya as om

from cg3dguru.maya import Attribute, Node, as_attribute, as_node, node_name, nodes


def names(values):
    return [node_name(value) for value in (values or [])]


def ls(*args, **kwargs):
    return nodes(cmds.ls(*args, **kwargs) or [])


def node_type(node):
    return cmds.nodeType(node_name(node))


def is_type(node, *types):
    return node_type(node) in types


def parent(node):
    result = cmds.listRelatives(node_name(node), parent=True, fullPath=True) or []
    return Node(result[0]) if result else None


def top_parent(node):
    current = as_node(node)
    current_parent = parent(current)
    while current_parent is not None:
        current = current_parent
        current_parent = parent(current)
    return current


def children(node, **kwargs):
    kwargs.setdefault("children", True)
    kwargs.setdefault("fullPath", True)
    return nodes(cmds.listRelatives(node_name(node), **kwargs) or [])


def descendants(values, **kwargs):
    value_names = names(values)
    if not value_names:
        return []
    kwargs.setdefault("allDescendents", True)
    kwargs.setdefault("fullPath", True)
    return nodes(cmds.listRelatives(value_names, **kwargs) or [])


def world_matrix(node):
    return om.MMatrix(cmds.xform(node_name(node), query=True, worldSpace=True, matrix=True))


def set_world_matrix(node, matrix):
    cmds.xform(node_name(node), worldSpace=True, matrix=list(matrix))


def rename(node, name):
    return Node(cmds.rename(node_name(node), name))


def set_members(object_set):
    return nodes(cmds.sets(node_name(object_set), query=True) or [])


def add_set_members(object_set, values):
    value_names = names(values)
    if value_names:
        cmds.sets(value_names, addElement=node_name(object_set))


def remove_set_members(object_set, values):
    value_names = names(values)
    if value_names:
        cmds.sets(value_names, remove=node_name(object_set))


def connect(source, destination, force=True):
    cmds.connectAttr(str(source), str(destination), force=force)


def disconnect(source, destination):
    if cmds.isConnected(str(source), str(destination)):
        cmds.disconnectAttr(str(source), str(destination))


def multi_indices(attribute):
    return cmds.getAttr(str(attribute), multiIndices=True) or []


def multi_elements(attribute):
    attribute = as_attribute(attribute)
    return [attribute[index] for index in multi_indices(attribute)]
