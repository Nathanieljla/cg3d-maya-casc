from pathlib import Path

from maya import OpenMayaUI as omui 
import pymel.core as pm
import maya.cmds as cmds
import maya.mel

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


gMainProgressBar = maya.mel.eval('$tmp = $gMainProgressBar')
progress_bar = False


def start_progress_bar(*args, **kwargs):
    global progress_bar, gMainProgressBar
    progress_bar = True

    kwargs['edit'] = True
    kwargs['beginProgress'] = True
    cmds.progressBar(gMainProgressBar, *args, **kwargs)

    
def edit_progress_bar(*args, **kwargs):
    kwargs['edit'] = True
    cmds.progressBar(gMainProgressBar, *args, **kwargs)


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
            
            global progress_bar, gMainProgressBar
            if progress_bar:
                progress_bar = False
                cmds.progressBar(gMainProgressBar, edit=True, endProgress=True)

    return wrapper


def _walk_up(transform, parents, keep):
    parent = transform.getParent()
    if parent is None:
        return

    if parent in parents:
        keep.add(parent)
        return

    parents.add(parent)
    _walk_up(parent, parents, keep)
    
    
def _get_closest_parent(transform, keep):
    parent = transform.getParent()
    if parent is None:
        return

    if parent in keep:
        return parent

    return _get_closest_parent(parent, keep)
    

def _solve_joint_hierarchy(joints):
    joint_hierarchy = {}
    
    keep = set()
    parents = set()
    for joint in joints:
        keep.add(joint)
        _walk_up(joint, parents, keep)

    for tranform in keep:
        parent = _get_closest_parent(tranform, keep)
        joint_hierarchy.setdefault(parent, set()).add(tranform)
        
    for key in joint_hierarchy.keys():
        joint_hierarchy[key] = list(joint_hierarchy[key])
        
    return joint_hierarchy

  
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
        
        
def _clone_joints(children, parent, joint_hierarchy, clone_pairing):
    reset_scale = preferences.get().derig_reset_joint_scale
    convert_transforms = False
    
    for child in children:
        child_type = child.type()
        new_type = 'joint' if child_type == 'joint' or convert_transforms else 'transform'
        clone = pm.general.createNode(new_type, name=f"{CLONE_PREFIX}:{get_base_name(child)}", parent=parent, skipSelect=True)
        _map_clone(child, clone, clone_pairing)

        if new_type == 'joint' and child_type == 'joint':
            clone.radius.set(child.radius.get())
        
        cm = new_world_matrix(child, reset_scale)
        clone.setMatrix(cm, worldSpace=True)
        
        next_children = joint_hierarchy.get(child, [])
        if next_children:
            _clone_joints(next_children, clone, joint_hierarchy, clone_pairing)
            
          
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
    
    _lock_transform(obj, False)
    pm.setAttr(obj.visibility, lock=False)
    
    
def _make_clean_copy(source_shape, mesh_cluster_mapping, temp_parent=None):
    base_name = get_base_name(source_shape.getParent())
    name = f"{CLONE_PREFIX}:{base_name}_TEMP"

    skin_proxy = pm.duplicate(source_shape, name=name)[0]

    _Unhide_primary_attrs(skin_proxy)
    pm.makeIdentity(skin_proxy.fullPathName(), apply=True, t=True, r=True, s=True, n=False, pn=True)
    pm.parent(skin_proxy.fullPathName(), world=True)
    pm.makeIdentity(skin_proxy.fullPathName(), apply=True, t=True, r=True, s=True, n=False, pn=True)
    pm.delete(skin_proxy.fullPathName(), constructionHistory=True)

    clone_name = f"{CLONE_PREFIX}:{base_name}"
    clone = pm.duplicate(skin_proxy, name=clone_name)[0]
    _Unhide_primary_attrs(clone)
    
    if temp_parent is not None:
        skin_proxy.setParent(temp_parent)
    
    if source_shape in mesh_cluster_mapping:
        for cluster in mesh_cluster_mapping[source_shape]:
            mi = pm.animation.skinCluster(cluster, maximumInfluences=True, query=True)
            influences = pm.animation.skinCluster(cluster, influence=True, query=True)

            cloned_cluster = pm.animation.skinCluster(*influences, skin_proxy, mi=mi, multi=True, tsb=True) #test
            pm.copySkinWeights(ss=cluster, ds=cloned_cluster, noMirror=True,
                               surfaceAssociation='closestPoint', influenceAssociation='closestJoint')
            
            pm.select(skin_proxy, replace=True)
            pm.animation.skinCluster(skin_proxy, edit=True, rui=True)

    return (clone, skin_proxy)




def replace_skin_joint(skinned_mesh, old_joint, new_joint):
    """
    Replaces a joint in a skinCluster by transferring weights.

    Args:
        skinned_mesh (pm.PyNode): The skinned mesh.
        old_joint (pm.PyNode): The old joint to replace.
        new_joint (pm.PyNode): The new joint to replace with.
    """
    # Check that the joints exist
    if not pm.objExists(old_joint) or not pm.objExists(new_joint):
        pm.warning("One or both of the joints do not exist.")
        return

    # Get the skinCluster node from the mesh
    skin_cluster_node = pm.general.PyNode(pm.mel.eval('findRelatedSkinCluster("{}")'.format(skinned_mesh)))

    if not skin_cluster_node:
        pm.warning(f"No skinCluster found on {skinned_mesh}.")
        return

    print(f"SkinCluster found: {skin_cluster_node}")

    # Add the new joint as an influence, if it isn't already one
    if new_joint not in skin_cluster_node.getInfluence():
        pm.skinCluster(skin_cluster_node, edit=True, addInfluence=new_joint, weight=0)
        print(f"Added {new_joint} as an influence.")

    # Transfer weights from the old joint to the new joint
    # The skinPercent command handles the weight transfer
    # (The `transformValue` flag is the key for transferring weights from one influence to another)
    all_vertices = skinned_mesh.vtx[:]
    pm.skinPercent(skin_cluster_node, all_vertices, transformValue=[(old_joint, 0), (new_joint, 1)])
    print(f"Transferred weights from {old_joint} to {new_joint}.")

    # Lock weights on the new joint to prevent redistribution on removal
    pm.skinCluster(skin_cluster_node, edit=True, lockWeights=True, influence=new_joint)
    
    # Remove the old joint from the skinCluster
    pm.skinCluster(skin_cluster_node, edit=True, removeInfluence=old_joint)
    print(f"Removed {old_joint} as an influence.")
    
    # Unlock weights on the new joint if you plan to continue editing them
    pm.skinCluster(skin_cluster_node, edit=True, lockWeights=False, influence=new_joint)
    print("Process complete.")

# --- Example Usage ---
# Make sure your scene contains a skinned mesh named 'pSphere1', and joints 'joint1' and 'joint2'
# with 'joint1' already being an influence on the mesh.

# To run the script, first set up your scene with the necessary objects.
# Example:
#   1. Create a sphere: `pm.polySphere()`
#   2. Create two joints: `pm.joint(p=(0, 5, 0), n='old_joint_01')` and `pm.joint(p=(0, 10, 0), n='new_joint_01')`
#   3. Skin the sphere to the old joint: `pm.skinCluster('old_joint_01', 'pSphere1')`

# Call the function with your specific object and joint names
# replace_skin_joint('pSphere1', 'old_joint_01', 'new_joint_01')



            
def _clone_meshes(meshes, mesh_parent, skinned_parent, clone_pairing):
    mesh_cluster_mapping = exchange.get_mesh_cluster_mappings()
    clean_skins_group = pm.general.createNode('transform', name = f"{CLONE_PREFIX}:CLEAN_SKINS")
    mesh_copies = {}

    edit_progress_bar(progress=0, maxValue=len(meshes) * 2)
    for source_shape in meshes:
        message =f"Cleaning proxy of {source_shape.name()}"
        edit_progress_bar(status=message, step=1)
        pm.displayInfo(message)
        
        copies = _make_clean_copy(source_shape, mesh_cluster_mapping, clean_skins_group)
        mesh_copies[source_shape] = copies

    #Update to get the latest clusters generated from our skin proxies
    mesh_cluster_mapping = exchange.get_mesh_cluster_mappings()    
    for source_shape, copies in mesh_copies.items():
        message = f"Finalizing proxy for {source_shape.name()}"
        edit_progress_bar(status=message, step=1)
        pm.displayInfo(message)
        
        clone, skin_proxy = copies
        _map_clone(source_shape, clone, clone_pairing)

        if source_shape not in mesh_cluster_mapping:
            clone.setParent(mesh_parent)
            continue

        clone.setParent(skinned_parent)
        for cluster in mesh_cluster_mapping[skin_proxy.getShape()]:
            mi = pm.animation.skinCluster(cluster, maximumInfluences=True, query=True)
            influences = pm.animation.skinCluster(cluster, influence=True, query=True)
            cloned_influences = [clone_pairing[i] for i in influences]

            cloned_cluster = pm.animation.skinCluster(*cloned_influences, clone, mi=mi, multi=True, tsb=True)
            
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
                        pm.warning(f"Index issue was found for skinned mesh {skin_proxy}.  Index value:{index}.")
                        continue
                    
                    target = cws.elementByLogicalIndex(index_mapping[index])
                    target.set(e.get())
       
            pm.animation.skinCluster(cloned_cluster, normalizeWeights=1, edit=True)

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

    start_progress_bar(status='Creating Proxy', maxValue=100)

    results = exchange.get_skinned_data_sets(selection)
    exchange.update_skinned_data_sets(*results)
    joints, meshes, skin_clusters, transforms = results
    
    if not joints and not meshes and not skin_clusters:
        pm.error("No joints or meshes to convert to a proxy.")
        return

    joint_hierarchy = _solve_joint_hierarchy(joints)

    clone_pairing = {}
    root = pm.general.createNode('transform', name=f"{CLONE_PREFIX}:root")
    data = ProxyRoot.add_data(root)
    data.rootType.set(0)

    skeleton_root = pm.general.createNode('transform', name=f"{CLONE_PREFIX}:skel_root", parent=root)
    ProxyRoot.add_data(skeleton_root).rootType.set(1)

    edit_progress_bar(status='Cloning Joints', step=50)
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
        #We have multiple proxies in the scene, so we need to do some extra work to find the right proxy
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


