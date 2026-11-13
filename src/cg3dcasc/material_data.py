"""
material_data.py
================
Defines the abstract ``BaseMaterialData`` interface, the ``MaterialConverter``
registry for cross-application material transformation, and the
``FilamentMaterialData`` stub for Google Filament rendering targets.

Canonical attribute names
-------------------------
Every ``BaseMaterialData`` subclass normalises DCC-native attribute names into
a shared canonical vocabulary at *extraction* time.  This means converters
between any two subclasses that share the same canonical keys can reuse
identical mapping tables (or even an identity map).

Canonical names (case-sensitive):
    BaseColor, Metallic, Specular, Roughness, Normal, EmissiveColor,
    Opacity, AmbientOcclusion, Coat, CoatRoughness, Transparency,
    SpecularRollOff
"""

from __future__ import annotations

import json
import copy
from dataclasses import dataclass, field
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Set,
    Tuple,
    Type,
)


# ---------------------------------------------------------------------------
# BaseMaterialData
# ---------------------------------------------------------------------------

class BaseMaterialData:
    """Abstract base for DCC-specific material extractors.

    Subclasses **must** override ``from_mesh`` to populate ``self.materials``.

    ``materials`` schema::

        {
            "<material_name>": {
                "<CanonicalAttr>": {
                    "type": "texture" | "scalar" | "vector",
                    "value": <list|float|list[float]>
                },
                ...
            },
            ...
        }
    """

    def __init__(self, mesh_name: str = ""):
        self.mesh_name: str = mesh_name
        self.materials: Dict[str, Dict[str, Dict[str, Any]]] = {}

    # -- abstract -----------------------------------------------------------

    @classmethod
    def from_mesh(cls, mesh_obj: Any) -> "BaseMaterialData":
        """Parse materials from a DCC-specific mesh object.

        Subclasses must override this method.
        """
        raise NotImplementedError(
            f"{cls.__name__} must implement from_mesh()"
        )

    # -- serialisation ------------------------------------------------------

    def to_dict(self) -> dict:
        """Return the canonical dict representation."""
        return {
            "source_class": type(self).__name__,
            "mesh_name": self.mesh_name,
            "materials": self.materials,
        }

    def to_json(self, indent: int = 4) -> str:
        """Serialise to a formatted JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, data: dict) -> "BaseMaterialData":
        """Reconstruct a ``BaseMaterialData`` from a dict.

        Note: this returns a *base* instance (no DCC-specific behaviour).
        Useful for deserialising data that will be fed into a converter.
        The original ``source_class`` is preserved in ``self.source_class``
        so you can inspect which subclass produced the data.
        """
        instance = cls.__new__(cls)
        BaseMaterialData.__init__(instance)
        instance.source_class = data.get("source_class", cls.__name__)
        instance.mesh_name = data.get("mesh_name", "")
        instance.materials = data.get("materials", {})
        return instance

    @classmethod
    def from_json(cls, json_str: str) -> "BaseMaterialData":
        """Deserialise from a JSON string."""
        return cls.from_dict(json.loads(json_str))

    @classmethod
    def from_file(cls, path: str) -> "BaseMaterialData":
        """Load from a ``.json`` file on disk."""
        with open(path, "r", encoding="utf-8") as fh:
            return cls.from_json(fh.read())

    def save(self, path: str) -> None:
        """Write ``to_json()`` to *path*."""
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(self.to_json())

    # -- introspection ------------------------------------------------------

    def property_names(self) -> Set[str]:
        """Return the union of all canonical attribute names across every
        material in this data set."""
        names: Set[str] = set()
        for attrs in self.materials.values():
            names.update(attrs.keys())
        return names

    def __repr__(self) -> str:
        mat_count = len(self.materials)
        return (
            f"<{self.__class__.__name__} mesh={self.mesh_name!r} "
            f"materials={mat_count}>"
        )


# ---------------------------------------------------------------------------
# MaterialConversionReport
# ---------------------------------------------------------------------------

@dataclass
class MaterialConversionReport:
    """Records what happened during a ``MaterialConverter.convert()`` call.

    Attributes:
        source_type:     Class name of the source ``BaseMaterialData``.
        target_type:     Class name of the target ``BaseMaterialData``.
        mapped:          ``{mat_name: {src_attr: dst_attr}}`` – successfully
                         mapped properties.
        unmapped_source: ``{mat_name: [attr, …]}`` – source properties with
                         no target equivalent (data lost).
        unmapped_target: ``{mat_name: [attr, …]}`` – target properties that
                         received no value from the source.
        warnings:        Free-form warning strings collected during conversion
                         (e.g. value-transform issues, type mismatches).
    """

    source_type: str = ""
    target_type: str = ""
    mapped: Dict[str, Dict[str, str]] = field(default_factory=dict)
    unmapped_source: Dict[str, List[str]] = field(default_factory=dict)
    unmapped_target: Dict[str, List[str]] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)

    # -- helpers ------------------------------------------------------------

    @property
    def has_data_loss(self) -> bool:
        """``True`` if any source properties went unmapped."""
        return any(bool(v) for v in self.unmapped_source.values())

    def add_warning(self, message: str) -> None:
        """Append a human-readable warning."""
        self.warnings.append(message)

    # -- serialisation ------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "source_type": self.source_type,
            "target_type": self.target_type,
            "mapped": self.mapped,
            "unmapped_source": self.unmapped_source,
            "unmapped_target": self.unmapped_target,
            "warnings": self.warnings,
        }

    def to_json(self, indent: int = 4) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    def summary(self) -> str:
        """One-line human readable summary."""
        total_mapped = sum(len(v) for v in self.mapped.values())
        total_lost = sum(len(v) for v in self.unmapped_source.values())
        total_missing = sum(len(v) for v in self.unmapped_target.values())
        return (
            f"Conversion {self.source_type} → {self.target_type}: "
            f"{total_mapped} mapped, {total_lost} lost, "
            f"{total_missing} target-only, {len(self.warnings)} warnings"
        )


# ---------------------------------------------------------------------------
# Value transform helpers
# ---------------------------------------------------------------------------

def _identity(value: Any) -> Any:
    """Pass-through transform — used when no conversion is needed."""
    return value


def _invert_scalar(value: Any) -> Any:
    """Invert a scalar value (e.g. roughness ↔ glossiness).

    For textures this is a no-op (returns the value unchanged) since we can't
    invert an image path at serialisation time.
    """
    if isinstance(value, (int, float)):
        return 1.0 - float(value)
    # Lists (vectors) – invert each component
    if isinstance(value, list) and all(isinstance(v, (int, float)) for v in value):
        return [1.0 - float(v) for v in value]
    return value


# Pre-built transforms that consumers can reference by name
VALUE_TRANSFORMS: Dict[str, Callable] = {
    "identity": _identity,
    "invert": _invert_scalar,
}


# ---------------------------------------------------------------------------
# MaterialConverter
# ---------------------------------------------------------------------------

class MaterialConverter:
    """Transforms one ``BaseMaterialData`` into another using a property
    mapping table.

    Mapping format
    --------------
    The *mapping* dict maps **source canonical attr** → target info::

        {
            "BaseColor":     "baseColor",                # simple rename
            "Roughness":     ("roughness", "identity"),   # rename + named transform
            "Glossiness":    ("roughness", "invert"),      # rename + invert
            "Roughness":     ("roughness", my_callable),   # rename + custom callable
        }

    If the value is a plain string it is treated as ``(target_name, "identity")``.

    Value transforms are applied **only to constant values** (``"scalar"`` and
    ``"vector"`` types).  ``"texture"`` values are always copied as-is, and a
    warning is appended to the report noting that the texture could not be
    transformed.

    Registry
    --------
    Use ``MaterialConverter.register(...)`` / ``MaterialConverter.get(...)``
    to store and retrieve converters by ``(source_type, target_type)`` pair.
    """

    _registry: Dict[Tuple[Type, Type], "MaterialConverter"] = {}

    def __init__(
        self,
        source_type: Type[BaseMaterialData],
        target_type: Type[BaseMaterialData],
        mapping: Dict[str, Any],
    ):
        self.source_type = source_type
        self.target_type = target_type

        # Normalise mapping to {src_attr: (dst_attr, transform_fn)}
        self._mapping: Dict[str, Tuple[str, Callable]] = {}
        for src_attr, dst_info in mapping.items():
            if isinstance(dst_info, str):
                self._mapping[src_attr] = (dst_info, _identity)
            elif isinstance(dst_info, (list, tuple)) and len(dst_info) == 2:
                dst_name, transform = dst_info
                if isinstance(transform, str):
                    transform = VALUE_TRANSFORMS.get(transform, _identity)
                self._mapping[src_attr] = (dst_name, transform)
            else:
                raise ValueError(
                    f"Invalid mapping value for '{src_attr}': {dst_info!r}"
                )

    # -- registry -----------------------------------------------------------

    @classmethod
    def register(
        cls,
        source_type: Type[BaseMaterialData],
        target_type: Type[BaseMaterialData],
        mapping: Dict[str, Any],
    ) -> "MaterialConverter":
        """Create a converter, store it in the registry, and return it."""
        converter = cls(source_type, target_type, mapping)
        cls._registry[(source_type, target_type)] = converter
        return converter

    @classmethod
    def get(
        cls,
        source_type: Type[BaseMaterialData],
        target_type: Type[BaseMaterialData],
    ) -> Optional["MaterialConverter"]:
        """Look up a previously registered converter.  Returns ``None`` if
        no converter exists for the pair."""
        return cls._registry.get((source_type, target_type))

    @classmethod
    def registered_pairs(cls) -> List[Tuple[Type, Type]]:
        """List all registered (source, target) pairs."""
        return list(cls._registry.keys())

    # -- conversion ---------------------------------------------------------

    def convert(
        self, source: BaseMaterialData
    ) -> Tuple[BaseMaterialData, MaterialConversionReport]:
        """Convert *source* into a new instance of ``self.target_type``.

        Returns ``(target_data, report)``.
        """
        report = MaterialConversionReport(
            source_type=type(source).__name__,
            target_type=self.target_type.__name__,
        )

        target = self.target_type(mesh_name=source.mesh_name)

        # Build reverse mapping for unmapped-target detection
        all_dst_attrs: Set[str] = {dst for dst, _ in self._mapping.values()}

        for mat_name, src_attrs in source.materials.items():
            target_attrs: Dict[str, Dict[str, Any]] = {}
            mapped_this: Dict[str, str] = {}
            unmapped_src: List[str] = []

            for src_attr, src_entry in src_attrs.items():
                if src_attr not in self._mapping:
                    unmapped_src.append(src_attr)
                    continue

                dst_attr, transform_fn = self._mapping[src_attr]
                entry = copy.deepcopy(src_entry)

                # Apply value transform only to constants
                if entry.get("type") in ("scalar", "vector"):
                    try:
                        entry["value"] = transform_fn(entry["value"])
                    except Exception as exc:
                        report.add_warning(
                            f"[{mat_name}] Transform failed for "
                            f"'{src_attr}' → '{dst_attr}': {exc}"
                        )
                elif entry.get("type") == "texture" and transform_fn is not _identity:
                    report.add_warning(
                        f"[{mat_name}] Value transform for "
                        f"'{src_attr}' → '{dst_attr}' skipped because the "
                        f"property is a texture (path copied as-is)."
                    )

                target_attrs[dst_attr] = entry
                mapped_this[src_attr] = dst_attr

            target.materials[mat_name] = target_attrs

            # Record report data for this material
            if mapped_this:
                report.mapped[mat_name] = mapped_this
            if unmapped_src:
                report.unmapped_source[mat_name] = unmapped_src

            # Detect target attrs that received no value
            filled_dst = set(target_attrs.keys())
            missing_dst = sorted(all_dst_attrs - filled_dst)
            if missing_dst:
                report.unmapped_target[mat_name] = missing_dst

        return target, report


# ---------------------------------------------------------------------------
# FilamentMaterialData  (stub)
# ---------------------------------------------------------------------------

class FilamentMaterialData(BaseMaterialData):
    """Material data targeting the Google Filament PBR renderer.

    Filament's ``Material`` model uses these core properties (lower-camelCase
    to match Filament naming conventions):

    - baseColor        (sRGB colour or texture)
    - metallic         (0.0–1.0 or texture)
    - roughness        (0.0–1.0 or texture)
    - reflectance      (0.0–1.0, replaces "specular" in some pipelines)
    - normal           (tangent-space normal map)
    - emissive         (HDR colour or texture)
    - ambientOcclusion (0.0–1.0 or texture)
    - clearCoat        (0.0–1.0)
    - clearCoatRoughness (0.0–1.0)

    This is a **stub** — ``from_mesh`` is not implemented because Filament
    does not have a scene graph to query.  Instances are created via
    ``MaterialConverter.convert()`` or ``from_json()`` / ``from_file()``.
    """

    # Canonical → Filament name mapping (used by converters targeting this type)
    CANONICAL_TO_FILAMENT = {
        "BaseColor":        "baseColor",
        "Metallic":         "metallic",
        "Specular":         "reflectance",
        "Roughness":        "roughness",
        "Normal":           "normal",
        "EmissiveColor":    "emissive",
        "Opacity":          "opacity",
        "AmbientOcclusion": "ambientOcclusion",
        "Coat":             "clearCoat",
        "CoatRoughness":    "clearCoatRoughness",
    }

    @classmethod
    def from_mesh(cls, mesh_obj: Any) -> "FilamentMaterialData":
        raise NotImplementedError(
            "FilamentMaterialData cannot extract from a mesh — "
            "create instances via MaterialConverter.convert() or from_json()."
        )


# ---------------------------------------------------------------------------
# Default converter registrations
# ---------------------------------------------------------------------------

def _register_defaults() -> None:
    """Register built-in converter mappings.

    Called at module import time so that converters are available immediately.
    Add new registrations here as more DCC types are created.
    """

    # BaseMaterialData → FilamentMaterialData
    # (works for any source that uses canonical attribute names)
    _canonical_to_filament = {
        src: dst for src, dst in FilamentMaterialData.CANONICAL_TO_FILAMENT.items()
    }

    MaterialConverter.register(
        BaseMaterialData,
        FilamentMaterialData,
        _canonical_to_filament,
    )


_register_defaults()
