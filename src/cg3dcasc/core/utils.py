from pathlib import Path
import time
import enum

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
    kwargs['visible'] = True
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

  
def _map_proxy(org, proxy, mapping):
    mapping[org] = proxy
    mapping[proxy] = org
    
    ProxyData.add_data(proxy)
    org.message >> proxy.proxySource
    
    
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

    edit_progress_bar(status='Cloning Joints', progress=0, maxValue=len(children))

    for child in children:
        edit_progress_bar(status='Cloning Joints', step=1)
        child_type = child.type()
        new_type = 'joint' if child_type == 'joint' or convert_transforms else 'transform'
        clone = pm.general.createNode(new_type, name=f"{CLONE_PREFIX}:{get_base_name(child)}", parent=parent, skipSelect=True)
        _map_proxy(child, clone, clone_pairing)

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
    

def _replace(p1, p1_idx, p2, p2_idx, skin_cluster_node, attr_list):
    new_data = attr_list.elementByLogicalIndex(p1_idx)
    old_data = attr_list.elementByLogicalIndex(p2_idx)

    list_locked = attr_list.isLocked()
    old_data_locked = old_data.isLocked()
    
    attr_list.unlock()    
    old_data.unlock()
    new_data.unlock()

    new_plug = new_data.inputs(plugs=True)
    if new_plug:
        pm.connectAttr(new_plug[0], old_data, force=True)
    else:
        old_data.set(new_data.get())
        
    attr_list[p1_idx].unlock()
    pm.removeMultiInstance(new_data, b=True)
    old_data.lock(old_data_locked)
    attr_list.lock(list_locked)


def _copy_swap(skin_proxy, skin_cluster_node, clone_pairing, originals, replacements):
    name = skin_proxy.name().split(":")[-1]
    message = f"Cloning {name} weights"
    edit_progress_bar(status=message, progress=0, maxValue=len(originals))
    
    skin_cluster_node.normalizeWeights.set(0)
    pm.skinCluster(skin_cluster_node, edit=True, addInfluence=replacements, weight=0.0)
    
    joint_indices = {}
    for idx, matrix in enumerate(skin_cluster_node.matrix):
        connections = pm.listConnections(matrix, source=True, plugs=False)
        if not connections:
            continue

        source_joint = connections[0]
        if source_joint not in clone_pairing:
            #this case shouldn't be posssible.
            pm.warning(f"{source_joint.name()} isn't be replaced? That shouldn't be possible.")
            continue
        
        joint_indices[source_joint] = matrix.index()


    bind_pose_node = skin_cluster_node.bindPose.inputs(plugs=True, type='dagPose')
    if bind_pose_node:
        pm.disconnectAttr(bind_pose_node[0], skin_cluster_node.bindPose)
        
    for joint, idx in joint_indices.items():
        edit_progress_bar(status=message, step=1)
        if joint not in replacements:
            continue
        
        p1 = joint
        p1_idx = idx
        p2 = clone_pairing[joint]
        p2_idx = joint_indices[p2]

        _replace(p1, p1_idx, p2, p2_idx, skin_cluster_node, skin_cluster_node.bindPreMatrix)
        _replace(p1, p1_idx, p2, p2_idx, skin_cluster_node, skin_cluster_node.matrix)

        connections = pm.listConnections(p2, destination=True,
                                         connections=True, plugs=True, sourceFirst=True, t='skinCluster',
                                         skipConversionNodes=True)

        for connection in connections:
            source_plug = connection[0]
            destination_plug = connection[1]
            if destination_plug.node() != skin_cluster_node:
                continue
            #print(f"disconnecting: {source_plug} and {destination_plug}")
            pm.disconnectAttr(source_plug, destination_plug)

    try:
        bind_pose = pm.dagPose(skin_cluster_node.getInfluence(), save=True,
                               bindPose=True, name=f'{skin_cluster_node.name()}_BindPose')
        bind_pose.message >> skin_cluster_node.bindPose
    except Exception as e:
        print(e)


def _copy_flood(skin_proxy, skin_cluster_node, clone_pairing, originals, replacements, vertices):
    original_warnings_state = cmds.scriptEditorInfo(query=True, suppressWarnings=True)
    cmds.scriptEditorInfo(suppressWarnings=True)

    name = skin_proxy.name().split(":")[-1]
    message = f"Cloning {name} weights"
    edit_progress_bar(status=message, progress=0, maxValue=len(originals))

    try:
        skin_cluster_node.normalizeWeights.set(1)
        pm.skinCluster(skin_cluster_node, edit=True, addInfluence=replacements, weight=0.0)    

        for idx, original in enumerate(originals):
            replacement = replacements[idx]
            pm.skinCluster(skin_cluster_node, edit=True, lockWeights=True, influence=original)
            pm.skinCluster(skin_cluster_node, edit=True, lockWeights=True, influence=replacement)
            
        for idx, original in enumerate(originals):
            replacement = replacements[idx]
            pm.skinCluster(skin_cluster_node, edit=True, lockWeights=False, influence=original)
            pm.skinCluster(skin_cluster_node, edit=True, lockWeights=False, influence=replacement)
            pm.skinPercent(skin_cluster_node, vertices, transformValue=[(original, 0.0), (replacement, 1.0)], zeroRemainingInfluences=False, normalize=True)
            pm.skinCluster(skin_cluster_node, edit=True, lockWeights=True, influence=original)
            pm.skinCluster(skin_cluster_node, edit=True, lockWeights=True, influence=replacement)
            
            edit_progress_bar(status=message, step=1)
    except Exception as e:
        raise e
    finally:
        cmds.scriptEditorInfo(suppressWarnings=original_warnings_state)
        

def _copy_per_vert(skin_proxy, skin_cluster_node, clone_pairing, originals, replacements):
    skin_cluster_node.normalizeWeights.set(2)
    pm.skinCluster(skin_cluster_node, edit=True, addInfluence=replacements, weight=0.0)
    
    #make sure the original joints are unlocked
    for og in originals:
        pm.skinCluster(skin_cluster_node, edit=True, lockWeights=False, influence=og)

    joint_to_idx = {element.inputs()[0]: element.index() for element in skin_cluster_node.matrix}
    oldIdx_to_newIdx = {joint_to_idx[og]: joint_to_idx[clone_pairing[og]] for og in originals}

    step_size = int(skin_cluster_node.wl.numElements() / 100)
    if step_size < 1:
        step_size = 1
    total_steps = int(skin_cluster_node.wl.numElements() / step_size)

    name = skin_proxy.name().split(":")[-1]
    message = f"Cloning {name} weights"
    edit_progress_bar(status=message, progress=0, maxValue=total_steps)

    for idx, vert_weights_entries in enumerate(skin_cluster_node.wl):
        if idx and idx % step_size == 0:
            edit_progress_bar(step=1)

        vert_weights = vert_weights_entries.weights #vert_weights.index() returns the vertex number
        new_weights = {}

        for vert_weight in vert_weights:
            joint_idx = vert_weight.index()
            joint_influence = vert_weight.get()

            vert_weight.set(0.0)
            if joint_idx not in oldIdx_to_newIdx:
                continue

            #define the new weight values and clear the old ones.
            new_weights[oldIdx_to_newIdx[joint_idx]] = joint_influence

        for joint_idx, value in new_weights.items():
            weight_entry = vert_weights.elementByLogicalIndex(joint_idx)
            weight_entry.set(value)


def _clone_meshes(meshes, mesh_parent, skinned_parent, clone_pairing):
    mesh_cluster_mapping = exchange.get_mesh_cluster_mappings()

    copy_method = preferences.CopyWeightType.SWAP
    print(f"Cloning weights via {copy_method} method.")

    for mesh_count, source_shape in enumerate(meshes):
        message = f"Making proxy of {source_shape.name()}"
        edit_progress_bar(status=message, progress=mesh_count, maxValue=len(meshes))
        pm.displayInfo(message)

        base_name = get_base_name(source_shape.getParent())
        name = f"{CLONE_PREFIX}:{base_name}"
        mesh_proxy = pm.duplicate(source_shape, name=name)[0]

        _Unhide_primary_attrs(mesh_proxy)
        pm.makeIdentity(mesh_proxy.fullPathName(), apply=True, t=True, r=True, s=True, n=False, pn=True)
        pm.parent(mesh_proxy.fullPathName(), world=True)
        pm.makeIdentity(mesh_proxy.fullPathName(), apply=True, t=True, r=True, s=True, n=False, pn=True)
        pm.delete(mesh_proxy.fullPathName(), constructionHistory=True)
        _map_proxy(source_shape, mesh_proxy, clone_pairing)

        if source_shape not in mesh_cluster_mapping:
            mesh_proxy.setParent(mesh_parent)
            continue
        else:
            mesh_proxy.setParent(skinned_parent)
            
            for cluster in mesh_cluster_mapping[source_shape]:
                mi = pm.animation.skinCluster(cluster, maximumInfluences=True, query=True)
                influences = pm.animation.skinCluster(cluster, influence=True, query=True)
    
                cloned_cluster = pm.animation.skinCluster(*influences, mesh_proxy, mi=mi, multi=True, tsb=True) #test
                pm.copySkinWeights(ss=cluster, ds=cloned_cluster, noMirror=True,
                                   surfaceAssociation='closestPoint', influenceAssociation='closestJoint')
                
                pm.select(mesh_proxy, replace=True)
                pm.animation.skinCluster(mesh_proxy, edit=True, rui=True) #remove unused influences
                pm.animation.skinCluster(cloned_cluster, edit=True, obeyMaxInfluences=False)
            
                originals = cloned_cluster.getInfluence()
                replacements = [clone_pairing[i] for i in originals]
                skinned_geometry = cloned_cluster.getGeometry()[0]
                vertices = skinned_geometry.vtx[:]
                prune = False
                remove_originals = True

                match copy_method:
                    case preferences.CopyWeightType.SWAP: #Mazu: 19.8838, Waitress: 4.5856,
                        remove_originals = False
                        _copy_swap(mesh_proxy, cloned_cluster, clone_pairing, originals, replacements)

                    case preferences.CopyWeightType.FLOOD: #Mazu: 158.3618, Waitress: 18.1239,
                        prune = True
                        _copy_flood(mesh_proxy, cloned_cluster, clone_pairing, originals, replacements, vertices)
            
                    case preferences.CopyWeightType.PER_VERT: #Mazu: 138.2624, Waitress: 70.3756,
                        _copy_per_vert(mesh_proxy, cloned_cluster, clone_pairing, originals, replacements)

                cloned_cluster.normalizeWeights.set(2)
                if remove_originals:
                    for original in originals:
                        pm.skinCluster(cloned_cluster, edit=True, removeInfluence=original)

                for influence in cloned_cluster.getInfluence():
                    pm.skinCluster(cloned_cluster, edit=True, lockWeights=False, influence=influence)
                    
                cloned_cluster.normalizeWeights.set(1)
                if prune:
                    pm.animation.skinPercent(cloned_cluster, vertices, pruneWeights=0.005)
                else:
                    pm.animation.skinCluster(cloned_cluster, forceNormalizeWeights=True, edit=True)

      
      

def create_export_set(name='', auto_add_selected=False) -> pm.nodetypes.ObjectSet:
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

    _clone_joints(joint_hierarchy[None], skeleton_root, joint_hierarchy, clone_pairing)
    
    cloned_root_joints = [clone_pairing[joint] for joint in joint_hierarchy[None]]
    pm.general.select(cloned_root_joints, replace=True)
    pm.general.makeIdentity(apply=True, t=0, r=1, s=0, n=0)
    
    meshes_root = pm.general.createNode('transform', name = f"{CLONE_PREFIX}:meshes", parent=root)
    ProxyRoot.add_data(meshes_root).rootType.set(2)
    
    skinned_meshes_root = pm.general.createNode('transform', name = f"{CLONE_PREFIX}:skinned_meshes", parent=root)
    ProxyRoot.add_data(skinned_meshes_root).rootType.set(3)
    skinned_meshes_root.inheritsTransform.set(0)

    start_time = time.perf_counter()
    _clone_meshes(meshes, meshes_root, skinned_meshes_root, clone_pairing)
    end_time = time.perf_counter()
    elapsed_time = end_time - start_time
    print(f"The function took {elapsed_time:.4f} seconds to run.")
    #waitress 76.3239 second with manual weight copy
    
    null_children = [child for child in root.getChildren() if not child.getChildren()]
    if null_children:
        pm.general.delete(null_children)
  
    constraints = [child for child in pm.listRelatives(root, allDescendents=True, type="transform") if isinstance(child, pm.nodetypes.Constraint)]
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


