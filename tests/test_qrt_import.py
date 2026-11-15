from __future__ import annotations

import sys
import unittest

from tests._support import SRC_ROOT, installed_modules, load_module, make_module, make_package


class QRigImportMappingTests(unittest.TestCase):
    def setUp(self):
        self.module = load_module(
            "_qrt_mapping_test", SRC_ROOT / "core" / "casc_qrt.py"
        )

    def tearDown(self):
        sys.modules.pop("_qrt_mapping_test", None)

    def test_qrt_semantics_map_to_hik_slots(self):
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
                            ],
                        }
                    ],
                }
            ]
        }

        mapped = self.module._qrt_hik_entries(document)

        self.assertEqual("pelvis", mapped["Hips"]["Joint name"])
        self.assertEqual("spine_01", mapped["Spine"]["Joint name"])
        self.assertEqual("spine_03", mapped["Spine1"]["Joint name"])
        self.assertEqual("neck_01", mapped["Neck"]["Joint name"])

    def test_twist_bones_map_in_order_to_hik_roll_slots(self):
        document = {
            "Document": [
                {
                    "Title": "Twist bones",
                    "Sections": [
                        {
                            "Section": "Left arm",
                            "Names": [
                                {"Bone name": "arm_l", "Joint name": "upperarm_twist_01_l"},
                                {"Bone name": "arm_l", "Joint name": "upperarm_twist_02_l"},
                                {"Bone name": "forearm_l", "Joint name": "lowerarm_twist_01_l"},
                            ],
                        }
                    ],
                }
            ]
        }

        mapped = self.module._qrt_hik_entries(document)

        self.assertEqual(
            "upperarm_twist_01_l",
            mapped["LeafLeftArmRoll1"]["Joint name"],
        )
        self.assertEqual(
            "upperarm_twist_02_l",
            mapped["LeafLeftArmRoll2"]["Joint name"],
        )
        self.assertEqual(
            "lowerarm_twist_01_l",
            mapped["LeafLeftForeArmRoll1"]["Joint name"],
        )

    def test_joint_paths_disambiguate_duplicate_short_names(self):
        entry = {
            "Joint name": "hand",
            "Joint path": ["root", "right_arm"],
        }
        joints = ["|root|left_arm|hand", "|root|right_arm|hand"]

        self.assertEqual(
            "|root|right_arm|hand",
            self.module._match_imported_joint(entry, joints),
        )

    def test_spline_ik_expands_all_intermediate_spine_slots(self):
        parents = {
            "|root|pelvis": "|root",
            "|root|pelvis|spine_01": "|root|pelvis",
            "|root|pelvis|spine_01|spine_02": "|root|pelvis|spine_01",
            "|root|pelvis|spine_01|spine_02|spine_03": "|root|pelvis|spine_01|spine_02",
            "|root|pelvis|spine_01|spine_02|spine_03|neck_01": "|root|pelvis|spine_01|spine_02|spine_03",
        }
        cmds = make_module(
            "maya.cmds",
            listRelatives=lambda node, **kwargs: [parents[node]] if node in parents else [],
        )
        maya = make_package("maya", cmds=cmds)
        joints = list(parents)
        mapping = {
            "Hips": "|root|pelvis",
            "Spine": "|root|pelvis|spine_01",
            "Spine1": "|root|pelvis|spine_01|spine_02|spine_03",
            "Neck": "|root|pelvis|spine_01|spine_02|spine_03|neck_01",
        }
        metadata = {
            "spline_ik_chains": [["spine_01", "spine_02", "spine_03"]]
        }

        with installed_modules({"maya": maya, "maya.cmds": cmds}):
            result = self.module._apply_spline_ik(mapping, metadata, joints)

        self.assertEqual("|root|pelvis|spine_01", result["Spine"])
        self.assertEqual("|root|pelvis|spine_01|spine_02", result["Spine1"])
        self.assertEqual(
            "|root|pelvis|spine_01|spine_02|spine_03",
            result["Spine2"],
        )


if __name__ == "__main__":
    unittest.main()
