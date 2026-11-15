"""Release smoke tests executed by Maya's mayapy interpreter."""

from __future__ import annotations

import os
import json
import pathlib
import sys
import tempfile
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
CASC_SRC = REPO_ROOT / "src"
CORE_SRC = pathlib.Path(
    os.environ.get(
        "CG3D_MAYA_CORE_SRC",
        REPO_ROOT.parent / "cg3d-maya-core" / "src",
    )
).resolve()
CASCADEUR_SITE = CASC_SRC / "cg3dcasc" / "casc-site"

for source_root in (str(CASC_SRC), str(CORE_SRC), str(CASCADEUR_SITE)):
    if source_root not in sys.path:
        sys.path.insert(0, source_root)

import maya.standalone

maya.standalone.initialize(name="python")

from maya import cmds

import cg3dcasc
import cg3dguru
from cg3dcasc import preferences
from cg3dcasc.core import casc_export, casc_qrt, fbx, materials, utils
from cg3dcasc.core import maya as mayautil
from cg3dcasc.core.udata import CascExportData, QRigData
from cg3dguru.maya import Node


def _new_scene():
    cmds.file(new=True, force=True)
    preferences._PREFS_INSTANCE = preferences.new()


def _under(path, root):
    try:
        pathlib.Path(path).resolve().relative_to(pathlib.Path(root).resolve())
        return True
    except ValueError:
        return False


class MayaCleanProcessSmokeTests(unittest.TestCase):
    def setUp(self):
        _new_scene()

    def test_imports_development_checkout_without_pymel(self):
        self.assertTrue(_under(cg3dcasc.__file__, CASC_SRC))
        self.assertTrue(_under(cg3dguru.__file__, CORE_SRC))
        self.assertFalse(any(name == "pymel" or name.startswith("pymel.") for name in sys.modules))

    def test_node_handles_disambiguate_duplicate_short_names(self):
        left = cmds.createNode("transform", name="left")
        right = cmds.createNode("transform", name="right")
        left_body = cmds.createNode("transform", name="body", parent=left)
        # Capture the unique DAG path before creating the duplicate. Maya's
        # createNode return value is only the short name at this point.
        left_body = cmds.ls(left_body, long=True)[0]
        right_body = cmds.createNode("transform", name="body", parent=right)
        right_body = cmds.ls(right_body, long=True)[0]

        left_handle = Node(left_body)
        right_handle = Node(right_body)

        self.assertNotEqual(left_handle, right_handle)
        with self.assertRaises(ValueError):
            Node("body")
        cmds.rename(left_handle.name(), "renamedBody")
        self.assertTrue(left_handle.name().endswith("|renamedBody"))
        self.assertTrue(right_handle.name().endswith("|body"))

    def test_export_data_defaults_to_embed_and_latest(self):
        export_set, data = CascExportData.create_node(nodeType="objectSet")

        self.assertTrue(cmds.objExists(export_set.name()))
        self.assertEqual(CascExportData.EMBED_TEXTURES, CascExportData.get_texture_mode(data))
        self.assertTrue(CascExportData.get_embed_textures(data))
        self.assertFalse(CascExportData.references_textures(data))
        self.assertEqual(CascExportData.LATEST, data.export_version.get())
        self.assertTrue(data.dynamicSet.get())

        data.embedTextures.set(CascExportData.REFERENCE_TEXTURES)
        self.assertTrue(CascExportData.references_textures(data))

    def test_export_set_fbx_round_trip_excludes_unrelated_sibling(self):
        root = cmds.createNode("transform", name="characterRoot")
        kept = cmds.polyCube(name="keptMesh")[0]
        excluded = cmds.polyCube(name="excludedMesh")[0]
        cmds.parent(kept, excluded, root)

        export_set, data = CascExportData.create_node(nodeType="objectSet")
        cmds.sets(kept, addElement=export_set.name())

        with tempfile.TemporaryDirectory() as directory:
            export_dir = pathlib.Path(directory)
            casc_export._export_data(data, export_dir, False, True)
            exported = list(export_dir.glob("*.fbx"))
            self.assertEqual(1, len(exported))

            cmds.file(new=True, force=True)
            fbx.import_fbx(exported[0])

        self.assertTrue(cmds.ls("keptMesh", long=True))
        self.assertFalse(cmds.ls("excludedMesh", long=True))

    def test_reference_material_uses_absolute_path_and_packed_channel(self):
        with tempfile.TemporaryDirectory() as directory:
            project = pathlib.Path(directory)
            source_images = project / "sourceimages"
            source_images.mkdir()
            texture = source_images / "packed.png"
            texture.write_bytes(b"smoke-test-placeholder")
            cmds.workspace(str(project), openWorkspace=True)

            mesh = cmds.polyCube(name="materialMesh")[0]
            shader = cmds.shadingNode("standardSurface", asShader=True, name="smokeMaterial")
            shading_group = cmds.sets(
                renderable=True,
                noSurfaceShader=True,
                empty=True,
                name="smokeMaterialSG",
            )
            cmds.connectAttr(shader + ".outColor", shading_group + ".surfaceShader")
            cmds.sets(mesh, edit=True, forceElement=shading_group)
            file_node = cmds.shadingNode("file", asTexture=True, name="packedTexture")
            cmds.setAttr(file_node + ".fileTextureName", "/sourceimages/packed.png", type="string")
            cmds.connectAttr(file_node + ".outColorG", shader + ".specularRoughness")

            export_set, data = CascExportData.create_node(nodeType="objectSet")
            cmds.sets(mesh, addElement=export_set.name())
            data.embedTextures.set(CascExportData.REFERENCE_TEXTURES)
            payload = materials.build_export_data(data, [mayautil.Node(mesh)])

        properties = payload["meshes"][0]["materials"][0]["properties"]
        self.assertEqual(1, properties["roughness_channel"])
        texture_path = pathlib.Path(properties["roughness_map"])
        self.assertTrue(texture_path.is_absolute())
        self.assertEqual("packed.png", texture_path.name)

    def test_proxy_skin_deforms_from_cloned_skeleton(self):
        cmds.select(clear=True)
        root_joint = cmds.joint(name="rootJoint", position=(0, 0, 0))
        child_joint = cmds.joint(name="childJoint", position=(0, 2, 0))
        cmds.select(clear=True)
        mesh = cmds.polyCube(name="skinnedMesh", height=4)[0]
        cmds.skinCluster(root_joint, child_joint, mesh, toSelectedBones=True)

        utils.CLONE_PREFIX = "SMOKE_PROXY"
        cmds.select(mesh, replace=True)
        self.assertTrue(utils._derig_selection())

        proxy_meshes = [
            item
            for item in (cmds.ls("SMOKE_PROXY:*", type="mesh", long=True) or [])
            if not cmds.getAttr(item + ".intermediateObject")
        ]
        proxy_joints = cmds.ls("SMOKE_PROXY:*", type="joint", long=True) or []
        self.assertEqual(1, len(proxy_meshes))
        self.assertEqual(2, len(proxy_joints))
        proxy_transform = cmds.listRelatives(proxy_meshes[0], parent=True, fullPath=True)[0]
        history = cmds.listHistory(proxy_transform) or []
        proxy_clusters = cmds.ls(history, type="skinCluster") or []
        self.assertEqual(1, len(proxy_clusters))
        influences = cmds.skinCluster(proxy_clusters[0], query=True, influence=True) or []
        self.assertTrue(influences)
        self.assertTrue(all(item.split("|")[-1].startswith("SMOKE_PROXY:") for item in influences))

        before = cmds.exactWorldBoundingBox(proxy_transform)
        proxy_root = next(item for item in proxy_joints if item.endswith(":rootJoint"))
        cmds.setAttr(proxy_root + ".translateX", 2.0)
        after = cmds.exactWorldBoundingBox(proxy_transform)
        before_center = (before[0] + before[3]) / 2.0
        after_center = (after[0] + after[3]) / 2.0
        # The cube is split between the two influences, so moving the root by
        # two units moves its weighted centre by one. Any meaningful movement
        # proves the cloned joint plugs drive the cloned skinCluster.
        self.assertGreater(after_center - before_center, 0.5)

    def test_qrig_import_builds_hik_definition_with_full_spline_spine(self):
        cmds.select(clear=True)
        joint_names = []
        for name in (
            "pelvis",
            "spine_01",
            "spine_02",
            "spine_03",
            "neck_01",
            "head",
        ):
            joint_names.append(cmds.joint(name=name))

        cmds.select("spine_03", replace=True)
        clavicle = cmds.joint(name="clavicle_l")
        upper_arm = cmds.joint(name="upperarm_l")
        lower_arm = cmds.joint(name="lowerarm_l")
        hand = cmds.joint(name="hand_l")
        cmds.select(upper_arm, replace=True)
        upper_twist_one = cmds.joint(name="upperarm_twist_01_l")
        cmds.select(upper_arm, replace=True)
        upper_twist_two = cmds.joint(name="upperarm_twist_02_l")
        joint_names.extend(
            [
                clavicle,
                upper_arm,
                lower_arm,
                hand,
                upper_twist_one,
                upper_twist_two,
            ]
        )
        joint_paths = cmds.ls(joint_names, long=True, type="joint") or []
        export_set, unused_data = CascExportData.create_node(nodeType="objectSet")

        document = {
            "Document": [
                {
                    "Title": "Body",
                    "Sections": [
                        {
                            "Section": "Body",
                            "Names": [
                                {"Bone name": "pelvis", "Joint name": "pelvis"},
                                {"Bone name": "stomach", "Joint name": "spine_01"},
                                {"Bone name": "chest", "Joint name": "spine_03"},
                                {"Bone name": "neck", "Joint name": "neck_01"},
                                {"Bone name": "head", "Joint name": "head"},
                                {"Bone name": "clavicle_l", "Joint name": "clavicle_l"},
                                {"Bone name": "arm_l", "Joint name": "upperarm_l"},
                                {"Bone name": "forearm_l", "Joint name": "lowerarm_l"},
                                {"Bone name": "hand_l", "Joint name": "hand_l"},
                            ],
                        }
                    ],
                },
                {
                    "Title": "Twist bones",
                    "Sections": [
                        {
                            "Section": "Left arm",
                            "Names": [
                                {
                                    "Bone name": "arm_l",
                                    "Joint name": "upperarm_twist_01_l",
                                },
                                {
                                    "Bone name": "arm_l",
                                    "Joint name": "upperarm_twist_02_l",
                                },
                            ],
                        }
                    ],
                }
            ]
        }
        metadata = {
            "version": 1,
            "spline_ik_chains": [["spine_01", "spine_02", "spine_03"]],
        }

        with tempfile.TemporaryDirectory() as directory:
            qrig_path = pathlib.Path(directory) / "character.qrigcasc"
            hikmap_path = pathlib.Path(directory) / "character.hikmap"
            qrig_path.write_text(json.dumps(document), encoding="utf-8")
            hikmap_path.write_text(json.dumps(metadata), encoding="utf-8")
            character = casc_qrt.import_qrig_character(
                qrig_path,
                hikmap_path,
                joint_paths,
                export_set,
            )
            second_character = casc_qrt.import_qrig_character(
                qrig_path,
                hikmap_path,
                joint_paths,
                export_set,
            )

        self.assertEqual("HIKCharacterNode", cmds.nodeType(character.name()))
        qrig_data = QRigData.get_data(export_set)
        self.assertIsNotNone(qrig_data)
        self.assertTrue(qrig_data.leftArmTwist.exists())
        for slot, joint in zip(("Spine", "Spine1", "Spine2"), joint_paths[1:4]):
            inputs = cmds.listConnections(
                character.name() + "." + slot,
                source=True,
                destination=False,
                type="joint",
            ) or []
            self.assertEqual([joint.rsplit("|", 1)[-1]], inputs)
        for slot, joint in (
            ("LeafLeftArmRoll1", upper_twist_one),
            ("LeafLeftArmRoll2", upper_twist_two),
        ):
            inputs = cmds.listConnections(
                character.name() + "." + slot,
                source=True,
                destination=False,
                type="joint",
            ) or []
            self.assertEqual([joint], inputs)

        self.assertEqual(character, second_character)
        self.assertEqual(1, len(cmds.ls(type="HIKCharacterNode") or []))
        self.assertFalse(cmds.ls(type="HIKControlSetNode") or [])


def main():
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(MayaCleanProcessSmokeTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    finally:
        maya.standalone.uninitialize()
