"""Assignment against the repository VMR, writing only a temporary nen file."""

import csv
from pathlib import Path

from virus_redteaming.nen_accession.index import ExemplarIndexFactory
from virus_redteaming.nen_accession.io import (
    NenAccessionWriter,
    NenCsvReader,
    VmrCsvReader,
)
from virus_redteaming.nen_accession.parse import GenBankAccessionParser
from virus_redteaming.nen_accession.workflow import AssignNenAccessions

_REPO = Path(__file__).resolve().parents[2]
_VMR = _REPO / "docs" / "VMR_MSL41.v1.20260729.csv"

_HEADER = (
    "Family,Genus,NEN genus,Viruses,NEN virus,"
    "Human pathogen hazard group,Schedule 5,Issues\n"
)


def _workflow() -> AssignNenAccessions:
    return AssignNenAccessions(
        vmr_reader=VmrCsvReader(),
        nen_reader=NenCsvReader(),
        writer=NenAccessionWriter(),
        parser=GenBankAccessionParser(),
        index_factory=ExemplarIndexFactory(),
    )


def test_repository_vmr_fills_known_names_and_reports_the_rest(tmp_path: Path) -> None:
    nen = tmp_path / "nen.csv"
    nen.write_text(
        _HEADER
        + "F,Orthoflavivirus,Orthoflavivirus,Dengue virus,dengue virus type 2,3,1,\n"
        + "F,Orthoflavivirus,Orthoflavivirus,Dengue virus,dengue virus type 1,3,1,\n"
        + "F,Orthoflavivirus,Orthoflavivirus,Dengue virus,dengue virus type 3,3,1,\n"
        + "F,Orthoflavivirus,Orthoflavivirus,Dengue virus,dengue virus type 4,3,1,\n"
        + "Reoviridae,Seadornavirus,Seadornavirus,Banna virus,Banna virus,2,0,\n"
        + "Picornaviridae,Enterovirus,Enterovirus,Poliovirus 2,poliovirus 2,3,1,\n"
        + "F,Orthoflavivirus,Orthoflavivirus,Zika virus,Zika virus,3,1,\n"
        + "P,Bocaparvovirus,Bocaparvovirus,Human bocavirus 1,human bocavirus 1,2,0,\n"
        + "P,Bocaparvovirus,Bocaparvovirus,Human bocavirus 3,human bocavirus 3,2,0,\n"
        + "Adenoviridae,,,Adenoviridae spp.,,2,0,genus not in ICTV\n"
        + "Togaviridae,Alphavirus,Alphavirus,Sindbis virus,Sindbis virus,3,0,\n",
        encoding="utf-8",
    )
    report = _workflow().run(nen, _VMR)
    with nen.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    by_name = {row["NEN virus"]: row for row in rows}
    assert by_name["dengue virus type 2"]["NCBI accession"] == "U87411"
    assert by_name["dengue virus type 1"]["NCBI accession"] == "U88536"
    assert by_name["dengue virus type 3"]["NCBI accession"] == "M93130"
    assert by_name["dengue virus type 4"]["NCBI accession"] == "AF326573"
    assert by_name["dengue virus type 2"]["Human pathogen hazard group"] == "3"
    assert by_name["dengue virus type 2"]["Schedule 5"] == "1"
    banna = by_name["Banna virus"]["NCBI accession"]
    assert banna.startswith("AF133430")
    assert "AF168005" not in banna
    assert by_name["poliovirus 2"]["NCBI accession"] == "M12197"
    assert by_name["Zika virus"]["NCBI accession"] == "AY632535"
    assert by_name["human bocavirus 1"]["NCBI accession"] == "JQ923422"
    assert by_name["human bocavirus 3"]["NCBI accession"] == ""
    assert by_name[""]["NCBI accession"] == ""
    assert by_name[""]["Issues"] == "genus not in ICTV"
    sindbis = by_name["Sindbis virus"]["NCBI accession"]
    assert sindbis == "J02363"
    assert "Ockelbo" not in sindbis
    assert report.matched == 9
    assert report.blank_nen_virus == 1
    assert report.unmatched_names == ("human bocavirus 3",)
    assert len(rows) == 11
