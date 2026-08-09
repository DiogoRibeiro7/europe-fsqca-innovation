#!/usr/bin/env Rscript

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 4) {
  stop("Usage: qca_crosscheck.R <calibrated.csv> <outcome> <condition_csv> <output_dir>")
}

input_path <- args[[1]]
outcome <- args[[2]]
conditions <- strsplit(args[[3]], ",", fixed = TRUE)[[1]]
output_dir <- args[[4]]

dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)

if (!requireNamespace("QCA", quietly = TRUE)) {
  stop("Install the CRAN QCA package before running this cross-check.")
}

data <- read.csv(input_path, check.names = FALSE)
required <- c(conditions, outcome)
missing <- setdiff(required, colnames(data))
if (length(missing) > 0) {
  stop(paste("Missing calibrated columns:", paste(missing, collapse = ", ")))
}

qca_data <- data[, required]
qca_data <- qca_data[complete.cases(qca_data), ]

# Publication thresholds must be synchronized manually with the YAML analysis config.
tt <- QCA::truthTable(
  qca_data,
  outcome = outcome,
  conditions = conditions,
  incl.cut = 0.80,
  pri.cut = 0.50,
  n.cut = 10,
  complete = TRUE,
  show.cases = TRUE
)

conservative <- QCA::minimize(tt, include = "", details = TRUE, show.cases = TRUE)
parsimonious <- QCA::minimize(tt, include = "?", details = TRUE, show.cases = TRUE)

capture.output(tt, file = file.path(output_dir, "truth_table.txt"))
capture.output(conservative, file = file.path(output_dir, "conservative.txt"))
capture.output(parsimonious, file = file.path(output_dir, "parsimonious.txt"))

# Intermediate solutions require directional expectations. Add them only after
# the theory section freezes expectations; do not infer expectations from results.
message("QCA cross-check complete: ", output_dir)
