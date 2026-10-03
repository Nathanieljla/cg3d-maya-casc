"""Proxy-rig and utility workflows implemented with Maya's native APIs."""

from pathlib import Path
import time

from maya import OpenMayaUI as omui
from maya import cmds, mel
from maya.api import OpenMaya as om

try:
    from PySide2.QtGui import QPixmap
    from PySide2.QtWidgets import QInputDialog, QMessageBox
    from shiboken2 import wrapInstance
except ImportError:
    from PySide6.QtGui import QPixmap
    from PySide6.QtWidgets import QInputDialog, QMessageBox
    from shiboken6 import wrapInstance

import cg3dguru.ui
import cg3dguru.udata
from cg3dguru.maya import Node, node_name, nodes

from cg3dcasc_v2 import preferences

from . import common, hik, materials, server
from . import maya as mayautil
from .udata import CascExportData, ProxyData, ProxyRoot


CLONE_PREFIX = "CASC"
progress_bar = False
if cmds.about(batch=True):
    gMainProgressBar = None
else:
    try:
        gMainProgressBar = mel.eval("$tmp = $gMainProgressBar")
    except RuntimeError:
        gMainProgressBar = None


def start_progress_bar(*args, **kwargs):
    global progress_bar
    if not gMainProgressBar:
        return
    progress_bar = True
    kwargs.update(edit=True, beginProgress=True, visible=True)
    cmds.progressBar(gMainProgressBar, *args, **kwargs)


def edit_progress_bar(*args, **kwargs):
    if gMainProgressBar:
        kwargs["edit"] = True
        cmds.progressBar(gMainProgressBar, *args, **kwargs)


def wait_cursor(func):
    def wrapper(*args, **kwargs):
        cmds.waitCursor(state=True)
        try:
            return func(*args, **kwargs)
        finally:
            cmds.waitCursor(state=False)
            global progress_bar
            if progress_bar and gMainProgressBar:
                progress_bar = False
                cmds.progressBar(gMainProgressBar, edit=True, endProgress=True)

    return wrapper


def _walk_up(transform, parents, keep):
    parent = mayautil.parent(transform)
    if parent is None:
        return
    if parent in parents:
        keep.add(parent)
        return
    parents.add(parent)
    _walk_up(parent, parents, keep)


def _get_closest_parent(transform, keep):
    parent = mayautil.parent(transform)
    if parent is None or parent in keep:
        return parent
    return _get_closest_parent(parent, keep)


def _solve_joint_hierarchy(joints):
    hierarchy = {}
    keep = set(joints)
    parents = set()
    for joint in joints:
        _walk_up(joint, parents, keep)
    for transform in keep:
        hierarchy.setdefault(_get_closest_parent(transform, keep), []).append(transform)
    return hierarchy


def _map_proxy(original, proxy, mapping):
    original = mayautil.as_node(original)
    proxy = mayautil.as_node(proxy)
    mapping[original] = proxy
    mapping[proxy] = original
    data = ProxyData.add_data(proxy)
    original.message.connect(data.proxySource, force=True)


def new_world_matrix(transform, reset_scale):
    matrix = om.MTransformationMatrix(mayautil.world_matrix(transform))
    if reset_scale:
        matrix.setScale((1.0, 1.0, 1.0), om.MSpace.kWorld)
    return matrix.asMatrix()


def get_base_name(obj):
    return node_name(obj).split("|")[-1].split(":")[-1]


def _clone_joints(children, parent, joint_hierarchy, clone_pairing):
    reset_scale = preferences.get().derig_reset_joint_scale
    edit_progress_bar(status="Cloning Joints", progress=0, maxValue=len(children))
    for child in children:
        edit_progress_bar(status="Cloning Joints", step=1)
        child_type = mayautil.node_type(child)
        new_type = "joint" if child_type == "joint" else "transform"
        clone = Node(
            cmds.createNode(
                new_type,
                name="{}:{}".format(CLONE_PREFIX, get_base_name(child)),
                parent=node_name(parent),
                skipSelect=True,
            )
        )
        _map_proxy(child, clone, clone_pairing)
        if new_type == "joint" and child_type == "joint":
            cmds.setAttr(clone.name() + ".radius", cmds.getAttr(node_name(child) + ".radius"))
        mayautil.set_world_matrix(clone, new_world_matrix(child, reset_scale))
        next_children = joint_hierarchy.get(child, [])
        if next_children:
            _clone_joints(next_children, clone, joint_hierarchy, clone_pairing)


def _transform_attributes(obj):
    name = node_name(obj)
    return [
        "{}.{}".format(name, attribute)
        for attribute in (
            "translate", "tx", "ty", "tz", "rotate", "rx", "ry", "rz",
            "scale", "sx", "sy", "sz",
        )
    ]


def _lock_transform(obj, state):
    for attribute in _transform_attributes(obj):
        cmds.setAttr(attribute, lock=state)


def _unhide_primary_attrs(obj):
    for attribute in _transform_attributes(obj):
        cmds.setAttr(attribute, keyable=True)
    _lock_transform(obj, False)
    cmds.setAttr(node_name(obj) + ".visibility", lock=False)


def _set_plug_value(destination, value, attribute_type):
    if attribute_type == "matrix":
        if isinstance(value, (list, tuple)) and len(value) == 1:
            value = value[0]
        cmds.setAttr(destination, *value, type="matrix")
    elif isinstance(value, str):
        cmds.setAttr(destination, value, type="string")
    elif isinstance(value, (list, tuple)):
        if len(value) == 1 and isinstance(value[0], (list, tuple)):
            value = value[0]
        cmds.setAttr(destination, *value)
    else:
        cmds.setAttr(destination, value)


def _replace(source_index, destination_index, skin_cluster, attribute_name):
    cluster_name = node_name(skin_cluster)
    array_plug = "{}.{}".format(cluster_name, attribute_name)
    source_plug = "{}[{}]".format(array_plug, source_index)
    destination_plug = "{}[{}]".format(array_plug, destination_index)
    array_locked = cmds.getAttr(array_plug, lock=True)
    destination_locked = cmds.getAttr(destination_plug, lock=True)
    cmds.setAttr(array_plug, lock=False)
    cmds.setAttr(destination_plug, lock=False)
    cmds.setAttr(source_plug, lock=False)

    inputs = cmds.listConnections(
        source_plug, source=True, destination=False, plugs=True
    ) or []
    if inputs:
        cmds.connectAttr(inputs[0], destination_plug, force=True)
    else:
        _set_plug_value(
            destination_plug,
            cmds.getAttr(source_plug),
            cmds.getAttr(source_plug, type=True),
        )
    cmds.removeMultiInstance(source_plug, b=True)
    cmds.setAttr(destination_plug, lock=destination_locked)
    cmds.setAttr(array_plug, lock=array_locked)


def _influence_indices(skin_cluster):
    cluster_name = node_name(skin_cluster)
    result = {}
    for index in cmds.getAttr(cluster_name + ".matrix", multiIndices=True) or []:
        inputs = cmds.listConnections(
            "{}.matrix[{}]".format(cluster_name, index),
            source=True,
            destination=False,
        ) or []
        if inputs:
            result[Node(inputs[0])] = index
    return result


def _copy_swap(skin_proxy, skin_cluster, clone_pairing, originals, replacements):
    cluster_name = node_name(skin_cluster)
    edit_progress_bar(
        status="Cloning {} weights".format(get_base_name(skin_proxy)),
        progress=0,
        maxValue=len(originals),
    )
    cmds.setAttr(cluster_name + ".normalizeWeights", 0)
    cmds.skinCluster(
        cluster_name,
        edit=True,
        addInfluence=mayautil.names(replacements),
        weight=0.0,
    )
    indices = _influence_indices(skin_cluster)

    bind_poses = cmds.listConnections(
        cluster_name + ".bindPose",
        source=True,
        destination=False,
        plugs=True,
        type="dagPose",
    ) or []
    if bind_poses:
        mayautil.disconnect(bind_poses[0], cluster_name + ".bindPose")

    for original in originals:
        edit_progress_bar(step=1)
        replacement = clone_pairing[original]
        _replace(indices[original], indices[replacement], skin_cluster, "bindPreMatrix")
        _replace(indices[original], indices[replacement], skin_cluster, "matrix")

        pairs = cmds.listConnections(
            node_name(replacement),
            source=False,
            destination=True,
            plugs=True,
            connections=True,
            type="skinCluster",
            skipConversionNodes=True,
        ) or []
        for source_plug, destination_plug in zip(pairs[0::2], pairs[1::2]):
            if destination_plug.split(".", 1)[0] == cluster_name:
                mayautil.disconnect(source_plug, destination_plug)

    try:
        influences = cmds.skinCluster(cluster_name, query=True, influence=True) or []
        bind_pose = cmds.dagPose(
            influences,
            save=True,
            bindPose=True,
            name=cluster_name.split("|")[-1] + "_BindPose",
        )
        cmds.connectAttr(bind_pose + ".message", cluster_name + ".bindPose", force=True)
    except RuntimeError as error:
        cmds.warning(str(error))


def _copy_flood(skin_proxy, skin_cluster, clone_pairing, originals, replacements, vertices):
    """Compatibility path; preserve weights by swapping influence plugs."""
    _copy_swap(skin_proxy, skin_cluster, clone_pairing, originals, replacements)


def _copy_per_vert(skin_proxy, skin_cluster, clone_pairing, originals, replacements):
    """Compatibility path; preserve weights by swapping influence plugs."""
    _copy_swap(skin_proxy, skin_cluster, clone_pairing, originals, replacements)


def _clone_meshes(meshes, mesh_parent, skinned_parent, clone_pairing):
    mesh_cluster_mapping = common.get_mesh_cluster_mappings()
    copy_method = preferences.CopyWeightType.SWAP
    print("Cloning weights via {} method.".format(copy_method))

    for mesh_count, source_shape in enumerate(meshes):
        message = "Making proxy of {}".format(source_shape.name())
        edit_progress_bar(status=message, progress=mesh_count, maxValue=len(meshes))
        om.MGlobal.displayInfo(message)

        name = "{}:{}".format(CLONE_PREFIX, get_base_name(mayautil.parent(source_shape)))
        mesh_proxy = Node(cmds.duplicate(node_name(source_shape), name=name)[0])
        _unhide_primary_attrs(mesh_proxy)
        cmds.makeIdentity(mesh_proxy.name(), apply=True, t=True, r=True, s=True, n=False, pn=True)
        if mayautil.parent(mesh_proxy) is not None:
            cmds.parent(mesh_proxy.name(), world=True)
        cmds.makeIdentity(mesh_proxy.name(), apply=True, t=True, r=True, s=True, n=False, pn=True)
        cmds.delete(mesh_proxy.name(), constructionHistory=True)
        _map_proxy(source_shape, mesh_proxy, clone_pairing)

        source_clusters = mesh_cluster_mapping.get(source_shape)
        if not source_clusters:
            cmds.parent(mesh_proxy.name(), node_name(mesh_parent))
            continue
        cmds.parent(mesh_proxy.name(), node_name(skinned_parent))

        for cluster in source_clusters:
            cluster_name = node_name(cluster)
            max_influences = cmds.skinCluster(
                cluster_name, maximumInfluences=True, query=True
            )
            influences = nodes(
                cmds.skinCluster(cluster_name, influence=True, query=True) or []
            )
            arguments = mayautil.names(influences) + [mesh_proxy.name()]
            kwargs = {
                "maximumInfluences": max_influences,
                "toSelectedBones": True,
            }
            if int(cmds.about(version=True)) > 2023:
                kwargs["multi"] = True
            cloned_cluster = Node(cmds.skinCluster(*arguments, **kwargs)[0])
            cmds.copySkinWeights(
                sourceSkin=cluster_name,
                destinationSkin=cloned_cluster.name(),
                noMirror=True,
                surfaceAssociation="closestPoint",
                influenceAssociation="closestJoint",
            )
            cmds.skinCluster(mesh_proxy.name(), edit=True, removeUnusedInfluence=True)
            cmds.skinCluster(
                cloned_cluster.name(), edit=True, obeyMaxInfluences=False
            )

            originals = nodes(
                cmds.skinCluster(
                    cloned_cluster.name(), query=True, influence=True
                )
                or []
            )
            replacements = [clone_pairing[influence] for influence in originals]
            _copy_swap(
                mesh_proxy,
                cloned_cluster,
                clone_pairing,
                originals,
                replacements,
            )
            cmds.setAttr(cloned_cluster.name() + ".normalizeWeights", 2)
            for influence in cmds.skinCluster(
                cloned_cluster.name(), query=True, influence=True
            ) or []:
                cmds.skinCluster(
                    cloned_cluster.name(),
                    edit=True,
                    lockWeights=False,
                    influence=influence,
                )
            cmds.setAttr(cloned_cluster.name() + ".normalizeWeights", 1)
            cmds.skinCluster(
                cloned_cluster.name(), edit=True, forceNormalizeWeights=True
            )


def create_export_set(name="", auto_add_selected=False):
    if not name:
        data_name, ok = QInputDialog.getText(None, "New Node Name", "Name this data")
        if not ok:
            return None
        name = "{}_CSC_EXPORT".format(data_name)

    selection = mayautil.ls(selection=True, long=True)
    filtered = mayautil.ls(
        selection=True,
        type=["transform", "joint", "skinCluster", "mesh"],
        long=True,
    )
    new_node, _ = CascExportData.create_node(nodeType="objectSet")
    new_node = mayautil.rename(new_node, name)
    if selection:
        cmds.select(mayautil.names(selection), replace=True)
    else:
        cmds.select(clear=True)

    if filtered:
        answer = (
            QMessageBox.StandardButton.Yes
            if auto_add_selected
            else QMessageBox.question(
                cg3dguru.ui.Window.mayaWindow,
                "Add",
                "Add the current selection?",
            )
        )
        if answer == QMessageBox.StandardButton.Yes:
            mayautil.add_set_members(new_node, filtered)
    return new_node


@wait_cursor
def convert_textures():
    roots = {mayautil.top_parent(item) for item in mayautil.ls(selection=True, long=True)}
    textures = materials.get_textures(mayautil.descendants(roots))
    valid_extensions = {".jpg", ".jpeg", ".png"}
    for texture_paths in textures.values():
        for texture in texture_paths:
            texture_path = Path(texture)
            if texture_path.suffix.lower() in valid_extensions:
                continue
            try:
                pointer = omui.MQtUtil.createPixmap(str(texture_path))
                pixmap = wrapInstance(int(pointer), QPixmap)
                pixmap.toImage().save(str(texture_path.with_suffix(".png")))
            except (RuntimeError, ValueError) as error:
                cmds.warning(str(error))


@wait_cursor
def _derig_selection():
    selection = mayautil.ls(selection=True, long=True)
    if not selection:
        return False
    start_progress_bar(status="Creating Proxy", maxValue=100)
    joints, meshes, skin_clusters, transforms = common.get_skinned_data_sets(selection)
    common.update_skinned_data_sets(joints, meshes, skin_clusters, transforms)
    if not joints and not meshes and not skin_clusters:
        cmds.error("No joints or meshes to convert to a proxy.")

    hierarchy = _solve_joint_hierarchy(joints)
    clone_pairing = {}
    root = Node(cmds.createNode("transform", name="{}:root".format(CLONE_PREFIX)))
    ProxyRoot.add_data(root).rootType.set(0)
    skeleton_root = Node(
        cmds.createNode(
            "transform",
            name="{}:skel_root".format(CLONE_PREFIX),
            parent=root.name(),
        )
    )
    ProxyRoot.add_data(skeleton_root).rootType.set(1)
    _clone_joints(hierarchy.get(None, []), skeleton_root, hierarchy, clone_pairing)

    cloned_roots = [clone_pairing[joint] for joint in hierarchy.get(None, [])]
    if cloned_roots:
        cmds.makeIdentity(
            mayautil.names(cloned_roots), apply=True, translate=False, rotate=True, scale=False
        )
    meshes_root = Node(
        cmds.createNode(
            "transform", name="{}:meshes".format(CLONE_PREFIX), parent=root.name()
        )
    )
    ProxyRoot.add_data(meshes_root).rootType.set(2)
    skinned_root = Node(
        cmds.createNode(
            "transform",
            name="{}:skinned_meshes".format(CLONE_PREFIX),
            parent=root.name(),
        )
    )
    ProxyRoot.add_data(skinned_root).rootType.set(3)
    cmds.setAttr(skinned_root.name() + ".inheritsTransform", False)

    start_time = time.perf_counter()
    _clone_meshes(meshes, meshes_root, skinned_root, clone_pairing)
    print("Proxy creation took {:.4f} seconds.".format(time.perf_counter() - start_time))

    empty_children = [
        child
        for child in mayautil.children(root)
        if not mayautil.children(child)
    ]
    if empty_children:
        cmds.delete(mayautil.names(empty_children))
    constraints = [
        child
        for child in mayautil.descendants([root])
        if cmds.objectType(child.name(), isAType="constraint")
    ]
    if constraints:
        cmds.delete(mayautil.names(constraints))
    cmds.select(root.name(), replace=True)
    return True


def constrain_proxy():
    data_nodes = cg3dguru.udata.Utils.get_nodes_with_data(data_class=ProxyRoot)
    joint_roots = [data for data in data_nodes if data.rootType.get() == 1]
    if not joint_roots:
        cmds.error("No proxy data found.")
    if len(joint_roots) > 1:
        cmds.warning("Multiple proxy rigs found; using the first one.")
    maintain_offset = preferences.get().derig_maintain_offset
    descendants = mayautil.descendants([joint_roots[0].node()])
    proxy_data = cg3dguru.udata.Utils.get_nodes_with_data(
        descendants, data_class=ProxyData
    )
    for proxy in proxy_data:
        sources = proxy.proxySource.inputs()
        if sources:
            cmds.parentConstraint(
                sources[0].name(),
                proxy.node().name(),
                maintainOffset=maintain_offset,
            )


def sync_casc_id():
    selected_sets = common.get_selected_export_nodes()
    success, casc_ids = server.send_and_listen("cg3dmaya.get_selected_ids()")
    if not success:
        cmds.error("Couldn't establish communication with Cascadeur")
    if len(selected_sets) != 1 or len(casc_ids) != 1:
        cmds.error("Select exactly one export set in Maya and Cascadeur")
    result = cmds.confirmDialog(
        title="Cascadeur Bridge",
        message=(
            "Warning: Syncing IDs should only be done if you understand the risks.\n"
            "See documentation for more details.\nContinue?"
        ),
        button=["Yes", "Cancel"],
        defaultButton="Yes",
        cancelButton="Cancel",
        dismissString="Cancel",
    )
    if result == "Yes":
        identifier = selected_sets[0].cscDataId
        identifier.unlock()
        identifier.set(casc_ids[0])
        identifier.lock()
        om.MGlobal.displayInfo("ID Synced")


def derig_selection():
    if not cmds.ls(selection=True):
        cmds.warning("Please select meshes and/or joints for cloning")
        return
    data_name, ok = QInputDialog.getText(None, "Name this character", "Unique namespace")
    if not ok:
        return None
    global CLONE_PREFIX
    CLONE_PREFIX = data_name
    if _derig_selection():
        create_export_set(
            "{}:{}_CSC_EXPORT".format(CLONE_PREFIX, CLONE_PREFIX),
            auto_add_selected=True,
        )


def hik_def_from_proxy():
    def connected_hik_attribute(source_node, destination_node):
        source_plug = source_node.name() + ".Character"
        if not cmds.objExists(source_plug):
            return None
        pairs = cmds.listConnections(
            source_plug,
            connections=True,
            destination=True,
            source=False,
            plugs=True,
        ) or []
        for _, destination in zip(pairs[0::2], pairs[1::2]):
            node, attribute = destination.split(".", 1)
            if node == destination_node:
                return attribute
        return None

    active_character = hik.get_current_character()
    if active_character == "None":
        cmds.warning("Please select a character from the HIK window.")
        return
    active_character = active_character.split("(")[0]
    node_indices = hik.get_node_index_mapping()
    proxy_data = cg3dguru.udata.Utils.get_nodes_with_data(
        mayautil.ls(type="joint"), data_class=ProxyData
    )
    if not proxy_data:
        cmds.warning("Couldn't find any proxy joints.")
        return

    source_indices = {}
    for proxy in proxy_data:
        sources = proxy.proxySource.inputs()
        if not sources:
            continue
        attribute = connected_hik_attribute(proxy.node(), active_character)
        if attribute in node_indices:
            source_indices[sources[0].name()] = node_indices[attribute]
    if not source_indices:
        cmds.warning("Couldn't find proxy joints from the active HIK character.")
        return

    current_characters = set(cmds.ls(type="HIKCharacterNode") or [])
    mel.eval("hikCreateDefinition")
    new_characters = [
        node
        for node in (cmds.ls(type="HIKCharacterNode") or [])
        if node not in current_characters
    ]
    if len(new_characters) != 1:
        cmds.error("Failed to create a new character definition.")
    target = new_characters[0]
    for joint_name, index in source_indices.items():
        mel.eval('setCharacterObject("{}", "{}", {}, 0)'.format(joint_name, target, index))
    if mel.eval("workspaceControl -query -raise hikCharacterControlsDock") != 1:
        mel.eval("hikToggleWidget")
