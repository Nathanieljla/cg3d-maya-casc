"""Script body executed inside a clean Cascadeur GUI process.

The local Cascadeur script server supplies ``scene``, ``ps`` and ``ARGS``.
The final ``result`` value is returned to the external runner as JSON.
"""

from __future__ import annotations

import importlib
import pathlib
import sys
import tempfile

import csc

site_root = pathlib.Path(ARGS["site_root"]).resolve()
if str(site_root) not in sys.path:
    sys.path.insert(0, str(site_root))

import cg3dmaya
from cg3dmaya import common, fbx as maya_fbx, maya_export, maya_import

# An existing development instance may have imported these modules before the
# checkout changed. Reload the workflow under test from the source path above.
maya_export = importlib.reload(maya_export)
cg3dmaya.export_character_and_rig = maya_export.export_character_and_rig

# The script runner's ``scene`` binding is the low-level csc.domain.Scene.
# Bridge commands consistently operate on pycsc's higher-level domain-scene
# wrapper, so exercise the same object the production entry points obtain.
scene = pycsc.get_current_scene().ds


def under(path, root):
    try:
        pathlib.Path(path).resolve().relative_to(pathlib.Path(root).resolve())
        return True
    except ValueError:
        return False


checks = []


def check(name, condition, detail=""):
    if not condition:
        raise AssertionError("{}: {}".format(name, detail or "condition was false"))
    checks.append(name)


check("development cg3dmaya checkout", under(cg3dmaya.__file__, site_root), cg3dmaya.__file__)
check(
    "no pymel loaded",
    not any(name == "pymel" or name.startswith("pymel.") for name in sys.modules),
)

expected_commands = {
    "add_selected": "Maya.Export Sets.Add Selected",
    "create_new_set": "Maya.Export Sets.Create New Set",
    "export_animation": "Maya.Export Animation",
    "export_character_and_rig": "Maya.Export Character and Rig",
    "remove_selected": "Maya.Export Sets.Remove Selected",
    "select_set_members": "Maya.Export Sets.Select Set Members",
    "sync_ids": "Maya.Export Sets.Sync Maya ID",
}
for module_name, expected_name in expected_commands.items():
    module = importlib.import_module("cg3dcmds." + module_name)
    check(module_name + " command name", module.command_name() == expected_name)
    check(module_name + " menu name", module.name() == expected_name)


created = {}


def make_roots(edit_scene):
    created["one"] = edit_scene.create_object("SmokeRootOne", simple=True)
    created["two"] = edit_scene.create_object("SmokeRootTwo", simple=True)


check("create smoke roots edit", bool(scene.edit("Create smoke roots", make_roots)))
export_set = common.create_export_set(scene, {created["one"]})
check("create export set", export_set is not None)
all_sets, selected_sets = common.get_export_sets(scene)
check("discover export set", export_set in all_sets)
check("initial set membership", common.get_set_members(export_set) == {created["one"]})
common._add_to_set(scene, {created["two"]}, export_set)
check(
    "add set membership",
    common.get_set_members(export_set) == {created["one"], created["two"]},
)

identifier = next(iter(common.get_ids({export_set})))
check("export id is present", bool(identifier))
common._sync_id(scene, "clean-process-smoke-id", export_set)
check(
    "sync export id",
    set(common.get_ids({export_set})) == {"clean-process-smoke-id"},
)
check("select set members", common._select_set_members(scene, export_set))

with tempfile.TemporaryDirectory() as directory:
    original_gettempdir = maya_export.tempfile.gettempdir
    original_temp_dir = maya_export.temp_dir
    maya_export.tempfile.gettempdir = lambda: directory
    try:
        maya_export.temp_dir = pathlib.Path(directory) / "mayacasc"
        maya_export.temp_dir.mkdir()
        (maya_export.temp_dir / "old.fbx").write_bytes(b"old")
        media = maya_export.temp_dir / "old.fbm"
        media.mkdir()
        (media / "texture.png").write_bytes(b"old")
        maya_export._clean_export_location()
        check("clean file and fbm directory", list(maya_export.temp_dir.iterdir()) == [])
    finally:
        maya_export.temp_dir = original_temp_dir
        maya_export.tempfile.gettempdir = original_gettempdir

with tempfile.TemporaryDirectory() as directory:
    original_gettempdir = tempfile.gettempdir
    tempfile.gettempdir = lambda: directory
    try:
        check("embed update textures is a no-op", maya_import._load_materials(scene) is None)
    finally:
        tempfile.gettempdir = original_gettempdir

unreal_scene_path = pathlib.Path(ARGS.get("unreal_scene", ""))
unreal_details = {}
if unreal_scene_path.is_file():
    loaded = csc.app.get_application().get_data_source_manager().load_scene(
        str(unreal_scene_path)
    )
    check("load bundled Unreal scene", loaded, str(unreal_scene_path))
    unreal_scene = pycsc.get_current_scene().ds
    rig_infos = list(unreal_scene.get_behaviours("RigInfo"))
    check("Unreal scene has one RigInfo", len(rig_infos) == 1, len(rig_infos))
    rig_info = rig_infos[0]
    rig_joints = set(rig_info.related_joints.get())
    check("Unreal RigInfo has qrt_json", bool(rig_info.qrt_json.get().strip()))
    check("Unreal RigInfo has related joints", bool(rig_joints))
    export_content = maya_export._rig_export_content(unreal_scene, rig_info)
    influenced_meshes = export_content.difference(rig_joints)
    check("Unreal export includes influenced meshes", bool(influenced_meshes))
    previous_export_set = maya_export._matching_rig_export_set(
        unreal_scene,
        rig_info,
        export_content,
    )
    first_export_set = maya_export._get_or_create_rig_export_set(
        unreal_scene,
        rig_info,
        export_content,
    )
    second_export_set = maya_export._get_or_create_rig_export_set(
        unreal_scene,
        rig_info,
        export_content,
    )
    check(
        "character export reuses its matching set",
        first_export_set == second_export_set,
    )
    root_behaviour = first_export_set.get_behaviour_by_name(common.MAYA_ROOTS)
    export_selection = []
    hierarchy = importlib.import_module("common.hierarchy")
    for reference in root_behaviour.behaviours.get():
        export_selection.extend(
            hierarchy.get_object_branch_inclusive(
                reference.object,
                reference.object.scene,
            )
        )
    export_selection = maya_export._with_required_ancestors(export_selection)
    check(
        "Manny export selection includes hidden parent transform",
        len(export_selection) > len(set(item.name for item in export_selection)),
    )
    check(
        "select Manny export content",
        bool(
            unreal_scene.edit(
                "Select clean-process character export content",
                maya_export._select_for_export,
                export_selection,
            )
        ),
    )
    with tempfile.TemporaryDirectory() as directory:
        fbx_path = pathlib.Path(directory) / "UE5_Manny.fbx"
        settings = csc.fbx.FbxSettings()
        settings.bake_animation = False
        maya_fbx.export_fbx(
            str(fbx_path),
            maya_fbx.FbxFilterType.SELECTED,
            settings,
        )
        check(
            "Manny selected content creates FBX",
            fbx_path.is_file() and fbx_path.stat().st_size > 0,
        )
    if previous_export_set is None:
        def remove_smoke_export_set(edit_scene):
            edit_scene.me.delete_objects([first_export_set])

        check(
            "remove temporary character export set",
            bool(
                unreal_scene.edit(
                    "Remove clean-process character export set",
                    remove_smoke_export_set,
                )
            ),
        )
    spline_chains = maya_export._spline_ik_chains(unreal_scene, rig_joints)
    check("Unreal rig exposes a spline spine", bool(spline_chains))
    check(
        "Unreal spline chain has intermediate spine joints",
        any(len(chain) > 2 for chain in spline_chains),
        spline_chains,
    )
    unreal_details = {
        "scene": str(unreal_scene_path),
        "rig_info": rig_info.object.name,
        "related_joint_count": len(rig_joints),
        "influenced_mesh_count": len(influenced_meshes),
        "spline_ik_chains": spline_chains,
    }

result = {
    "host": "Cascadeur",
    "module": str(pathlib.Path(cg3dmaya.__file__).resolve()),
    "checks": checks,
    "count": len(checks),
    "unreal": unreal_details,
}
