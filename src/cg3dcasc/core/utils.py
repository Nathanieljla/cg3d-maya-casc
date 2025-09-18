from pathlib import Path

from maya import OpenMayaUI as omui 
import pymel.core as pm


try:
    from PySide2.QtWidgets import *
    from PySide2.QtGui import *
    from shiboken2 import wrapInstance
except:
    from PySide6.QtWidgets import *
    from PySide6.QtGui import *
    from shiboken6 import wrapInstance   


import cg3dguru.ui
from . import exchange
from .udata import *

CLONE_PREFIX = 'CASC'

from cg3dcasc import preferences



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



def _get_parent_joint(joint):
    parent = joint.getParent()
    while not isinstance(parent, pm.nodetypes.Joint) and parent is not None:
        parent = parent.getParent()
        
    return parent



def _make_joint_hierarchy(joint, joint_hierarchy):
    """Build a dict of parent keys, with children values
    
    This skips anything in the hierarchy that isn't a joint
    """
    parent = joint.getParent()
    if not isinstance(parent, pm.nodetypes.Joint):
        parent = _get_parent_joint(joint)
        
    #The if joint parent pair has already been processed, we don't need to do
    #anything
    if parent in joint_hierarchy and joint in joint_hierarchy[parent]:
        return
        
    joint_hierarchy.setdefault(parent, set()).add(joint)
    if parent is not None:
        _make_joint_hierarchy(parent, joint_hierarchy)

        
        
        
def _map_clone(org, clone, mapping):
    mapping[org] = clone
    mapping[clone] = org
    
    ProxyData.add_data(clone)
    org.message >> clone.proxySource
    
    
def new_world_matrix(transform, reset_scale):

    # Create a new matrix with scale set to (1, 1, 1)
    new_matrix = pm.datatypes.TransformationMatrix(transform.getMatrix(worldSpace=True))
    if reset_scale:
        new_matrix.setScale((1, 1, 1), space='world')
    
    return new_matrix
        

def get_base_name(obj):
    return obj.name().split(":")[-1]
        
        
def _clone_joints(joint_list, parent, joint_hierarchy, clone_pairing):
    reset_scale = preferences.get().derig_reset_joint_scale
    
    for joint in joint_list:
        new_joint = pm.general.createNode('joint', name=f"{CLONE_PREFIX}:{get_base_name(joint)}", parent=parent, skipSelect=True)
        _map_clone(joint, new_joint, clone_pairing)
        new_joint.radius.set(joint.radius.get())
        
        jm = new_world_matrix(joint, reset_scale)
        new_joint.setMatrix(jm, worldSpace=True)
        
        children = joint_hierarchy.get(joint, [])
        if children:
            _clone_joints(children, new_joint, joint_hierarchy, clone_pairing)
            
          
            
def _get_index_mapping(source_cluster, cloned_cluster, clone_pairing):
    cloned_indices = {element.inputs()[0]: element.index() for element in cloned_cluster.matrix}
    
    index_mapping = {}
    for element in source_cluster.matrix:
        index_mapping[element.index()] = cloned_indices[clone_pairing[element.inputs()[0]]]
        
    return index_mapping
    
      
def _get_transform_attrs(obj):
    #You can lock/unlock individual attributes, but the compound attribute
    #might also be locked so you need to make sure it matches the same state.
    #This took way to long to figure out
    attrs = ['translate', 'tx', 'ty', 'tz', 'rotate', 'rx', 'ry', 'rz', 'scale', ' sx', 'sy', 'sz']
    return [obj.attr(name) for name in attrs]

      
def _lock_transform(obj, state):
    attrs = _get_transform_attrs(obj)

    for attr in attrs:
        pm.setAttr(attr, lock=state)
 
    
def _Unhide_primary_attrs(obj):
    attrs = _get_transform_attrs(obj)

    for attr in attrs:
        pm.setAttr(attr, keyable=True)    
    #pm.setAttr(obj.translateX, keyable=True)
    #pm.setAttr(obj.translateY, keyable=True)
    #pm.setAttr(obj.translateZ, keyable=True)
    #pm.setAttr(obj.rotateX, keyable=True)
    #pm.setAttr(obj.rotateY, keyable=True)
    #pm.setAttr(obj.rotateZ, keyable=True)
    #pm.setAttr(obj.scaleX, keyable=True)
    #pm.setAttr(obj.scaleY, keyable=True)
    #pm.setAttr(obj.scaleZ, keyable=True)
    #pm.setAttr(obj.visibility, keyable=True)
    
    _lock_transform(obj, False)
    pm.setAttr(obj.visibility, lock=False)
    
    

def _make_clean_copy(mesh, mesh_cluster_mapping, temp_parent=None):
    base_name = get_base_name(mesh.getParent())
    name = f"{CLONE_PREFIX}:{base_name}_TEMP"

    skin_proxy = pm.duplicate(mesh, name=name)[0]

    #Freeze any scale that might be on the mesh
    _lock_transform(skin_proxy, False)
    pm.makeIdentity(skin_proxy, apply=True, t=True, r=True, s=True, n=False, pn=True)
    pm.parent(skin_proxy, world=True)
    pm.makeIdentity(skin_proxy, apply=True, t=True, r=True, s=True, n=False, pn=True)
    pm.delete(skin_proxy, constructionHistory=True)

    
    clone_name = f"{CLONE_PREFIX}:{base_name}"
    clone = pm.duplicate(skin_proxy, name=clone_name)[0]
    _Unhide_primary_attrs(clone)
    
    if temp_parent is not None:
        skin_proxy.setParent(temp_parent)
    
    if mesh in mesh_cluster_mapping:
        for cluster in mesh_cluster_mapping[mesh]:
            mi = pm.animation.skinCluster(cluster, maximumInfluences=True, query=True)
            influences = pm.animation.skinCluster(cluster, influence=True, query=True)

            cloned_cluster = pm.animation.skinCluster(*influences, skin_proxy, mi=mi, tsb=True)
            pm.copySkinWeights(ss=cluster, ds=cloned_cluster, noMirror=True,
                               surfaceAssociation='closestPoint', influenceAssociation='closestJoint')
            
            pm.select(skin_proxy, replace=True)
            pm.animation.skinCluster(skin_proxy, edit=True, rui=True)

    return (clone, skin_proxy)
    
            
            
def _clone_meshes(meshes, mesh_parent, skinned_parent, clone_pairing):
    mesh_cluster_mapping = exchange.get_mesh_cluster_mappings()
    clean_skins_group = pm.general.createNode('transform', name = f"{CLONE_PREFIX}:CLEAN_SKINS")
    mesh_copies = {}
    
    for mesh in meshes:
        pm.displayInfo(f"Cleaning proxy of {mesh.name()}")
        copies = _make_clean_copy(mesh, mesh_cluster_mapping, clean_skins_group)
        mesh_copies[mesh] = copies
        
    #Update to get the latest clusters generated from our skin proxies
    mesh_cluster_mapping = exchange.get_mesh_cluster_mappings()    
    for mesh, copies in mesh_copies.items():
        pm.displayInfo(f"Finalizing proxy for {mesh.name()}")
        
        clone, skin_proxy = copies
        _map_clone(mesh, clone, clone_pairing)

        if mesh not in mesh_cluster_mapping:
            clone.setParent(mesh_parent)
            continue

        clone.setParent(skinned_parent)
        for cluster in mesh_cluster_mapping[skin_proxy.getShape()]:
            mi = pm.animation.skinCluster(cluster, maximumInfluences=True, query=True)
            influences = pm.animation.skinCluster(cluster, influence=True, query=True)         
 
            cloned_influences = [clone_pairing[i] for i in influences]
            cloned_cluster = pm.animation.skinCluster(*cloned_influences, clone, mi=mi, tsb=True)
            
            _map_clone(cluster, cloned_cluster, clone_pairing)
            pm.animation.skinCluster(cloned_cluster, normalizeWeights =0, edit=True)
            index_mapping = _get_index_mapping(cluster, cloned_cluster, clone_pairing)
            cloned_cluster.wl.setNumElements(cluster.wl.numElements())
            
            for weight in cluster.wl:
                cw = cloned_cluster.wl.elementByPhysicalIndex(weight.index())
                wws = weight.weights
                cws = cw.weights
                
                #clear all the weights
                for i in range(0, cws.numElements()):
                    cws.elementByPhysicalIndex(i).set(0)
                
                for e in wws:
                    index = e.index()
                    if index not in index_mapping:
                        pm.error(f"Index issue was found for skinned mesh {skin_proxy}.  Index value:{index}.")
                        continue
                    
                    target = cws.elementByLogicalIndex(index_mapping[index])
                    target.set(e.get())
       
            pm.animation.skinCluster(cloned_cluster, normalizeWeights =1, edit=True)
            
            
    pm.delete(clean_skins_group)
            
            

def create_export_set(name='', auto_add_selected=False) -> pm.nodetypes.ObjectSet :
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
        _make_joint_hierarchy(joint, joint_hierarchy)
        
    if not joint_hierarchy:
        pm.warning("Please select one or more skinned meshes.")
        return False
    
    for key in joint_hierarchy.keys():
        joint_hierarchy[key] = list(joint_hierarchy[key])
    

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
        
    constraints = [child for child in pm.listRelatives(root, allDescendents =True, type="transform") if isinstance(child, pm.nodetypes.Constraint)]
    if constraints:
        pm.general.delete(constraints) 
    
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
        

    maintain_offset = preferences.get().derig_maintain_offset
    proxy_data = cg3dguru.udata.Utils.get_nodes_with_data(pm.listRelatives(joint_roots, allDescendents =True), data_class=ProxyData)
    for proxy in proxy_data:
        source = proxy.proxySource.get()
        if source:
            pm.parentConstraint(source, proxy, maintainOffset=maintain_offset)
    


def derig_selection():
    selection = pm.ls(sl=True)
    if not selection:
        pm.warning("Please select meshes and/or joints for cloning")
        return
    
    data_name, ok = QInputDialog.getText(None, "Name this character", 'Unique namespace')
    if not ok:
        return None    
    
    global CLONE_PREFIX
    CLONE_PREFIX = data_name
    
    if _derig_selection():
        name = f"{CLONE_PREFIX}:{CLONE_PREFIX}_CSC_EXPORT"
        create_export_set(name, auto_add_selected=True)


