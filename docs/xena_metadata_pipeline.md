# UCSC Xena Metadata Pipeline

## Purpose

`core/pipelines/run_xena_metadata_pipeline.py` runs the UCSC Xena metadata-only dataset inventory workflow with one command.

This module is part of Milestone 1E.8: integrating Xena dataset inventory report generation into the Xena metadata pipeline.

## Scope

The pipeline queries selected UCSC Xena hubs and writes dataset-level metadata.

The pipeline does **not** download:

```text
expression matrices
copy-number matrices
methylation matrices
mutation matrices
clinical matrices
large molecular files