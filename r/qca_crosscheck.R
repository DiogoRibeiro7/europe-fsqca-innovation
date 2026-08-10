#!/usr/bin/env Rscript

# Canonical publication fsQCA using the CRAN QCA package.
#
# Thresholds, conditions, the outcome and directional expectations are read
# from the same YAML analysis configuration the Python pipeline uses, so the
# two implementations cannot drift apart silently. Output is written as
# structured term-level CSV rather than as captured console text, which is what
# makes automated Python-R parity possible.

suppressWarnings(suppressMessages({
  ok_qca <- requireNamespace("QCA", quietly = TRUE)
  ok_yaml <- requireNamespace("yaml", quietly = TRUE)
}))
if (!ok_qca) stop("Install the CRAN QCA package before running this cross-check.")
if (!ok_yaml) stop("Install the CRAN yaml package before running this cross-check.")

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 3) {
  stop("Usage: qca_crosscheck.R <calibrated.csv> <analysis_config.yml> <output_dir> [outcome]")
}

input_path <- args[[1]]
config_path <- args[[2]]
output_dir <- args[[3]]

config <- yaml::yaml.load_file(config_path)
conditions <- names(config$conditions)
outcome <- if (length(args) >= 4) args[[4]] else names(config$outcome)[[1]]

threshold <- function(key, fallback) {
  value <- config$truth_table[[key]]
  if (is.null(value)) fallback else value
}
incl_cut <- threshold("consistency_cutoff", 0.80)
pri_cut <- threshold("pri_cutoff", 0.50)
n_cut <- threshold("frequency_cutoff", 10)

# Directional expectations drive the intermediate solution. "present" expects
# the condition to contribute when present, "absent" when absent, and "either"
# leaves the counterfactual unconstrained.
direction_code <- function(name) {
  value <- config$conditions[[name]]$direction
  if (is.null(value) || value == "either") "-" else if (value == "present") "1" else "0"
}

dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)

data <- read.csv(input_path, check.names = FALSE)
missing <- setdiff(c(conditions, outcome), colnames(data))
if (length(missing) > 0) {
  # A restricted sample legitimately drops conditions; analyse what is present.
  message("Conditions absent from the calibrated table: ", paste(missing, collapse = ", "))
  conditions <- setdiff(conditions, missing)
  if (!(outcome %in% colnames(data))) {
    stop(paste("Missing outcome column:", outcome))
  }
}

qca_data <- data[, c(conditions, outcome)]
qca_data <- qca_data[complete.cases(qca_data), ]

tt <- QCA::truthTable(
  qca_data,
  outcome = outcome,
  conditions = conditions,
  incl.cut = incl_cut,
  pri.cut = pri_cut,
  n.cut = n_cut,
  complete = TRUE,
  show.cases = TRUE
)

dir_exp <- vapply(conditions, direction_code, character(1))
has_expectations <- any(dir_exp != "-")

# use.tilde keeps negation explicit so the exported terms parse unambiguously.
conservative <- QCA::minimize(tt, include = "", details = TRUE, show.cases = TRUE, use.tilde = TRUE)
parsimonious <- QCA::minimize(tt, include = "?", details = TRUE, show.cases = TRUE, use.tilde = TRUE)
intermediate <- NULL
if (has_expectations) {
  intermediate <- tryCatch(
    QCA::minimize(
      tt,
      include = "?",
      dir.exp = paste(dir_exp, collapse = ","),
      details = TRUE,
      show.cases = TRUE,
      use.tilde = TRUE
    ),
    error = function(e) {
      message("Intermediate solution unavailable: ", conditionMessage(e))
      NULL
    }
  )
}

# Term-level metrics as a canonical table.
#
# QCA can return several equally minimal solution models. Exporting only the
# first would present one arbitrary model as the result, so every model is
# exported with a model index. With a single model the metrics live in
# IC$incl.cov; with several they live in IC$individual[[i]]$incl.cov.
model_metrics <- function(solution, index) {
  if (!is.null(solution$IC$individual)) {
    return(solution$IC$individual[[index]]$incl.cov)
  }
  solution$IC$incl.cov
}

model_totals <- function(solution, index) {
  if (!is.null(solution$IC$individual)) {
    return(solution$IC$individual[[index]]$sol.incl.cov)
  }
  solution$IC$sol.incl.cov
}

term_rows <- function(solution, kind) {
  if (is.null(solution)) return(NULL)
  out <- list()
  for (index in seq_along(solution$solution)) {
    expressions <- as.character(solution$solution[[index]])
    metrics <- model_metrics(solution, index)
    if (is.null(metrics)) {
      out[[length(out) + 1]] <- data.frame(
        solution = kind,
        model = index,
        term = seq_along(expressions),
        configuration = expressions,
        consistency = NA_real_,
        pri = NA_real_,
        raw_coverage = NA_real_,
        unique_coverage = NA_real_,
        stringsAsFactors = FALSE
      )
      next
    }
    metrics <- as.data.frame(metrics)
    metrics <- metrics[rownames(metrics) %in% expressions, , drop = FALSE]
    out[[length(out) + 1]] <- data.frame(
      solution = kind,
      model = index,
      term = seq_len(nrow(metrics)),
      configuration = rownames(metrics),
      consistency = as.numeric(metrics[["inclS"]]),
      pri = as.numeric(metrics[["PRI"]]),
      raw_coverage = as.numeric(metrics[["covS"]]),
      unique_coverage = as.numeric(metrics[["covU"]]),
      stringsAsFactors = FALSE
    )
  }
  do.call(rbind, out)
}

solution_rows <- function(solution, kind) {
  if (is.null(solution)) return(NULL)
  essential <- if (is.null(solution$IC$essential)) character(0) else as.character(solution$IC$essential)
  out <- list()
  for (index in seq_along(solution$solution)) {
    expression <- paste(as.character(solution$solution[[index]]), collapse = " + ")
    totals <- model_totals(solution, index)
    out[[length(out) + 1]] <- data.frame(
      solution = kind,
      model = index,
      n_models = length(solution$solution),
      expression = expression,
      n_terms = length(solution$solution[[index]]),
      consistency = if (is.null(totals)) NA_real_ else as.numeric(totals[["inclS"]]),
      pri = if (is.null(totals)) NA_real_ else as.numeric(totals[["PRI"]]),
      coverage = if (is.null(totals)) NA_real_ else as.numeric(totals[["covS"]]),
      essential_terms = paste(essential, collapse = " + "),
      stringsAsFactors = FALSE
    )
  }
  do.call(rbind, out)
}

terms <- do.call(rbind, list(
  term_rows(conservative, "conservative"),
  term_rows(parsimonious, "parsimonious"),
  term_rows(intermediate, "intermediate")
))
solutions <- do.call(rbind, list(
  solution_rows(conservative, "conservative"),
  solution_rows(parsimonious, "parsimonious"),
  solution_rows(intermediate, "intermediate")
))

for (kind in unique(solutions$solution)) {
  count <- max(solutions$n_models[solutions$solution == kind])
  if (count > 1) {
    message("Model ambiguity: ", kind, " solution has ", count, " equally minimal models")
  }
}

write.csv(terms, file.path(output_dir, "solution_terms.csv"), row.names = FALSE)
write.csv(solutions, file.path(output_dir, "solutions.csv"), row.names = FALSE)
write.csv(as.data.frame(tt$tt), file.path(output_dir, "truth_table.csv"), row.names = FALSE)

necessity <- QCA::superSubset(
  qca_data,
  outcome = outcome,
  conditions = conditions,
  relation = "necessity",
  incl.cut = 0.9,
  cov.cut = 0.5
)
necessity_frame <- tryCatch(
  {
    incl_cov <- as.data.frame(necessity$incl.cov)
    data.frame(
      expression = rownames(incl_cov),
      consistency = as.numeric(incl_cov[["inclN"]]),
      coverage = as.numeric(incl_cov[["covN"]]),
      stringsAsFactors = FALSE
    )
  },
  error = function(e) data.frame(expression = character(0), consistency = numeric(0), coverage = numeric(0))
)
write.csv(necessity_frame, file.path(output_dir, "necessity.csv"), row.names = FALSE)

specification <- data.frame(
  key = c("outcome", "conditions", "incl_cut", "pri_cut", "n_cut", "dir_exp", "n_cases", "config"),
  value = c(
    outcome,
    paste(conditions, collapse = ","),
    format(incl_cut),
    format(pri_cut),
    format(n_cut),
    paste(dir_exp, collapse = ","),
    format(nrow(qca_data)),
    config_path
  ),
  stringsAsFactors = FALSE
)
write.csv(specification, file.path(output_dir, "specification.csv"), row.names = FALSE)

# Human-readable transcripts remain useful for manual review, but they are not
# the machine-readable interface.
capture.output(tt, file = file.path(output_dir, "truth_table.txt"))
capture.output(conservative, file = file.path(output_dir, "conservative.txt"))
capture.output(parsimonious, file = file.path(output_dir, "parsimonious.txt"))
if (!is.null(intermediate)) {
  capture.output(intermediate, file = file.path(output_dir, "intermediate.txt"))
}

message("QCA cross-check complete: ", output_dir)
