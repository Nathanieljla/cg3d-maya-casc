from pathlib import Path

from maya import OpenMayaUI as omui 
from shiboken2 import wrapInstance

import pymel.core as pm
from PySide2.QtWidgets import *
from PySide2.QtGui import * 

import cg3dguru.ui
from . import exchange
from .udata import *

CLONE_PREFIX = 'CASC'



def wait_cursor(func):
    def wrapper(*args, **kwargs):
        pm.waitCursor(state=True)
        result = None
        try:
            result = func(*args, **kwargs)
        except Exception as e:
            raise e
        else:
            return result
        finally:
            pm.waitCursor(state=False)

    return wrapper   



def _make_joint_hierarchy(joint, parent, joint_hierarchy):
    """Build a dict of parent keys, with children values
    
    This skips anything in the hierarchy that isn't a jointe
    """
    if parent is None:
        joint_hierarchy.setdefault(None, []).append(joint)
    elif isinstance(parent, pm.nodetypes.Joint):
        joint_hierarchy.setdefault(parent, []).append(joint)
    else:
        _make_joint_hierarchy(joint, parent.getParent(), joint_hierarchy)
        
        
        
def _map_clone(org, clone, mapping):
    mapping[org] = clone
    mapping[clone] = org
    
    ProxyData.add_data(clone)
    org.message >> clone.proxySource    
        
        
        
def _clone_joints(joint_list, parent, joint_hierarchy, clone_pairing):
    for joint in joint_list:
        new_joint = pm.general.createNode('joint', name=f"{CLONE_PREFIX}:{joint.name()}", parent =parent, skipSelect=True)
        _map_clone(joint, new_joint, clone_pairing)
        new_joint.radius.set(joint.radius.get())
        new_joint.setMatrix(joint.getMatrix(worldSpace=True), worldSpace=True)
        
        children = joint_hierarchy.get(joint, [])
        if children:
            _clone_joints(children, new_joint, joint_hierarchy, clone_pairing)
            
          
            
def _get_index_mapping(source_cluster, cloned_cluster, clone_pairing):
    cloned_indices = {element.inputs()[0]: element.index() for element in cloned_cluster.matrix}
    
    index_mapping = {}
    for element in source_cluster.matrix:
        index_mapping[element.index()] = cloned_indices[clone_pairing[element.inputs()[0]]]
        
    return index_mapping
    
            
            
def _clone_meshes(meshes, mesh_parent, skinned_parent, clone_pairing):
    mesh_cluster_mapping = exchange.get_mesh_cluster_mappings()
    
    for mesh in meshes:
        name = f"{CLONE_PREFIX}:{mesh.getParent().name()}"

        clone = pm.duplicate(mesh, name=name)[0]
        _map_clone(mesh, clone, clone_pairing)

        if mesh not in mesh_cluster_mapping:
            clone.setParent(mesh_parent)
            continue

        clone.setParent(skinned_parent)
        for cluster in mesh_cluster_mapping[mesh]:
            mi = pm.animation.skinCluster(cluster, maximumInfluences=True, query=True)
            influences = pm.animation.skinCluster(cluster, influence=True, query=True)         
 
            cloned_influences = [clone_pairing[i] for i in influences]
            cloned_cluster = pm.animation.skinCluster(*cloned_influences, clone, mi=mi)
            
            _map_clone(cluster, cloned_cluster, clone_pairing)
            pm.animation.skinCluster(cloned_cluster, normalizeWeights =0, edit=True)
            index_mapping = _get_index_mapping(cluster, cloned_cluster, clone_pairing)
            cloned_cluster.wl.setNumElements(cluster.wl.numElements())
            
            for weight in cluster.wl:
                cw = cloned_cluster.wl.elementByPhysicalIndex(weight.index())
                wws = weight.weights
                cws = cw.weights
                #clear all the weights
                for i in range(0, cws.numElements()):cws.elementByPhysicalIndex(i).set(0)
                
                for e in wws:
                    target = cws.elementByLogicalIndex(index_mapping[e.index()])
                    target.set(e.get())
       
            pm.animation.skinCluster(cloned_cluster, normalizeWeights =1, edit=True)
            
            
            
            
def create_export_set(name='', auto_add_selected=False) -> pm.nodetypes.ObjectSet | None:
    if not name:
        data_name, ok = QInputDialog.getText(None, "New Node Name", 'Name this data')
        if not ok:
            return None
        
        name = f'{data_name}_CSC_EXPORT'
    
    selection = pm.ls(sl=True)
    filtered_selection = pm.ls(sl=True,type=['transform','joint', 'skinCluster', 'mesh'])
    new_node, data = CascExportData.create_node(nodeType = 'objectSet')

    pm.rename(new_node, name)
    pm.select(selection, replace=True)
    
    if filtered_selection:
        if auto_add_selected:
            answer = QMessageBox.StandardButton.Yes
        else:
            answer =  QMessageBox.question(cg3dguru.ui.Window.mayaWindow, 'Add', 'Add the current selection?')
            
        if answer == QMessageBox.StandardButton.Yes:
            new_node.addMembers(filtered_selection)
            
    return new_node


@wait_cursor
def convert_textures():
    #https://help.autodesk.com/view/MAYAUL/2024/ENU/?guid=MAYA_API_REF_cpp_ref_class_m_qt_util_html
    #https://stackoverflow.com/questions/72801366/maya-python-get-the-widget-containing-the-renderd-image-from-mayas-render-view

    roots = {item.getParent(-1) for item in pm.ls(sl=True)}
    branches = pm.listRelatives(list(roots), allDescendents=True)
    textures = exchange.get_textures(branches)
    
    valid_extensions = {'jpg', 'jpeg', 'png'}
    for key, textures in textures.items():
        for texture in textures:
            tpath = Path(texture)
            if tpath.suffix.lower() not in valid_extensions:
                try:         
                    pp = omui.MQtUtil.createPixmap(tpath)
                    pmap = wrapInstance( int(pp), QPixmap)
                    image = pmap.toImage()
                    save_name = tpath.with_suffix('.png')
                    image.save(str(save_name))
                except Exception as e:
                    print(e)
    


@wait_cursor
def _derig_selection():
    selection = pm.ls(sl=True)
    if not selection:
        return False
    
    results = exchange.get_skinned_data_sets(selection)
    exchange.update_skinned_data_sets(*results)
    joints, meshes, skin_clusters, transforms = results

    joint_hierarchy = {}    
    for joint in joints:
        _make_joint_hierarchy(joint, joint.getParent(), joint_hierarchy)
       
    if not joint_hierarchy:
        return False
    
    clone_pairing = {}
    root = pm.general.createNode('transform', name = f"{CLONE_PREFIX}:root")
    data = ProxyRoot.add_data(root)
    data.rootType.set(0)
    
    skeleton_root = pm.general.createNode('transform', name = f"{CLONE_PREFIX}:skel_root", parent=root)
    ProxyRoot.add_data(skeleton_root).rootType.set(1)
    _clone_joints(joint_hierarchy[None], skeleton_root, joint_hierarchy, clone_pairing)
    
    cloned_root_joints = [clone_pairing[joint] for joint in joint_hierarchy[None]]
    pm.general.select(cloned_root_joints, replace=True)
    pm.general.makeIdentity(apply=True, t=0, r=1, s=0, n=0)
    
    meshes_root = pm.general.createNode('transform', name = f"{CLONE_PREFIX}:meshes", parent=root)
    ProxyRoot.add_data(meshes_root).rootType.set(2)
    
    skinned_meshes_root = pm.general.createNode('transform', name = f"{CLONE_PREFIX}:skinned_meshes", parent=root)
    ProxyRoot.add_data(skinned_meshes_root).rootType.set(3)
    skinned_meshes_root.inheritsTransform.set(0)
    
    _clone_meshes(meshes, meshes_root, skinned_meshes_root, clone_pairing)
    
    null_children = [child for child in root.getChildren() if not child.getChildren()]
    if null_children:
        pm.general.delete(null_children)
        
    pm.select(root, replace=True)
    return True




def constrain_proxy():
    import cg3dguru.udata
    data_nodes = cg3dguru.udata.Utils.get_nodes_with_data(data_class=ProxyRoot)
    joint_roots = [joint_root for joint_root in data_nodes if joint_root.rootType.get() == 1]
    
    joint_root = None
    proxy_joints = []
    if not joint_roots:
        pm.error("No proxy data found.")
        return
    
    elif len(joint_roots) > 2:
        #We have mulltiple proxies in the scene, so we need to do some extra work to find the right proxy
        export_nodes = exchange.get_export_nodes()
        pm.warning("add support for finding one of many proxy rigs")
        
    else:
        joint_root = joint_roots[0]
        
        
    proxy_data = cg3dguru.udata.Utils.get_nodes_with_data(pm.listRelatives(joint_roots, allDescendents =True), data_class=ProxyData)
    for proxy in proxy_data:
        source = proxy.proxySource.get()
        if source:
            pm.parentConstraint(source, proxy, maintainOffset =True)
    
        
        



def derig_selection():
    if _derig_selection():
        create_export_set(auto_add_selected=True)        
        
    
    
#import pymel.core as pm
#cluster = pm.PyNode('skinCluster8')
#print(cluster)
#mapping = {}
#for e in cluster.matrix:mapping.setdefault(e.index(),[]).append(e.inputs()[0])
#cluster = pm.PyNode('skinCluster11')
#for e in cluster.matrix:mapping.setdefault(e.index(),[]).append(e.inputs()[0])

#for key,value in mapping.items():
    #print(value)

    
    