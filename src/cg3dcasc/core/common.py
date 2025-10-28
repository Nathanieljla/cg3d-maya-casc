
import json
import tempfile
import os
import pathlib

import pymel.core as pm
from . import hik

import wingcarrier.pigeons
import cg3dguru.udata
import cg3dguru.animation.fbx
import cg3dguru.utils

from .udata import *
from . import client
from . import command_port
from . import server


def get_character_node(export_data):
    """Return any HIK character node associated with the export_data"""
    
    qrig_data = QRigData.get_data(export_data.node())
    character_node = None
    if qrig_data:
        inputs = qrig_data.characterNode.inputs()
        if not qrig_data.characterNode.inputs():
            pm.error("ERROR: cascadeur.core.export: qrig_data wasn't provided with HIK Character node")
        else:
            character_node = inputs[0]
            
    return character_node



def get_joint_skin_clusters(joints):
    """Given a list of joints, return a set of associated skinClusters"""

    clusters = set()
    for joint in joints:
        world_matrix = joint.attr('worldMatrix')
        outputs = world_matrix.outputs()
        for output in outputs:
            if output.type() == 'skinCluster' and output not in clusters:
                clusters.add(output)

    return clusters
                
                
def get_skin_cluster_joints(skin_clusters):
    """Given a list of skinClusters, return a set of associated joints"""
    joint_set = set()
    for skin_cluster in skin_clusters:
        temp_set = set(skin_cluster.matrix.inputs())
        joint_set.update(temp_set)
        
    return joint_set



def get_skin_cluster_meshes(skin_clusters):
    """Given a list of skinClusters, return a set of associated meshes"""
    meshes = set()
    for cluster in skin_clusters:
        meshes.update(
            pm.animation.skinCluster(cluster, geometry=True, query=True)
        )

    return meshes
    
    
def get_mesh_cluster_mappings() -> dict:
    """Return a global mapping of mesh:clusters and cluster:meshes"""
    mapping = {}
    for cluster in pm.ls(type='skinCluster'):
        meshes = pm.animation.skinCluster(cluster, geometry=True, query=True)
        mapping[cluster] = set(meshes)

        for mesh in meshes:
            mapping.setdefault(mesh, set()).add(cluster)

    return mapping


def get_mesh_skin_clusters(meshes):
    """Given a list of meshes, return a set of all associated skinClusters"""
    mesh_clusters = get_mesh_cluster_mappings()
    clusters = set()
    for mesh in meshes:
        if mesh in mesh_clusters:
            clusters.update(mesh_clusters[mesh])
            
    return clusters

def get_non_intermediate_mesh_shapes(node):
    shapes = [shape for shape in node.getShapes() if not shape.intermediateObject.get() and isinstance(shape, pm.nodetypes.Mesh)]
    return shapes
    

def get_skinned_data_sets(input_list):
    """Sort the input list into joints, meshes, skin_clusters, and transforms"""
    joints = set()
    meshes = set()
    skin_clusters = set()
    transforms = set()

    #organize our exportExtra nodes into types
    for node in input_list:
        if isinstance(node, pm.nodetypes.Joint):
            joints.add(node)
        elif isinstance(node, pm.nodetypes.Mesh):
            meshes.add(node)
        elif isinstance(node, pm.nodetypes.SkinCluster):
            skin_clusters.add(node)
        elif isinstance(node, pm.nodetypes.Transform):
            shapes = get_non_intermediate_mesh_shapes(node)
            if len(shapes) > 1:
                #What's this case and do we want to skip it?
                pm.error(f"Skipping '{node.name()}'. Tool can't handle multiple mesh shapes. Please contact 3dcg guru for support.")
            if not shapes:
                transforms.add(node)
            else:
                meshes.add(shapes[0])
        else:
            pm.warning('Cascaduer Export: Ignoring object {}'.format(node.name()))
            
    return (joints, meshes, skin_clusters, transforms)


def update_skinned_data_sets(joints, meshes, skin_clusters, transforms):
    """Update each input set with any dependencies from the other sets"""
    
    skin_clusters.update(
        get_mesh_skin_clusters(meshes)
    )
    
    skin_clusters.update(
        get_joint_skin_clusters(joints)
    )
    
    joints.update(
        get_skin_cluster_joints(skin_clusters)
    )
    
    meshes.update(
        get_skin_cluster_meshes(skin_clusters)
    )
    

def get_selected_export_nodes():
    selected_sets = pm.ls(sl=True, type='objectSet')
    return cg3dguru.udata.Utils.get_nodes_with_data(selected_sets, data_class=CascExportData)


def get_all_export_nodes():
    all_sets = pm.ls(type='objectSet')
    return cg3dguru.udata.Utils.get_nodes_with_data(all_sets, data_class=CascExportData)
    

def get_export_nodes():
    selected_sets = get_selected_export_nodes()
    return selected_sets if selected_sets else get_all_export_nodes()


def get_all_set_ids():
    data = []
    export_sets = get_all_export_nodes()
    data = [e.cscDataId.get() for e in export_sets]

    client.data_to_casc(data)
    
    
def get_selected_set_ids():
    data = []
    export_sets = get_selected_export_nodes()
    data = [e.cscDataId.get() for e in export_sets]

    client.data_to_casc(data)    
    

def get_coord_system():
    data = pm.cmds.upAxis(q=True, axis=True)
    client.data_to_casc(data)
            
def run():
    pass

