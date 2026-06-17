# Multi-Atlas Architecture

## Purpose

This document describes the current architecture of OpenMultiOmics-Cancer-Atlas as of the multi-atlas metadata framework stage.

The framework is currently focused on metadata-only public cancer omics atlas construction using GDC and UCSC Xena as the main public repositories.

## Architecture layers

The project currently has four main layers:

```text
Layer A  Public source discovery
Layer B  Unified public metadata platform
Layer C  Atlas-specific slice and QC
Layer D  Generalized multi-atlas framework
core.atlas.build_keyword_public_omics_atlas
core.atlas.report_keyword_public_omics_atlas_qc
core.atlas.build_keyword_public_omics_atlas_from_config
core.atlas.run_keyword_public_omics_atlas_batch