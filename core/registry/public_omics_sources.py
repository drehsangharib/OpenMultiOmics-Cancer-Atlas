#!/usr/bin/env python3

"""
Public Omics Source.Public Omics Source Registry

Output:
    outputs/dataset_inventory/public_omics_sources.tsv

Example:
    python -m core.registry.public_omics_sources
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import List, Optional

import pandas as pd


DEFAULT_OUTPUT = Path("outputs/dataset_inventory/public_omics_sources.tsv")


SOURCE_COLUMNS = [
    "source_id",
    "source_name",
    "source_type",
    "primary_domain",
    "omics_scope",
    "cancer_relevance",
    "access_type",
    "api_available",
    "bulk_download_available",
    "controlled_access_possible",
    "recommended_first_integration",
    "priority_for_atlas",
    "integration_stage",
    "base_url",
    "api_or_docs_url",
    "notes",
]


@dataclass(frozen=True)
class PublicOmicsSource:
    """
    Curated public omics source metadata.
    """

    source_id: str
    source_name: str
    source_type: str
    primary_domain: str
    omics_scope: str
    cancer_relevance: str
    access_type: str
    api_available: bool
    bulk_download_available: bool
    controlled_access_possible: bool
    recommended_first_integration: bool
    priority_for_atlas: int
    integration_stage: str
    base_url: str
    api_or_docs_url: str
    notes: str

    def to_record(self) -> dict:
        """
        Convert source metadata to a dictionary record.
        """
        return asdict(self)


def make_source(
    source_id: str,
    source_name: str,
    source_type: str,
    primary_domain: str,
    omics_scope: str,
    cancer_relevance: str,
    access_type: str,
    api_available: bool,
    bulk_download_available: bool,
    controlled_access_possible: bool,
    recommended_first_integration: bool,
    priority_for_atlas: int,
    integration_stage: str,
    base_url: str,
    api_or_docs_url: str,
    notes: str,
) -> PublicOmicsSource:
    """
    Helper for constructing source records.
    """
    return PublicOmicsSource(
        source_id=source_id,
        source_name=source_name,
        source_type=source_type,
        primary_domain=primary_domain,
        omics_scope=omics_scope,
        cancer_relevance=cancer_relevance,
        access_type=access_type,
        api_available=api_available,
        bulk_download_available=bulk_download_available,
        controlled_access_possible=controlled_access_possible,
        recommended_first_integration=recommended_first_integration,
        priority_for_atlas=priority_for_atlas,
        integration_stage=integration_stage,
        base_url=base_url,
        api_or_docs_url=api_or_docs_url,
        notes=notes,
    )


def get_public_omics_sources() -> List[PublicOmicsSource]:
    """
    Return curated public omics sources for atlas expansion.

    priority_for_atlas:
        5 = immediate high-value integration target
        4 = strong integration target
        3 = useful secondary integration target
        2 = useful later
        1 = background/reference resource
    """
    return [
        make_source(
            source_id="gdc",
            source_name="NCI Genomic Data Commons",
            source_type="data_portal",
            primary_domain="cancer genomics",
            omics_scope="genomics; transcriptomics; epigenomics; clinical; biospecimen; imaging metadata",
            cancer_relevance="primary cancer data commons and current foundation of the project",
            access_type="open metadata; open and controlled files",
            api_available=True,
            bulk_download_available=True,
            controlled_access_possible=True,
            recommended_first_integration=True,
            priority_for_atlas=5,
            integration_stage="implemented",
            base_url="https://portal.gdc.cancer.gov/",
            api_or_docs_url="https://docs.gdc.cancer.gov/API/Users_Guide/Getting_Started/",
            notes="Already implemented as the first metadata, ranking, visualization, report, and subset-export source.",
        ),
        make_source(
            source_id="xena",
            source_name="UCSC Xena",
            source_type="data_hub",
            primary_domain="public cancer multi-omics matrices",
            omics_scope="transcriptomics; copy number; methylation; mutation; phenotype; survival; pan-cancer matrices",
            cancer_relevance="precompiled public matrices across TCGA, GDC, ICGC, TARGET, GTEx, CCLE, Pan-Cancer Atlas, PCAWG and other hubs",
            access_type="open public datasets; optional private hubs",
            api_available=True,
            bulk_download_available=True,
            controlled_access_possible=False,
            recommended_first_integration=True,
            priority_for_atlas=5,
            integration_stage="next",
            base_url="https://xena.ucsc.edu/",
            api_or_docs_url="https://xenabrowser.net/datapages/",
            notes="Best next source because it provides ready-to-use public matrices for downstream atlas modules.",
        ),
        make_source(
            source_id="cbioportal",
            source_name="cBioPortal",
            source_type="data_portal_api",
            primary_domain="cancer genomics and clinical studies",
            omics_scope="mutations; copy number; expression; clinical; sample metadata; study metadata",
            cancer_relevance="large public cancer genomics study catalog with REST API and clinical/genomic study structure",
            access_type="open public studies; some private instances possible",
            api_available=True,
            bulk_download_available=True,
            controlled_access_possible=True,
            recommended_first_integration=True,
            priority_for_atlas=5,
            integration_stage="planned",
            base_url="https://www.cbioportal.org/",
            api_or_docs_url="https://docs.cbioportal.org/web-api-and-clients/",
            notes="Strong source for study-level cancer genomics inventory and cross-validation of GDC/TCGA-derived studies.",
        ),
        make_source(
            source_id="pdc",
            source_name="NCI Proteomic Data Commons",
            source_type="data_portal_api",
            primary_domain="cancer proteomics",
            omics_scope="proteomics; phosphoproteomics; clinical; study metadata; file metadata",
            cancer_relevance="harmonized cancer proteomic data with links to genomic and imaging resources",
            access_type="open metadata; open and controlled data possible",
            api_available=True,
            bulk_download_available=True,
            controlled_access_possible=True,
            recommended_first_integration=True,
            priority_for_atlas=5,
            integration_stage="planned",
            base_url="https://pdc.cancer.gov/",
            api_or_docs_url="https://pdc.cancer.gov/",
            notes="Key source for proteogenomics-ready cancer atlas modules.",
        ),
        make_source(
            source_id="cptac",
            source_name="Clinical Proteomic Tumor Analysis Consortium",
            source_type="consortium",
            primary_domain="cancer proteogenomics",
            omics_scope="proteomics; phosphoproteomics; genomics; transcriptomics; clinical",
            cancer_relevance="major cancer proteogenomics consortium with data exposed through GDC, PDC, ISB-CGC, and related resources",
            access_type="open processed data; controlled raw data possible",
            api_available=True,
            bulk_download_available=True,
            controlled_access_possible=True,
            recommended_first_integration=False,
            priority_for_atlas=4,
            integration_stage="planned",
            base_url="https://proteomics.cancer.gov/programs/cptac",
            api_or_docs_url="https://pdc.cancer.gov/",
            notes="Useful as a program layer; PDC should be the first technical access point.",
        ),
        make_source(
            source_id="pride",
            source_name="PRIDE Archive",
            source_type="repository_api",
            primary_domain="public proteomics",
            omics_scope="mass spectrometry proteomics; peptide identifications; protein identifications; project metadata; file metadata",
            cancer_relevance="broad public proteomics repository useful for cancer proteomics discovery outside curated CPTAC/PDC cohorts",
            access_type="open public datasets",
            api_available=True,
            bulk_download_available=True,
            controlled_access_possible=False,
            recommended_first_integration=False,
            priority_for_atlas=4,
            integration_stage="planned",
            base_url="https://www.ebi.ac.uk/pride/",
            api_or_docs_url="https://pride-archive.github.io/PrideAPIDocs/",
            notes="Useful for broad proteomics dataset discovery and cross-repository proteomics coverage.",
        ),
        make_source(
            source_id="icgc_argo",
            source_name="ICGC ARGO",
            source_type="data_platform_api",
            primary_domain="international cancer genomics",
            omics_scope="whole genome; transcriptomics; clinical; molecular file metadata",
            cancer_relevance="international cancer genomics platform with programmatic APIs and controlled-access molecular data considerations",
            access_type="open metadata; controlled molecular data",
            api_available=True,
            bulk_download_available=True,
            controlled_access_possible=True,
            recommended_first_integration=False,
            priority_for_atlas=4,
            integration_stage="planned",
            base_url="https://platform.icgc-argo.org/",
            api_or_docs_url="https://docs.icgc-argo.org/",
            notes="Useful after open-source metadata layers are stable; controlled access should remain metadata-only unless credentials are explicitly handled later.",
        ),
        make_source(
            source_id="geo",
            source_name="NCBI Gene Expression Omnibus",
            source_type="repository",
            primary_domain="public functional genomics",
            omics_scope="transcriptomics; epigenomics; single-cell; array; sequencing metadata",
            cancer_relevance="large public repository with many cancer transcriptomic and epigenomic studies",
            access_type="open public datasets",
            api_available=True,
            bulk_download_available=True,
            controlled_access_possible=False,
            recommended_first_integration=False,
            priority_for_atlas=4,
            integration_stage="planned_later",
            base_url="https://www.ncbi.nlm.nih.gov/geo/",
            api_or_docs_url="https://www.ncbi.nlm.nih.gov/geo/info/geo_paccess.html",
            notes="High-value broad discovery source, but metadata harmonization is harder than GDC/Xena/cBioPortal.",
        ),
        make_source(
            source_id="sra",
            source_name="NCBI Sequence Read Archive",
            source_type="repository",
            primary_domain="raw sequencing archives",
            omics_scope="raw sequencing reads; transcriptomics; genomics; epigenomics; metagenomics",
            cancer_relevance="broad raw sequencing archive that can expand cancer discovery beyond curated cancer portals",
            access_type="open public datasets; controlled dbGaP-linked studies possible",
            api_available=True,
            bulk_download_available=True,
            controlled_access_possible=True,
            recommended_first_integration=False,
            priority_for_atlas=3,
            integration_stage="planned_later",
            base_url="https://www.ncbi.nlm.nih.gov/sra",
            api_or_docs_url="https://www.ncbi.nlm.nih.gov/sra/docs/",
            notes="Useful later for raw-data discovery; requires careful query design and metadata harmonization.",
        ),
        make_source(
            source_id="metabolights",
            source_name="MetaboLights",
            source_type="repository_api",
            primary_domain="metabolomics",
            omics_scope="metabolomics; study metadata; assay metadata; sample metadata",
            cancer_relevance="potential source for public cancer metabolomics datasets",
            access_type="open public datasets",
            api_available=True,
            bulk_download_available=True,
            controlled_access_possible=False,
            recommended_first_integration=False,
            priority_for_atlas=3,
            integration_stage="planned_later",
            base_url="https://www.ebi.ac.uk/metabolights/",
            api_or_docs_url="https://www.ebi.ac.uk/metabolights/ws/api/spec.html",
            notes="Useful for expanding beyond genomics/proteomics into metabolomics after core source inventory is stable.",
        ),
        make_source(
            source_id="depmap",
            source_name="DepMap",
            source_type="data_portal",
            primary_domain="cancer cell line functional genomics",
            omics_scope="cell line genomics; transcriptomics; CRISPR dependency; drug sensitivity; molecular profiles",
            cancer_relevance="important for linking tumor atlas signals to cancer cell line dependency and perturbation data",
            access_type="open public processed data",
            api_available=True,
            bulk_download_available=True,
            controlled_access_possible=False,
            recommended_first_integration=False,
            priority_for_atlas=3,
            integration_stage="planned_later",
            base_url="https://depmap.org/portal/",
            api_or_docs_url="https://depmap.org/portal/download/",
            notes="Useful for downstream mechanistic interpretation and model-system linkage.",
        ),
        make_source(
            source_id="human_protein_atlas",
            source_name="Human Protein Atlas",
            source_type="knowledgebase",
            primary_domain="protein expression and pathology",
            omics_scope="protein expression; immunohistochemistry; pathology images; tissue specificity; cancer summaries",
            cancer_relevance="useful for protein/pathology context and marker interpretation",
            access_type="open public knowledgebase",
            api_available=True,
            bulk_download_available=True,
            controlled_access_possible=False,
            recommended_first_integration=False,
            priority_for_atlas=2,
            integration_stage="planned_later",
            base_url="https://www.proteinatlas.org/",
            api_or_docs_url="https://www.proteinatlas.org/about/download",
            notes="Useful as interpretability/annotation layer rather than primary cohort inventory.",
        ),
        make_source(
            source_id="cellosaurus",
            source_name="Cellosaurus",
            source_type="knowledgebase",
            primary_domain="cell line metadata",
            omics_scope="cell line identity; disease metadata; tissue metadata; cross-references",
            cancer_relevance="useful for harmonizing cancer cell line identifiers across DepMap, CCLE, PRIDE, and literature data",
            access_type="open public knowledgebase",
            api_available=True,
            bulk_download_available=True,
            controlled_access_possible=False,
            recommended_first_integration=False,
            priority_for_atlas=2,
            integration_stage="planned_later",
            base_url="https://www.cellosaurus.org/",
            api_or_docs_url="https://www.cellosaurus.org/downloads",
            notes="Useful as a reference harmonization layer for cell-line-centric modules.",
        ),
    ]


def build_source_inventory_dataframe(
    sources: Optional[List[PublicOmicsSource]] = None,
) -> pd.DataFrame:
    """
    Build source registry DataFrame.
    """
    if sources is None:
        sources = get_public_omics_sources()

    records = [source.to_record() for source in sources]
    df = pd.DataFrame(records)

    for column in SOURCE_COLUMNS:
        if column not in df.columns:
            df[column] = ""

    df = df.loc[:, SOURCE_COLUMNS].copy()
    df = df.sort_values(
        by=["priority_for_atlas", "recommended_first_integration", "source_id"],
        ascending=[False, False, True],
        kind="stable",
    ).reset_index(drop=True)

    return df


def filter_source_inventory(
    df: pd.DataFrame,
    source_id: Optional[str] = None,
    source_type: Optional[str] = None,
    omics_scope: Optional[str] = None,
    api_only: bool = False,
    recommended_only: bool = False,
    min_priority: Optional[int] = None,
) -> pd.DataFrame:
    """
    Filter source registry DataFrame.
    """
    out = df.copy()

    if source_id:
        query = source_id.strip().lower()
        out = out[
            out["source_id"]
            .astype(str)
            .str.lower()
            .str.contains(query, regex=False)
        ]

    if source_type:
        query = source_type.strip().lower()
        out = out[
            out["source_type"]
            .astype(str)
            .str.lower()
            .str.contains(query, regex=False)
        ]

    if omics_scope:
        query = omics_scope.strip().lower()
        out = out[
            out["omics_scope"]
            .astype(str)
            .str.lower()
            .str.contains(query, regex=False)
        ]

    if api_only:
        out = out[out["api_available"].astype(bool)]

    if recommended_only:
        out = out[out["recommended_first_integration"].astype(bool)]

    if min_priority is not None:
        out = out[out["priority_for_atlas"].astype(int) >= min_priority]

    return out.reset_index(drop=True)


def write_public_omics_sources_inventory(
    output_path: Path = DEFAULT_OUTPUT,
    source_id: Optional[str] = None,
    source_type: Optional[str] = None,
    omics_scope: Optional[str] = None,
    api_only: bool = False,
    recommended_only: bool = False,
    min_priority: Optional[int] = None,
) -> pd.DataFrame:
    """
    Write public omics source registry to TSV.
    """
    df = build_source_inventory_dataframe()
    df = filter_source_inventory(
        df=df,
        source_id=source_id,
        source_type=source_type,
        omics_scope=omics_scope,
        api_only=api_only,
        recommended_only=recommended_only,
        min_priority=min_priority,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, sep="\t", index=False)

    return df


def build_arg_parser() -> argparse.ArgumentParser:
    """
    Build CLI parser.
    """
    parser = argparse.ArgumentParser(
        description="Write curated public omics source registry."
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output source registry TSV. Default: {DEFAULT_OUTPUT}",
    )

    parser.add_argument(
        "--source-id",
        default=None,
        help="Optional source ID text filter.",
    )

    parser.add_argument(
        "--source-type",
        default=None,
        help="Optional source type text filter.",
    )

    parser.add_argument(
        "--omics-scope",
        default=None,
        help="Optional omics scope text filter.",
    )

    parser.add_argument(
        "--api-only",
        action="store_true",
        help="Keep only sources with programmatic API availability.",
    )

    parser.add_argument(
        "--recommended-only",
        action="store_true",
        help="Keep only sources recommended for first integration wave.",
    )

    parser.add_argument(
        "--min-priority",
        type=int,
        default=None,
        help="Keep only sources with priority_for_atlas >= this value.",
    )

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """
    CLI entrypoint.
    """
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        df = write_public_omics_sources_inventory(
            output_path=args.output,
            source_id=args.source_id,
            source_type=args.source_type,
            omics_scope=args.omics_scope,
            api_only=args.api_only,
            recommended_only=args.recommended_only,
            min_priority=args.min_priority,
        )
    except Exception as exc:
        print(
            f"ERROR: Failed to write public omics source registry: {exc}",
            file=sys.stderr,
        )
        return 1

    print("Public omics source registry complete.")
    print(f"Rows: {len(df)}")
    print(f"Output: {args.output}")

    if not df.empty:
        print("Top sources:")
        for _, row in df.head(10).iterrows():
            print(
                f"  {row['source_id']} | "
                f"priority={row['priority_for_atlas']} | "
                f"stage={row['integration_stage']} | "
                f"name={row['source_name']}"
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
