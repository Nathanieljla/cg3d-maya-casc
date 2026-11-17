"""Shared Maya scene queries for Cascadeur import and export."""

from maya import cmds

import cg3dguru.udata
from cg3dguru.maya import Node, node_name, nodes

from . import client
from .maya import ls
from .udata import CascExportData, QRigData


def get_character_node(export_data):
    """Return the HIK character node associated with an export data block."""
    qrig_data = QRigData.get_data(export_data.node())
    if not qrig_data:
        return None

    inputs = qrig_data.characterNode.inputs()
    if not inputs:
        cmds.error(
            "Cascadeur export data wasn't provided with an HIK character node."
        )
    return inputs[0]


def get_joint_skin_clusters(joints):
    """Given joints, return their connected skin clusters."""
    clusters = set()
    for joint in joints:
        connected = cmds.listConnections(
            "{}.worldMatrix".format(node_name(joint)),
            source=False,
            destination=True,
            type="skinCluster",
        ) or []
        clusters.update(nodes(connected))
    return clusters


def get_skin_cluster_joints(skin_clusters):
    """Given skin clusters, return their influences."""
    joints = set()
    for skin_cluster in skin_clusters:
        joints.update(
            nodes(cmds.skinCluster(node_name(skin_cluster), query=True, influence=True) or [])
        )
    return joints


def get_skin_cluster_meshes(skin_clusters):
    """Given skin clusters, return their associated mesh shapes."""
    meshes = set()
    for cluster in skin_clusters:
        for geometry in cmds.skinCluster(
            node_name(cluster), geometry=True, query=True
        ) or []:
            if cmds.nodeType(geometry) == "mesh":
                long_names = cmds.ls(geometry, long=True) or [geometry]
                meshes.add(Node(long_names[0]))
                continue
            shapes = cmds.listRelatives(
                geometry,
                shapes=True,
                noIntermediate=True,
                type="mesh",
                fullPath=True,
            ) or []
            meshes.update(nodes(shapes))
    return meshes


def get_mesh_cluster_mappings():
    """Return a global mapping of mesh-to-clusters and cluster-to-meshes."""
    mapping = {}
    for cluster in ls(type="skinCluster"):
        meshes = get_skin_cluster_meshes([cluster])
        mapping[cluster] = set(meshes)
        for mesh in meshes:
            mapping.setdefault(mesh, set()).add(cluster)
    return mapping


def get_mesh_skin_clusters(meshes):
    mapping = get_mesh_cluster_mappings()
    clusters = set()
    for mesh in meshes:
        clusters.update(mapping.get(mesh, set()))
    return clusters


def get_non_intermediate_mesh_shapes(node):
    return nodes(
        cmds.listRelatives(
            node_name(node),
            shapes=True,
            noIntermediate=True,
            type="mesh",
            fullPath=True,
        )
        or []
    )


def get_skinned_data_sets(input_list):
    """Sort nodes into joints, meshes, skin clusters, and transforms."""
    joints = set()
    meshes = set()
    skin_clusters = set()
    transforms = set()

    for value in input_list:
        node = value if isinstance(value, Node) else Node(value)
        node_kind = cmds.nodeType(node_name(node))
        if node_kind == "joint":
            joints.add(node)
        elif node_kind == "mesh":
            meshes.add(node)
        elif node_kind == "skinCluster":
            skin_clusters.add(node)
        elif node_kind == "transform":
            shapes = get_non_intermediate_mesh_shapes(node)
            if len(shapes) > 1:
                cmds.error(
                    "Skipping '{}'. Multiple mesh shapes aren't supported.".format(
                        node.name()
                    )
                )
            if shapes:
                meshes.add(shapes[0])
            else:
                transforms.add(node)
        else:
            cmds.warning("Cascadeur export: ignoring {}".format(node.name()))

    return joints, meshes, skin_clusters, transforms


def update_skinned_data_sets(joints, meshes, skin_clusters, transforms):
    """Add dependencies implied by each of the supplied node sets."""
    skin_clusters.update(get_mesh_skin_clusters(meshes))
    skin_clusters.update(get_joint_skin_clusters(joints))
    joints.update(get_skin_cluster_joints(skin_clusters))
    meshes.update(get_skin_cluster_meshes(skin_clusters))


def get_selected_export_nodes():
    selected_sets = ls(selection=True, type="objectSet")
    return cg3dguru.udata.Utils.get_nodes_with_data(
        selected_sets, data_class=CascExportData
    )


def get_all_export_nodes():
    return cg3dguru.udata.Utils.get_nodes_with_data(
        ls(type="objectSet"), data_class=CascExportData
    )


def get_export_nodes():
    selected_sets = get_selected_export_nodes()
    return selected_sets if selected_sets else get_all_export_nodes()


def get_all_set_ids():
    client.data_to_casc([data.cscDataId.get() for data in get_all_export_nodes()])


def get_selected_set_ids():
    client.data_to_casc(
        [data.cscDataId.get() for data in get_selected_export_nodes()]
    )


def get_coord_system():
    client.data_to_casc(cmds.upAxis(query=True, axis=True))


def run():
    pass
