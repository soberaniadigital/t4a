#!/usr/bin/env Rscript
# Install R dependencies into a project-local renv library.
# Usage: Rscript setup_r.R
#
# To do a clean reinstall: rm -rf renv/ .Rprofile && Rscript setup_r.R

packages <- c(
  # Analysis
  "lme4",         # Mixed-effects models
  "lmerTest",     # Satterthwaite p-values for lmer
  "emmeans",      # Estimated marginal means and contrasts
  "multcomp",     # Multiple comparisons
  "multcompView", # Compact letter displays
  "performance",  # Model diagnostics
  # Data
  "dplyr",        # Data manipulation
  "tidyr",        # Reshape (pivot_wider, unite)
  # Plots
  "ggplot2",      # Visualization
  # Dev
  "styler"        # Code formatter
)

if (!requireNamespace("renv", quietly = TRUE)) {
  install.packages("renv", repos = "https://cloud.r-project.org")
}

# Initialize renv if not yet set up (or after deleting renv/)
if (!file.exists("renv.lock")) {
  renv::init(bare = TRUE)
}

renv::install(packages)
renv::snapshot(prompt = FALSE)
