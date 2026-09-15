#!/usr/bin/env Rscript
# GSE7451 P1 execution script.
# The script reads all paths and parameters from a JSON config.

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 1) stop("Usage: run_pipeline.R <config.json>")
config_path <- args[[1]]
config <- jsonlite::fromJSON(config_path, simplifyVector = TRUE)

required_packages <- c("jsonlite", "affy", "limma", "Biobase")
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
if (!all(c("sample_id", "group") %in% colnames(sample_sheet))) stop("Sample sheet must contain sample_id and group")
sample_sheet$group <- factor(sample_sheet$group, levels = c("control", "pSS"))
if (any(is.na(sample_sheet$group))) stop("Unresolved sample groups detected")
if (nrow(sample_sheet) < 6) stop("Sample size is below the minimum safety threshold")

cel_files <- unlist(config$parameters$cel_files)
if (length(cel_files) != nrow(sample_sheet)) stop("CEL file count does not match sample sheet")
if (!all(file.exists(cel_files))) stop("At least one decompressed CEL file is missing")

raw <- affy::ReadAffy(filenames = cel_files)
normalized <- affy::rma(raw)
normalized_matrix <- Biobase::exprs(normalized)
colnames(normalized_matrix) <- sample_sheet$sample_id
write.csv(normalized_matrix, file.path(result_dir, "normalized_expression_matrix.csv"), quote = FALSE)

# MAS5 present/absent calls are used only for the pre-registered probe filter.
# Process one CEL at a time: the full AffyBatch plus a 20-sample MAS5 object
# exceeds the memory ceiling of the local validation sandbox. This remains the
# same MAS5 method, with lower peak memory.
rm(raw, normalized)
gc(verbose = FALSE)
call_matrix <- matrix(NA_character_, nrow = nrow(normalized_matrix), ncol = length(cel_files))
rownames(call_matrix) <- rownames(normalized_matrix)
colnames(call_matrix) <- sample_sheet$sample_id
for (i in seq_along(cel_files)) {
  one_raw <- affy::ReadAffy(filenames = cel_files[[i]])
  one_call <- affy::mas5calls(one_raw)
  one_values <- Biobase::exprs(one_call)[, 1]
  call_matrix[, i] <- as.character(one_values[rownames(normalized_matrix)])
  rm(one_raw, one_call, one_values)
  gc(verbose = FALSE)
}
present_fraction <- rowMeans(call_matrix == "P", na.rm = TRUE)
absent_fraction <- 1 - present_fraction
probe_qc <- data.frame(
  probe_id = rownames(normalized_matrix),
  present_fraction = present_fraction[rownames(normalized_matrix)],
  absent_fraction = absent_fraction[rownames(normalized_matrix)]
)
write.csv(probe_qc, file.path(table_dir, "probe_detection_summary.csv"), row.names = FALSE, quote = FALSE)
keep <- absent_fraction[rownames(normalized_matrix)] <= as.numeric(config$parameters$absent_probe_threshold)
filtered_matrix <- normalized_matrix[keep, , drop = FALSE]
write.csv(filtered_matrix, file.path(result_dir, "filtered_expression_matrix.csv"), quote = FALSE)

# Differential expression: pSS minus control, moderated t statistics, BH correction.
design <- stats::model.matrix(~ 0 + sample_sheet$group)
colnames(design) <- c("control", "pSS")
contrast <- limma::makeContrasts(pSS - control, levels = design)
fit <- limma::lmFit(filtered_matrix, design)
fit <- limma::contrasts.fit(fit, contrast)
fit <- limma::eBayes(fit)
de <- limma::topTable(fit, number = Inf, adjust.method = "BH", sort.by = "P")
de$probe_id <- rownames(de)

# Optional annotation is explicit. Missing annotation does not change DE values.
annotation_status <- "not_available"
annotation <- NULL
if (requireNamespace("hgu133plus2.db", quietly = TRUE) && requireNamespace("AnnotationDbi", quietly = TRUE)) {
  annotation <- tryCatch({
    AnnotationDbi::select(hgu133plus2.db::hgu133plus2.db,
      keys = rownames(filtered_matrix),
      columns = c("SYMBOL", "ENTREZID"),
      keytype = "PROBEID"
    )
  }, error = function(e) NULL)
  if (!is.null(annotation)) {
    annotation <- annotation[!duplicated(annotation$PROBEID), , drop = FALSE]
    colnames(annotation)[colnames(annotation) == "PROBEID"] <- "probe_id"
    de <- merge(de, annotation, by = "probe_id", all.x = TRUE, sort = FALSE)
    annotation_status <- "hgu133plus2.db"
  }
}
write.csv(de, file.path(table_dir, "differential_expression.csv"), row.names = FALSE, quote = FALSE)

significant <- de[!is.na(de$adj.P.Val) & de$adj.P.Val <= 0.05 & abs(de$logFC) >= 1, , drop = FALSE]

# The prompt names MAPPFinder. We do not silently relabel a different tool as MAPPFinder.
pathway_status <- "blocked"
pathway_method_executed <- "not_run"
pathway_reason <- "No compatible pathway tool or no significant annotated genes"
pathway <- data.frame()
if (!is.null(annotation) && nrow(significant) > 0 && "ENTREZID" %in% colnames(significant) && requireNamespace("org.Hs.eg.db", quietly = TRUE)) {
  entrez <- unique(stats::na.omit(as.character(significant$ENTREZID)))
  universe <- unique(stats::na.omit(as.character(annotation$ENTREZID)))
  if (length(entrez) > 0 && length(universe) > 0) {
    pathway <- tryCatch(
      limma::goana(de = entrez, universe = universe, species = "Hs"),
      error = function(e) NULL
    )
    if (!is.null(pathway)) {
      pathway$GO_ID <- rownames(pathway)
      rownames(pathway) <- NULL
      pathway_status <- "success_compatibility"
      pathway_method_executed <- "limma::goana"
      pathway_reason <- "MAPPFinder was requested; limma::goana was executed as an explicitly labelled compatibility implementation"
    }
  }
}
write.csv(pathway, file.path(table_dir, "pathway_enrichment.csv"), row.names = FALSE, quote = FALSE)

# Export one QC figure in all five requested formats.
export_figure <- function(stem, plot_fun) {
  grDevices::pdf(file.path(figure_dir, paste0(stem, ".pdf")), width = 7, height = 5, useDingbats = FALSE)
  plot_fun(); grDevices::dev.off()
  grDevices::svg(file.path(figure_dir, paste0(stem, ".svg")), width = 7, height = 5)
  plot_fun(); grDevices::dev.off()
  grDevices::png(file.path(figure_dir, paste0(stem, ".png")), width = 2100, height = 1500, res = 300)
  plot_fun(); grDevices::dev.off()
  grDevices::tiff(file.path(figure_dir, paste0(stem, ".tiff")), width = 2100, height = 1500, res = 300, compression = "lzw")
  plot_fun(); grDevices::dev.off()
  grDevices::jpeg(file.path(figure_dir, paste0(stem, ".jpg")), width = 2100, height = 1500, res = 300, quality = 95)
  plot_fun(); grDevices::dev.off()
}
plot_qc <- function() {
  boxplot(normalized_matrix, las = 2, col = c("#4C78A8", "#F58518"),
    main = "GSE7451 normalized expression", ylab = "RMA expression (log2 scale)", cex.axis = 0.65)
}
export_figure("Figure_1_QC", plot_qc)

summary <- list(
  dataset_id = config$meta$dataset_id,
  module_id = config$meta$module_id,
  run_id = config$meta$run_id,
  input_mode = "full_raw",
  random_seed = config$parameters$random_seed,
  n_samples = nrow(sample_sheet),
  groups = as.list(table(sample_sheet$group)),
  normalized_probe_count = nrow(normalized_matrix),
  filtered_probe_count = nrow(filtered_matrix),
  significant_gene_count = nrow(significant),
  absent_probe_threshold = config$parameters$absent_probe_threshold,
  multiple_testing = "BH",
  rma_status = "success",
  absent_filter_status = "success",
  limma_status = "success",
  annotation_status = annotation_status,
  pathway_status = pathway_status,
  pathway_method_requested = "MAPPFinder",
  pathway_method_executed = pathway_method_executed,
  pathway_reason = pathway_reason,
  figure_formats = c("pdf", "svg", "png", "tiff", "jpg"),
  r_version = R.version.string,
  status = "success"
)
jsonlite::write_json(summary, config$outputs$summary_json, auto_unbox = TRUE, pretty = TRUE)
