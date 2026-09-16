#!/usr/bin/env Rscript
# Lightweight raw-CEL smoke path for Affymetrix Human Gene 2.1 ST (GPL17692).
# This is deliberately separate from the GSE7451 GPL570/MAS5 path.
args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 1) stop("Usage: run_affy_st_smoke.R <config.json>")
config <- jsonlite::fromJSON(args[[1]], simplifyVector = TRUE)
required <- c("jsonlite", "oligo", "limma", "Biobase")
missing <- required[!vapply(required, requireNamespace, logical(1), quietly = TRUE)]
if (length(missing) > 0) stop(paste("Missing R packages:", paste(missing, collapse = ", ")))

set.seed(as.integer(config$parameters$random_seed))
output_dir <- config$outputs$output_dir
result_dir <- file.path(output_dir, "results")
table_dir <- file.path(output_dir, "tables")
figure_dir <- file.path(output_dir, "figures")
dir.create(result_dir, recursive = TRUE, showWarnings = FALSE)
dir.create(table_dir, recursive = TRUE, showWarnings = FALSE)
dir.create(figure_dir, recursive = TRUE, showWarnings = FALSE)

sample_sheet <- read.csv(config$input_paths$sample_sheet, stringsAsFactors = FALSE, check.names = FALSE)
sample_sheet$group <- factor(sample_sheet$group, levels = c("control", "case"))
if (any(is.na(sample_sheet$group))) stop("Unresolved sample groups detected")
cel_files <- unlist(config$parameters$cel_files)
if (length(cel_files) != nrow(sample_sheet) || !all(file.exists(cel_files))) stop("CEL/sample sheet mismatch")

raw <- oligo::read.celfiles(cel_files, verbose = FALSE)
normalized <- oligo::rma(raw, target = "core")
normalized_matrix <- Biobase::exprs(normalized)
colnames(normalized_matrix) <- sample_sheet$sample_id
write.csv(normalized_matrix, file.path(result_dir, "normalized_expression_matrix.csv"), quote = FALSE)

# GPL17692 is an Affymetrix Gene ST array. MAS5 calls are not silently claimed.
# Gene ST arrays use oligo's DABG/PSDABG present/absent compatibility methods;
# DABG p-values are aggregated from probes to the same core transcript clusters
# used by RMA. The method and the non-MAS5 boundary are carried into every record.
aggregate_dabg_to_core <- function(feature_set) {
  pvalues <- Biobase::exprs(oligo::paCalls(feature_set, "DABG", verbose = FALSE))
  pvalues <- as.matrix(pvalues)
  info <- oligo::getProbeInfo(feature_set, field = c("fid", "fsetid"), target = "core")
  fid_col <- if ("fid" %in% colnames(info)) "fid" else stop("DABG probe info has no fid column")
  fset_col <- if ("fsetid" %in% colnames(info)) "fsetid" else if ("man_fsetid" %in% colnames(info)) "man_fsetid" else stop("DABG probe info has no fsetid column")
  probe_ids <- as.character(rownames(pvalues))
  fset_ids <- as.character(info[[fset_col]])[match(probe_ids, as.character(info[[fid_col]]))]
  valid <- !is.na(fset_ids) & nzchar(fset_ids)
  if (!any(valid)) stop("DABG probe IDs did not map to core transcript clusters")
  pvalues <- pvalues[valid, , drop = FALSE]
  fset_ids <- fset_ids[valid]
  target_ids <- unique(fset_ids)
  aggregated <- matrix(NA_real_, nrow = length(target_ids), ncol = ncol(pvalues),
                        dimnames = list(target_ids, colnames(pvalues)))
  for (j in seq_len(ncol(pvalues))) {
    aggregated[, j] <- stats::tapply(pvalues[, j], fset_ids, stats::median, na.rm = TRUE)[target_ids]
  }
  aggregated
}

detection <- tryCatch(aggregate_dabg_to_core(raw), error = function(e) NULL)
absent_filter_status <- "N/A_oligo_DABG_unavailable"
absent_filter_method <- "not_run"
if (!is.null(detection) && all(rownames(normalized_matrix) %in% rownames(detection))) {
  detection <- detection[rownames(normalized_matrix), , drop = FALSE]
  present_fraction <- rowMeans(detection < 0.05, na.rm = TRUE)
  absent_fraction <- 1 - present_fraction
  keep <- absent_fraction <= as.numeric(config$parameters$absent_probe_threshold)
  absent_filter_status <- "success_compatibility_DABG"
  absent_filter_method <- "oligo::paCalls(DABG) aggregated to core; p<0.05; not MAS5"
} else {
  # PSDABG is a documented oligo fallback at probeset level. Use it only when
  # the platform design cannot expose a core-level DABG mapping.
  detection_ps <- tryCatch(Biobase::exprs(oligo::paCalls(raw, "PSDABG", verbose = FALSE)), error = function(e) NULL)
  if (!is.null(detection_ps)) {
    detection_ps <- as.matrix(detection_ps)
    if (!is.null(rownames(detection_ps)) && all(rownames(normalized_matrix) %in% rownames(detection_ps))) {
      detection_ps <- detection_ps[rownames(normalized_matrix), , drop = FALSE]
      present_fraction <- rowMeans(detection_ps < 0.05, na.rm = TRUE)
      absent_fraction <- 1 - present_fraction
      keep <- absent_fraction <= as.numeric(config$parameters$absent_probe_threshold)
      absent_filter_status <- "success_compatibility_PSDABG"
      absent_filter_method <- "oligo::paCalls(PSDABG); p<0.05; not MAS5"
    }
  }
}
if (!grepl("^success", absent_filter_status)) {
  keep <- rep(TRUE, nrow(normalized_matrix))
  present_fraction <- rep(NA_real_, nrow(normalized_matrix))
  absent_fraction <- rep(NA_real_, nrow(normalized_matrix))
}
probe_qc <- data.frame(
  probe_id = rownames(normalized_matrix),
  present_fraction = present_fraction,
  absent_fraction = absent_fraction,
  filter_status = absent_filter_status,
  filter_method = absent_filter_method
)
write.csv(probe_qc, file.path(table_dir, "probe_detection_summary.csv"), row.names = FALSE, quote = FALSE)
filtered_matrix <- normalized_matrix[keep, , drop = FALSE]
write.csv(filtered_matrix, file.path(result_dir, "filtered_expression_matrix.csv"), quote = FALSE)

design <- stats::model.matrix(~ 0 + sample_sheet$group)
colnames(design) <- c("control", "case")
contrast <- limma::makeContrasts(case - control, levels = design)
fit <- limma::lmFit(filtered_matrix, design)
fit <- limma::contrasts.fit(fit, contrast)
fit <- limma::eBayes(fit)
de <- limma::topTable(fit, number = Inf, adjust.method = "BH", sort.by = "P")
de$probe_id <- rownames(de)
annotation_status <- "not_available"
annotation <- NULL
if (requireNamespace("hugene21sttranscriptcluster.db", quietly = TRUE) && requireNamespace("AnnotationDbi", quietly = TRUE)) {
  annotation <- tryCatch(AnnotationDbi::select(
    hugene21sttranscriptcluster.db::hugene21sttranscriptcluster.db,
    keys = rownames(filtered_matrix), columns = c("SYMBOL", "ENTREZID"), keytype = "PROBEID"
  ), error = function(e) NULL)
  if (!is.null(annotation)) {
    annotation <- annotation[!duplicated(annotation$PROBEID), , drop = FALSE]
    colnames(annotation)[colnames(annotation) == "PROBEID"] <- "probe_id"
    de <- merge(de, annotation, by = "probe_id", all.x = TRUE, sort = FALSE)
    annotation_status <- "hugene21sttranscriptcluster.db"
  }
}
write.csv(de, file.path(table_dir, "differential_expression.csv"), row.names = FALSE, quote = FALSE)
significant <- de[!is.na(de$adj.P.Val) & de$adj.P.Val <= 0.05 & abs(de$logFC) >= 1, , drop = FALSE]
pathway <- data.frame()
pathway_status <- "N/A_no_compatible_annotation"
pathway_method_executed <- "not_run"
enrichment_input <- significant
pathway_input_policy <- "BH<=0.05 and |logFC|>=1"
if (nrow(enrichment_input) == 0 && nrow(de) > 0) {
  # A small smoke dataset can have no BH-significant rows despite a valid
  # limma fit. Still execute the enrichment implementation on the 100 most
  # highly ranked rows, and label this technical fallback explicitly.
  enrichment_input <- utils::head(de, 100)
  pathway_input_policy <- "top 100 limma-ranked rows fallback; no BH-significant rows"
}
if (!is.null(annotation) && nrow(enrichment_input) > 0 && "ENTREZID" %in% colnames(enrichment_input) && requireNamespace("org.Hs.eg.db", quietly = TRUE)) {
  entrez <- unique(stats::na.omit(as.character(enrichment_input$ENTREZID)))
  universe <- unique(stats::na.omit(as.character(annotation$ENTREZID)))
  if (length(entrez) > 0 && length(universe) > 0) {
    pathway <- tryCatch(limma::goana(de = entrez, universe = universe, species = "Hs"), error = function(e) NULL)
    if (!is.null(pathway)) {
      pathway$GO_ID <- rownames(pathway)
      rownames(pathway) <- NULL
      pathway_status <- if (nrow(significant) > 0) "success_compatibility" else "success_compatibility_top_ranked_fallback"
      pathway_method_executed <- "limma::goana"
    }
  }
}
write.csv(pathway, file.path(table_dir, "pathway_enrichment.csv"), row.names = FALSE, quote = FALSE)

export_figure <- function(stem, plot_fun) {
  grDevices::pdf(file.path(figure_dir, paste0(stem, ".pdf")), width = 7, height = 5, useDingbats = FALSE); plot_fun(); grDevices::dev.off()
  grDevices::svg(file.path(figure_dir, paste0(stem, ".svg")), width = 7, height = 5); plot_fun(); grDevices::dev.off()
  grDevices::png(file.path(figure_dir, paste0(stem, ".png")), width = 2100, height = 1500, res = 300); plot_fun(); grDevices::dev.off()
  grDevices::tiff(file.path(figure_dir, paste0(stem, ".tiff")), width = 2100, height = 1500, res = 300, compression = "lzw"); plot_fun(); grDevices::dev.off()
  grDevices::jpeg(file.path(figure_dir, paste0(stem, ".jpg")), width = 2100, height = 1500, res = 300, quality = 95); plot_fun(); grDevices::dev.off()
}
plot_qc <- function() {
  boxplot(normalized_matrix, las = 2, col = c("#4C78A8", "#F58518"), main = "GSE77459 normalized expression", ylab = "RMA expression (log2 scale)", cex.axis = 0.65)
}
export_figure("Figure_1_QC", plot_qc)
summary <- list(
  dataset_id = config$meta$dataset_id,
  module_id = config$meta$module_id,
  run_id = config$meta$run_id,
  input_mode = "full_raw",
  platform = "GPL17692",
  organism = "Homo sapiens",
  random_seed = config$parameters$random_seed,
  n_samples = nrow(sample_sheet),
  groups = as.list(table(sample_sheet$group)),
  normalized_probe_count = nrow(normalized_matrix),
  filtered_probe_count = nrow(filtered_matrix),
  significant_gene_count = nrow(significant),
  absent_probe_threshold = config$parameters$absent_probe_threshold,
  absent_filter_status = absent_filter_status,
  absent_filter_method = absent_filter_method,
  multiple_testing = "BH",
  rma_status = "success_oligo_rma",
  limma_status = "success",
  annotation_status = annotation_status,
  pathway_status = pathway_status,
  pathway_method_requested = "MAPPFinder",
  pathway_method_executed = pathway_method_executed,
  pathway_input_policy = pathway_input_policy,
  pathway_reason = "GSE77459 smoke path uses explicitly labelled platform-compatible steps; it is not a GSE7451/pSS result",
  figure_formats = c("pdf", "svg", "png", "tiff", "jpg"),
  r_version = R.version.string,
  status = "success"
)
report_pdf <- file.path(result_dir, "GSE77459_smoke_report.pdf")
grDevices::pdf(report_pdf, width = 8.5, height = 11, useDingbats = FALSE)
par(mar = c(0, 0, 0, 0))
plot.new()
text(0.05, 0.94, "GSE77459 raw-CEL technical smoke report", adj = c(0, 0.5), cex = 1.35, font = 2)
report_lines <- c(
  paste("Run:", config$meta$run_id),
  "Dataset: GSE77459 | Platform: GPL17692 Affymetrix Human Gene 2.1 ST",
  "Design: Homo sapiens, control=6, case=6",
  "Input: full_raw; RMA: oligo::rma",
  paste("Absent filter:", absent_filter_status, "|", absent_filter_method),
  paste("Limma/BH:", "success", "| significant rows:", nrow(significant)),
  paste("Pathway requested: MAPPFinder | executed:", pathway_method_executed),
  paste("Pathway input policy:", pathway_input_policy),
  "Boundary: technical validation only; not a pSS or GSE7451 scientific result."
)
text(0.05, seq(0.85, 0.45, length.out = length(report_lines)), report_lines, adj = c(0, 0.5), cex = 0.9)
text(0.05, 0.12, "Generated by shengxinceshi-arena; compatible methods are explicitly labelled.", adj = c(0, 0.5), cex = 0.75, col = "#555555")
grDevices::dev.off()
summary$report_pdf <- basename(report_pdf)
summary$pdf_status <- "success"
jsonlite::write_json(summary, config$outputs$summary_json, auto_unbox = TRUE, pretty = TRUE)
