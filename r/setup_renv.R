#!/usr/bin/env Rscript

args <- commandArgs(trailingOnly = TRUE)
install_mode <- "--install" %in% args
required_packages <- c("renv", "QCA")

package_status <- data.frame(
  package = required_packages,
  installed = vapply(required_packages, requireNamespace, logical(1), quietly = TRUE),
  stringsAsFactors = FALSE
)

print(package_status, row.names = FALSE)

missing_packages <- package_status$package[!package_status$installed]
if (!install_mode) {
  if (length(missing_packages) > 0) {
    message("Missing R packages: ", paste(missing_packages, collapse = ", "))
    message("Run: Rscript r/setup_renv.R --install")
  } else {
    message("R validation packages are available.")
  }
  quit(status = 0)
}

options(repos = c(CRAN = "https://cloud.r-project.org"), renv.consent = TRUE)

if (!requireNamespace("renv", quietly = TRUE)) {
  install.packages("renv")
}

if (!file.exists("renv.lock")) {
  renv::init(bare = TRUE, restart = FALSE)
}

for (package in setdiff(required_packages, "renv")) {
  if (!requireNamespace(package, quietly = TRUE)) {
    renv::install(package)
  }
}

renv::status()
