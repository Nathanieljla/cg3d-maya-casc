"""
maya_material_data.py
=====================
``MayaMaterialData`` — a ``BaseMaterialData`` subclass that extracts material
properties from Maya meshes via ``pymel``.

Supported shader types
----------------------
- **aiStandardSurface** (Arnold)
- **lambert**
- **blinn**
- **phong**
- **phongE**

All attribute names are normalised to canonical names at extraction time
(see ``BaseMaterialData`` for the canonical vocabulary).
"""

from __future__ import annotations

import pathlib
from typing import Any, Dict, List, Optional, Set, Tuple

import pymel.core as pm

# Import BaseMaterialData — adjust the import path as needed for your
# packaging setup.  The two-try block mirrors the pattern in core.py.
try:
    from cg3dcasc.material_data import (
        BaseMaterialData,
        MaterialConverter,
        FilamentMaterialData,
    )
except ImportError:
    from material_data import (
        BaseMaterialData,
        MaterialConverter,
        FilamentMaterialData,
    )


# ---------------------------------------------------------------------------
# Attribute mapping tables: (shader_type, maya_attr) → canonical_attr
# ---------------------------------------------------------------------------

# Each shader type declares which Maya attributes to query and what canonical
# name they map to.  Order matters — attributes are queried in the order
# listed.
#
# The dict is keyed by shader type name (the string returned by
# ``pm.nodeType(shader)``).  Values are lists of (maya_attr, canonical_name).

_SHADER_ATTR_MAP: Dict[str, List[Tuple[str, str]]] = {
    # ── Arnold Standard Surface ──────────────────────────────────────────
    "aiStandardSurface": [
        ("baseColor",          "BaseColor"),
        ("metalness",          "Metallic"),
        ("specularColor",      "Specular"),
        ("specularRoughness",  "Roughness"),
        ("normalCamera",       "Normal"),
        ("emissionColor",      "EmissiveColor"),
        ("opacity",            "Opacity"),
        ("coat",               "Coat"),
        ("coatRoughness",      "CoatRoughness"),
    ],
    # ── Lambert ──────────────────────────────────────────────────────────
    "lambert": [
        ("color",              "BaseColor"),
        ("transparency",       "Transparency"),
        ("ambientColor",       "AmbientOcclusion"),
        ("incandescence",      "EmissiveColor"),
        ("normalCamera",       "Normal"),
    ],
    # ── Blinn ────────────────────────────────────────────────────────────
    "blinn": [
        ("color",              "BaseColor"),
        ("transparency",       "Transparency"),
        ("ambientColor",       "AmbientOcclusion"),
        ("incandescence",      "EmissiveColor"),
        ("normalCamera",       "Normal"),
        ("specularColor",      "Specular"),
        ("eccentricity",       "Roughness"),
        ("specularRollOff",    "SpecularRollOff"),
    ],
    # ── Phong ────────────────────────────────────────────────────────────
    "phong": [
        ("color",              "BaseColor"),
        ("transparency",       "Transparency"),
        ("ambientColor",       "AmbientOcclusion"),
        ("incandescence",      "EmissiveColor"),
        ("normalCamera",       "Normal"),
        ("specularColor",      "Specular"),
        ("cosinePower",        "Roughness"),  # will need inversion at convert time
    ],
    # ── PhongE ───────────────────────────────────────────────────────────
    "phongE": [
        ("color",              "BaseColor"),
        ("transparency",       "Transparency"),
        ("ambientColor",       "AmbientOcclusion"),
        ("incandescence",      "EmissiveColor"),
        ("normalCamera",       "Normal"),
        ("highlightSize",      "Roughness"),
        ("roughness",          "SpecularRollOff"),
    ],
}


# ---------------------------------------------------------------------------
# MayaMaterialData
# ---------------------------------------------------------------------------

class MayaMaterialData(BaseMaterialData):
    """Extract and store material data from Maya meshes.

    Usage::

        selected = pm.selected()
        data = MayaMaterialData.from_mesh(selected)
        data.save("/path/to/materials.json")
    """

    # Expose the mapping so callers can inspect / extend it at runtime
    SHADER_ATTR_MAP = _SHADER_ATTR_MAP

    @classmethod
    def from_mesh(cls, mesh_objs: Any) -> "MayaMaterialData":
        """Parse materials from one or more Maya mesh transforms / shapes.

        Parameters
        ----------
        mesh_objs :
            A single ``PyNode``, a list of ``PyNode`` objects, or anything
            accepted by ``pm.ls(…, dagObjects=True)``.

        Returns
        -------
        MayaMaterialData
            Populated instance with canonical attribute names.
        """
        if not isinstance(mesh_objs, (list, tuple)):
            mesh_objs = [mesh_objs]

        data = cls()

        # Resolve to shape nodes
        shapes: List[pm.PyNode] = []
        for obj in mesh_objs:
            if obj.type() == "mesh":
                shapes.append(obj)
            else:
                shapes.extend(pm.listRelatives(obj, shapes=True, noIntermediate=True) or [])

        if not shapes:
            pm.warning("MayaMaterialData: no mesh shapes found in the provided objects.")
            return data

        # Use the first transform's name as mesh_name (or combine)
        parents = list({s.getParent().name() for s in shapes})
        data.mesh_name = parents[0] if len(parents) == 1 else "|".join(sorted(parents))

        # Iterate shapes → shading engines → shaders
        seen_shaders: Set[str] = set()
        for shape in shapes:
            sgs = pm.listConnections(shape, type="shadingEngine") or []
            for sg in sgs:
                shaders = pm.listConnections(
                    f"{sg}.surfaceShader", source=True, destination=False
                ) or []
                for shader in shaders:
                    shader_name = shader.name()
                    if shader_name in seen_shaders:
                        continue
                    seen_shaders.add(shader_name)

                    attrs = cls._extract_shader(shader)
                    if attrs:
                        data.materials[shader_name] = attrs

        return data

    # -- private extraction helpers -----------------------------------------

    @classmethod
    def _extract_shader(cls, shader: pm.PyNode) -> Optional[Dict[str, Dict[str, Any]]]:
        """Extract canonical attributes from a single shader node."""
        shader_type = pm.nodeType(shader)
        attr_list = _SHADER_ATTR_MAP.get(shader_type)

        if attr_list is None:
            pm.warning(
                f"MayaMaterialData: unsupported shader type '{shader_type}' "
                f"on '{shader.name()}' — skipping."
            )
            return None

        attributes: Dict[str, Dict[str, Any]] = {}
        for maya_attr, canonical_name in attr_list:
            if not hasattr(shader, maya_attr):
                continue
            entry = cls._read_attribute(shader, maya_attr)
            if entry is not None:
                attributes[canonical_name] = entry

        return attributes

    @classmethod
    def _read_attribute(
        cls, shader: pm.PyNode, maya_attr: str
    ) -> Optional[Dict[str, Any]]:
        """Read a single attribute from *shader* and return a canonical entry.

        Returns ``None`` if the attribute doesn't exist or is unreadable.
        """
        attr_plug = getattr(shader, maya_attr, None)
        if attr_plug is None:
            return None

        # 1. Check for connected texture file node(s)
        texture_path = cls._find_texture(attr_plug)
        if texture_path:
            return {"type": "texture", "value": [texture_path]}

        # 2. Fallback to reading the constant value
        try:
            raw = attr_plug.get()
        except Exception:
            return None

        return cls._constant_entry(raw)

    @classmethod
    def _find_texture(cls, attr_plug) -> Optional[str]:
        """Walk upstream connections from *attr_plug* looking for a ``file``
        texture node.  Returns the file path string or ``None``.
        """
        # Direct connections first
        connections = pm.listConnections(attr_plug, source=True, destination=False) or []

        # Also look deeper — some setups chain through utility nodes
        file_nodes = pm.findType(connections, type="file", forward=False, deep=True) if connections else []

        if not file_nodes:
            # Try finding file nodes among direct connections themselves
            file_nodes = [c for c in connections if pm.nodeType(c) == "file"]

        if not file_nodes:
            return None

        # Use the first file node found
        file_node = pm.PyNode(file_nodes[0])
        filepath = file_node.fileTextureName.get()
        if not filepath:
            return None

        # Normalise path separators
        return filepath.replace("\\", "/")

    @classmethod
    def _constant_entry(cls, raw: Any) -> Optional[Dict[str, Any]]:
        """Convert a raw Maya attribute value into a canonical constant entry."""
        if raw is None:
            return None

        # PyMel colour / vector types are tuple-like
        if isinstance(raw, (tuple, list)):
            values = [float(v) for v in raw]
            if len(values) == 1:
                return {"type": "scalar", "value": values[0]}
            return {"type": "vector", "value": values}

        if isinstance(raw, (int, float)):
            return {"type": "scalar", "value": float(raw)}

        # Some attributes return True/False
        if isinstance(raw, bool):
            return {"type": "scalar", "value": 1.0 if raw else 0.0}

        return None


# ---------------------------------------------------------------------------
# Register Maya → Filament converter
# ---------------------------------------------------------------------------
MaterialConverter.register(
    MayaMaterialData,
    FilamentMaterialData,
    {k: v for k, v in FilamentMaterialData.CANONICAL_TO_FILAMENT.items()},
)
