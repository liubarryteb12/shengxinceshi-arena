#!/usr/bin/env Rscript
# Memory-safe validation path. It does not claim to perform RMA or MAS5.
args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 1) stop("Usage: run_matrix_pipeline.R <config.json>")
config <- jsonlite::fromJSON(args[[1]], simplifyVector = TRUE)
required_packages <- c("jsonlite", "limma")
missing <- required_packages[!vapply(required_packages, requireNamespace, logical(1), quietly = TRUE)]
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
sample_sheet$group <- factor(sample_sheet$group, levels = c("control", "pSS"))
if (any(is.na(sample_sheet$group))) stop("Unresolved sample groups detected")
expression <- read.csv(config$input_paths$expression_matrix, check.names = FALSE, row.names = 1)
expression <- as.matrix(expression)
mode(expression) <- "numeric"
if (ncol(expression) != nrow(sample_sheet)) stop("Expression matrix column count does not match sample sheet")
colnames(expression) <- sample_sheet$sample_id
normalized_matrix <- expression
write.csv(normalized_matrix, file.path(result_dir, "normalized_expression_matrix.csv"), quote = FALSE)

# The GEO series matrix is already processed. Do not relabel it as a new RMA run.
filtered_matrix <- normalized_matrix
write.csv(filtered_matrix, file.path(result_dir, "filtered_expression_matrix.csv"), quote = FALSE)
probe_qc <- data.frame(
  probe_id = rownames(normalized_matrix),
  present_fraction = NA_real_,
  absent_fraction = NA_real_,
  filter_status = "N/A_series_matrix_already_processed"
)
write.csv(probe_qc, file.path(table_dir, "probe_detection_summary.csv"), row.names = FALSE, quote = FALSE)

design <- stats::model.matrix(~ 0 + sample_sheet$group)
colnames(design) <- c("control", "pSS")
contrast <- limma::makeContrasts(pSS - control, levels = design)
fit <- limma::lmFit(filtered_matrix, design)
fit <- limma::contrasts.fit(fit, contrast)
fit <- limma::eBayes(fit)
de <- limma::topTable(fit, number = Inf, adjust.method = "BH", sort.by = "P")
de$probe_id <- rownames(de)
write.csv(de, file.path(table_dir, "differential_expression.csv"), row.names = FALSE, quote = FALSE)
significant <- de[!is.na(de$adj.P.Val) & de$adj.P.Val <= 0.05 & abs(de$logFC) >= 1, , drop = FALSE]
pathway <- data.frame()
write.csv(pathway, file.path(table_dir, "pathway_enrichment.csv"), row.names = FALSE, quote = FALSE)

export_figure <- function(stem, plot_fun) {
  grDevices::pdf(file.path(figure_dir, paste0(stem, ".pdf")), width = 7, height = 5, useDingbats = FALSE); plot_fun(); grDevices::dev.off()
  grDevices::svg(file.path(figure_dir, paste0(stem, ".svg")), width = 7, height = 5); plot_fun(); grDevices::dev.off()
  grDevices::png(file.path(figure_dir, paste0(stem, ".png")), width = 2100, height = 1500, res = 300); plot_fun(); grDevices::dev.off()
  grDevices::tiff(file.path(figure_dir, paste0(stem, ".tiff")), width = 2100, height = 1500, res = 300, compression = "lzw"); plot_fun(); grDevices::dev.off()
  grDevices::jpeg(file.path(figure_dir, paste0(stem, ".jpg")), width = 2100, height = 1500, res = 300, quality = 95); plot_fun(); grDevices::dev.off()
}
plot_qc <- function() {
  boxplot(normalized_matrix, las = 2, col = c("#4C78A8", "#F58518"), main = "GSE7451 series matrix", ylab = "series-matrix expression scale", cex.axis = 0.65)
}
export_figure("Figure_1_QC", plot_qc)
summary <- list(
  dataset_id = config$meta$dataset_id,
  module_id = config$meta$module_id,
  run_id = config$meta$run_id,
  input_mode = "series_matrix",
  random_seed = config$parameters$random_seed,
  n_samples = nrow(sample_sheet),
  groups = as.list(table(sample_sheet$group)),
  normalized_probe_count = nrow(normalized_matrix),
  filtered_probe_count = nrow(filtered_matrix),
  significant_gene_count = nrow(significant),
  absent_probe_threshold = config$parameters$absent_probe_threshold,
  multiple_testing = "BH",
  rma_status = "N/A_series_matrix_already_processed",
  absent_filter_status = "N/A_raw_MAS5_not_run_in_memory_safe_mode",
  annotation_status = "not_available",
  limma_status = "success",
  pathway_status = "N/A_no_annotation_in_matrix_validation_mode",
  pathway_method_requested = "MAPPFinder",
  pathway_method_executed = "not_run",
  pathway_reason = "Matrix-only validation intentionally stops before raw-CEL RMA/MAS5 and annotation-dependent enrichment",
  figure_formats = c("pdf", "svg", "png", "tiff", "jpg"),
  r_version = R.version.string,
  status = "success"
)
jsonlite::write_json(summary, config$outputs$summary_json, auto_unbox = TRUE, pretty = TRUE)
