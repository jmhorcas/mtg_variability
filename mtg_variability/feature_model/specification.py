from dataclasses import dataclass, field
from typing import Literal


@dataclass
class VariantSpec:
    name: str
    children: list["VariationPointSpec"] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


@dataclass
class VariationPointSpec:
    name: str
    variants: list[VariantSpec] = field(default_factory=list)
    cardinality: Literal["optional", "or", "alternative"] | None = None
    mandatory: bool = False
    metadata: dict = field(default_factory=dict)


@dataclass
class SubFeatureModelSpec:
    root: VariationPointSpec
    constraints: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)