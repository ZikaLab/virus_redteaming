"""Harmonize when asked, otherwise sample an existing nen file."""

from __future__ import annotations

from pathlib import Path

from virus_redteaming.category1.except_sample import (
    GenusCategory1Sampler,
    GenusVirusExcept,
)
from virus_redteaming.category1.harmonize import NenHarmonizer
from virus_redteaming.category1.inventory import CatalogueGenusIndex, IctvGenusInventory
from virus_redteaming.category1.write import IctvCat1Writer, NenReader, NenWriter
from virus_redteaming.core.errors import VirusRedteamingError


class Category1PromptRequired(VirusRedteamingError):  # noqa: N818
    """Sampling needs nen_viruses.csv, or a harmonizer when that file is missing."""

    def __init__(self, nen_path: Path) -> None:
        self.nen_path = nen_path
        super().__init__(f"prompts required to write {nen_path}")


class BuildCategory1:
    def __init__(
        self,
        catalogue_index: CatalogueGenusIndex,
        harmonizer: NenHarmonizer | None,
        exceptor: GenusVirusExcept,
        sampler: GenusCategory1Sampler,
        nen_writer: NenWriter,
        nen_reader: NenReader,
        cat1_writer: IctvCat1Writer,
    ) -> None:
        self._catalogue_index = catalogue_index
        self._harmonizer = harmonizer
        self._exceptor = exceptor
        self._sampler = sampler
        self._nen_writer = nen_writer
        self._nen_reader = nen_reader
        self._cat1_writer = cat1_writer

    def run(
        self,
        viruses_path: Path,
        ictv_path: Path,
        nen_path: Path,
        cat1_path: Path,
        refresh: bool = False,
    ) -> None:
        inventory = IctvGenusInventory.from_csv(ictv_path)
        if refresh or not nen_path.exists():
            if self._harmonizer is None:
                raise Category1PromptRequired(nen_path)
            catalogue_rows = self._catalogue_index.read(viruses_path)
            nen_rows = self._harmonizer.harmonize(catalogue_rows, inventory)
            self._nen_writer.write(nen_path, nen_rows)
        else:
            nen_rows = self._nen_reader.read(nen_path)
        remainder = self._exceptor.remainder(inventory, nen_rows)
        sample = self._sampler.sample(nen_rows, remainder)
        self._cat1_writer.write(cat1_path, sample)
