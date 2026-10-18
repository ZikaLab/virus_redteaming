"""HSE rows and Category 1 rows keep their own columns in one table."""

from virus_redteaming.hse_cat1_merge.merge import HseCat1Merger
from virus_redteaming.hse_cat1_merge.models import Cat1VirusRow, HseVirusRow, VmrTaxon
from virus_redteaming.hse_cat1_merge.vmr import VmrTaxonIndex
from virus_redteaming.nen_accession.parse import GenBankAccessionParser


def _hse(**overrides: str) -> HseVirusRow:
    values = {
        "family": "Reoviridae",
        "genus": "Rotavirus",
        "nen_genus": "Rotavirus",
        "viruses": "Human rotaviruses A, B and C",
        "nen_virus": "rotavirus A",
        "ncbi_accession": "NC_011503",
        "hazard_group": "2",
        "schedule_5": "0",
        "issues": "",
    }
    values.update(overrides)
    return HseVirusRow(**values)


def _cat1(**overrides: str) -> Cat1VirusRow:
    values = {
        "species": "Rotavirus rotahominis",
        "exemplar": "rotavirus H",
        "family": "Sedoreoviridae",
        "genus": "Rotavirus",
        "kingdom": "Orthornavirae",
        "genbank": "L: GU983676; S: GU983677",
        "refseq": "NC_000000",
        "hazard_group": "1",
        "schedule_5": "0",
        "issues": "",
    }
    values.update(overrides)
    return Cat1VirusRow(**values)


def _taxon(
    name: str,
    exemplar: bool,
    family: str,
    species: str,
    genbank: str,
) -> VmrTaxon:
    return VmrTaxon(name, exemplar, family, species, "Orthornavirae", genbank)


def _merge(
    hse: tuple[HseVirusRow, ...],
    cat1: tuple[Cat1VirusRow, ...],
    taxa: tuple[VmrTaxon, ...],
):
    merger = HseCat1Merger(VmrTaxonIndex(taxa), GenBankAccessionParser())
    return merger.merge(hse, cat1)


def test_hse_row_keeps_catalogue_fields_and_fills_ictv_from_the_exemplar() -> None:
    taxa = (
        _taxon("rotavirus A", False, "Sedoreoviridae", "Other", "EXTRA"),
        _taxon(
            "rotavirus A",
            True,
            "Sedoreoviridae",
            "Rotavirus alphagastroenteritidis",
            "NC_011503",
        ),
    )
    rows = _merge((_hse(),), (), taxa)
    row = rows[0]
    assert row.source == "HSE"
    assert row.catalogue_family == "Reoviridae"
    assert row.catalogue_genus == "Rotavirus"
    assert row.catalogue_virus == "Human rotaviruses A, B and C"
    assert row.ictv_family == "Sedoreoviridae"
    assert row.ictv_genus == "Rotavirus"
    assert row.ictv_virus == "rotavirus A"
    assert row.species == "Rotavirus alphagastroenteritidis"
    assert row.genbank_accessions == "NC_011503"
    assert row.ncbi_accession == "NC_011503"
    assert row.refseq_accessions == ""
    assert row.hazard_group == "2"


def test_catalogue_genus_is_not_replaced_by_the_ictv_genus() -> None:
    taxa = (
        _taxon(
            "human hepatitis C virus",
            True,
            "Flaviviridae",
            "Orthohepacivirus hominis",
            "AF009606",
        ),
    )
    rows = _merge(
        (
            _hse(
                family="Flaviviridae",
                genus="Hepacivirus",
                nen_genus="Orthohepacivirus",
                viruses="Hepatitis C virus",
                nen_virus="human hepatitis C virus",
                ncbi_accession="AF009606",
                hazard_group="3",
            ),
        ),
        (),
        taxa,
    )
    assert rows[0].catalogue_genus == "Hepacivirus"
    assert rows[0].ictv_genus == "Orthohepacivirus"


def test_cat1_row_leaves_catalogue_columns_blank_and_parses_accessions() -> None:
    rows = _merge((), (_cat1(),), ())
    row = rows[0]
    assert row.source == "Cat1"
    assert row.catalogue_family == ""
    assert row.catalogue_genus == ""
    assert row.catalogue_virus == ""
    assert row.ictv_family == "Sedoreoviridae"
    assert row.ictv_genus == "Rotavirus"
    assert row.ictv_virus == "rotavirus H"
    assert row.genbank_accessions == "L: GU983676; S: GU983677"
    assert row.ncbi_accession == "GU983676; GU983677"
    assert row.refseq_accessions == "NC_000000"
    assert row.hazard_group == "1"


def test_hse_rows_precede_cat1_rows() -> None:
    rows = _merge((_hse(), _hse(nen_virus="rotavirus B")), (_cat1(),), ())
    assert [row.source for row in rows] == ["HSE", "HSE", "Cat1"]
    assert rows[1].ictv_virus == "rotavirus B"
    assert rows[1].ictv_family == ""
    assert rows[1].genbank_accessions == ""


def test_blank_nen_virus_is_not_looked_up() -> None:
    taxa = (VmrTaxon("", True, "X", "Y", "Z", "U87411"),)
    rows = _merge(
        (_hse(nen_virus="", ncbi_accession="", issues="genus not in ICTV"),),
        (),
        taxa,
    )
    assert rows[0].ictv_virus == ""
    assert rows[0].ictv_family == ""
    assert rows[0].species == ""
    assert rows[0].genbank_accessions == ""
    assert rows[0].issues == "genus not in ICTV"


def test_unmatched_nen_virus_keeps_its_genus_and_blank_taxonomy() -> None:
    rows = _merge(
        (
            _hse(
                nen_genus="Bocaparvovirus",
                viruses="Human bocavirus 1 and 3",
                nen_virus="human bocavirus 3",
                ncbi_accession="",
                hazard_group="2",
            ),
        ),
        (),
        (),
    )
    assert rows[0].ictv_genus == "Bocaparvovirus"
    assert rows[0].ictv_virus == "human bocavirus 3"
    assert rows[0].ictv_family == ""
    assert rows[0].genbank_accessions == ""
