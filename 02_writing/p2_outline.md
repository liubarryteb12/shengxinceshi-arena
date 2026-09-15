> Output level: L1
> P1 status: partial
> Evidence boundary: candidate / exploratory
> Target journal: pending
> Note: 本地 matrix_only 验证；raw CEL 的 RMA/MAS5 尚待 GitHub Actions full_raw

# Exploratory salivary gene expression analysis in primary Sjögren's syndrome

## One-sentence positioning

This project evaluates whether a reproducible Affymetrix expression workflow can transform GSE7451 salivary expression data into traceable candidate evidence for primary Sjögren's syndrome research.

## Logical chain P0–P4

- **P0 Background problem**: salivary molecular profiles may differ between primary Sjögren's syndrome and healthy controls.
- **P1 Main finding**: the current validation package contains a balanced 10-control/10-pSS design [L-E001].
- **P2 Supporting evidence**: an expression matrix and limma/BH comparison were produced; the run reports 0 multiple-testing-significant probes under its current input mode [L-E002].
- **P3 Limitation**: this local run is series_matrix; it does not replace the raw-CEL RMA/MAS5 run.
- **P4 Outlook**: execute the same configuration in GitHub Actions, then review pathway-tool compatibility and independent validation needs.

## Abstract (structured draft)

### Background
Primary Sjögren's syndrome is an autoimmune disease for which minimally invasive molecular signals remain of interest. This work uses a reproducible workflow to test an exploratory salivary expression analysis.

### Methods
The GSE7451 series contains 20 samples, including 10 controls and 10 pSS samples [L-E001]. The target pipeline is RMA preprocessing, removal of probe sets absent in more than 75% of samples, limma differential expression with Benjamini–Hochberg correction, and pathway enrichment. The present local run used series_matrix; the raw-CEL path is scheduled on GitHub Actions.

### Results
The current run produced an expression matrix with 54675 retained rows and a differential-expression table. 0 rows met the configured adjusted-P and effect-size thresholds in this run [L-E002]. Figure 1 is a QC visualization, not a clinical-performance plot.

### Conclusions
The repository now records a traceable P1-to-P2 evidence path. The findings are exploratory and candidate-level; independent validation and the raw-CEL execution remain necessary.

## Introduction

Primary Sjögren's syndrome affects exocrine tissues and can be studied with molecular measurements from saliva. The present workflow is designed to separate data processing, evidence extraction, writing, and journal strategy. It therefore treats the GSE7451 result as a candidate signal rather than a validated diagnostic marker.

## Materials and methods

### Dataset and sample groups

GSE7451 is an expression-profiling-by-array series on whole saliva. The downloaded package contains Affymetrix GPL570 raw files and a GEO series matrix. The tracked sample sheet records 20 samples, with balanced control and pSS groups [L-E001].

### Reproducible analysis workflow

The confirmed workflow is: input integrity and sample check → RMA → MAS5 present/absent filtering at the pre-registered 75% threshold → limma comparison of pSS versus control with BH correction → pathway enrichment. Every step is configured through files rather than hard-coded user paths. In the local validation run, the series matrix was used only to validate downstream contracts; the full raw-CEL workflow is assigned to GitHub Actions.

### Evidence and claim boundary

All numerical statements in this draft are anchored to the P1 run and its evidence interface. The terms “candidate”, “exploratory”, “associated”, and “requires independent validation” are intentional. This workflow does not support claims of diagnosis, clinical utility, causality, mechanism confirmation, or external validation.

## Results

### Input and workflow integrity

The input package was downloaded from NCBI GEO, recorded with checksums, and parsed into a sample sheet. The group balance was control=10 and pSS=10 [L-E001].

### Differen
