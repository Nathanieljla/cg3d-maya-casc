"""FBX import/export helpers using Maya's native command layer."""

import json
import os

from maya import cmds, mel

import cg3dguru.utils


EXPORT_ANIM = 0x01
EXPORT_RIG = 0x01 << 1
EXPORT_ANIM_RIG = EXPORT_ANIM | EXPORT_RIG


def _mel_value(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return json.dumps(value)
    return str(value)


def _fbx(command, value=None, flag="v"):
    statement = command
    if value is not None:
        if flag:
            statement += " -{} {}".format(flag, _mel_value(value))
        else:
            statement += " {}".format(_mel_value(value))
    return mel.eval(statement + ";")


def _configure_export(export_type, bake_animations, remove_namespaces):
    start = int(cmds.playbackOptions(query=True, animationStartTime=True))
    end = int(cmds.playbackOptions(query=True, animationEndTime=True))
    export_animation = bool(export_type & EXPORT_ANIM)
    export_rig = bool(export_type & EXPORT_RIG)

    print("export animations:{} export rig:{}".format(export_animation, export_rig))
    print("start:{} end:{}".format(start, end))

    _fbx("FBXResetExport")
    _fbx("FBXExportUpAxis", cmds.upAxis(query=True, axis=True), flag=None)
    _fbx("FBXExportBakeComplexStart", start)
    _fbx("FBXExportBakeComplexEnd", end)
    _fbx("FBXExportBakeComplexAnimation", export_animation and bake_animations)
    _fbx("FBXExportBakeResampleAnimation", True)
    _fbx("FBXExportSkins", export_rig)
    _fbx("FBXExportShapes", True)
    _fbx("FBXExportConstraints", False)
    _fbx("FBXExportInputConnections", False)
    _fbx("FBXExportCameras", False)
    _fbx("FBXExportLights", False)
    _fbx("FBXExportInAscii", remove_namespaces)
    _fbx("FBXExportAnimationOnly", not export_rig)


def set_export_options(
    export_type, bake_animations=True, remove_namespaces=False
):
    _configure_export(export_type, bake_animations, remove_namespaces)


def export(
    filename,
    export_type=EXPORT_ANIM_RIG,
    bake_animations=True,
    remove_namespaces=False,
    include_children=True,
):
    _configure_export(export_type, bake_animations, remove_namespaces)
    _fbx("FBXExportSkeletonDefinitions", True)
    _fbx("FBXExportIncludeChildren", include_children)
    _fbx("FBXExport", str(filename).replace("\\", "/"), flag="f")

    if os.path.exists(filename) and remove_namespaces:
        cg3dguru.utils.remove_namespaces(filename)


def export_anim(filename, *args, **kwargs):
    export(filename, export_type=EXPORT_ANIM_RIG, *args, **kwargs)


def export_rig(filename, *args, **kwargs):
    export(filename, export_type=EXPORT_RIG, *args, **kwargs)


def import_fbx(filepath):
    _fbx("FBXImportMode", "merge")
    _fbx("FBXImportFillTimeline", True)
    _fbx("FBXImportSkins", True)
    _fbx("FBXImport", str(filepath).replace("\\", "/"), flag="f")
