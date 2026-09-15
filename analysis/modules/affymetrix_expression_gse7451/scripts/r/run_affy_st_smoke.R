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

# GPL17692 is an Affymetrix Gene ST array. MAS5 calls are not silently claimed;
# oligo::detectionP is the explicitly labelled platform-compatible detection step.
detection <- tryCatch(oligo::detectionP(raw), error = function(e) NULL)
absent_filter_status <- "N/A_oligo_detectionP_unavailable"
absent_filter_method <- "not_run"
if (!is.null(detection)) {
  detection <- as.matrix(detection)
  if (!is.null(rownames(detection)) && all(rownames(normalized_matrix) %in% rownames(detection))) {
    detection <- detection[rownames(normalized_matrix), , drop = FALSE]
    present_fraction <- rowMeans(detection < 0.05, na.rm = TRUE)
    absent_fraction <- 1 - present_fraction
    keep <- absent_fraction <= as.numeric(config$parameters$absent_probe_threshold)
    absent_filter_status <- "success_compatibility_detectionP"
    absent_filter_method <- "oligo::detectionP(p<0.05); not MAS5"
  }
}
if (absent_filter_status != "success_compatibility_detectionP") {
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
pathway_status <- "N/A_no_compatible_annotation_or_significant_genes"
pathway_method_executed <- "not_run"
if (!is.null(annotation) && nrow(significant) > 0 && "ENTREZID" %in% colnames(significant) && requireNamespace("org.Hs.eg.db", quietly = TRUE)) {
  entrez <- unique(stats::na.omit(as.character(significant$ENTREZID)))
  universe <- unique(stats::na.omit(as.character(annotation$ENTREZID)))
  if (length(entrez) > 0 && length(universe) > 0) {
    pathway <- tryCatch(limma::goana(de = entrez, universe = universe, species = "Hs"), error = function(e) NULL)
    if (!is.null(pathway)) {
      pathway$GO_ID <- rownames(pathway)
      rownames(pathway) <- NULL
      pathway_status <- "success_compatibility"
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
  pathway_reason = "GSE77459 smoke path uses explicitly labelled platform-compatible steps; it is not a GSE7451/pSS result",
  figure_formats = c("pdf", "svg", "png", "tiff", "jpg"),
  r_version = R.version.string,
  status = "success"
)
jsonlite::write_json(summary, config$outputs$summary_json, auto_unbox = TRUE, pretty = TRUE)
