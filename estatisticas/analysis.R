# =============================================================================
# Analysis of Pivot Translation Experiment
# =============================================================================
#
# Design: Nested within-subjects (repeated measures)
#   - Fixed factor A: treatment_type (3 levels: direct, single_pivot, dual_pivot)
#   - Fixed factor B(A): pivot_config, nested within treatment_type
#       - direct:       1 level  ("none")
#       - single_pivot: 7 levels (one per pivot language)
#       - dual_pivot:  21 levels (one per pair of pivot languages)
#   - Random factor: sentence nested within source (blocking)
#   - Every sentence is observed under all 29 conditions
#
# Research questions:
#   Q1: Do treatment types differ (direct vs single-pivot vs dual-pivot)?
#   Q2: Do pivot languages differ within the single-pivot treatment?
#   Q3: Do pivot-language pairs differ within the dual-pivot treatment?
#
# CSV file format (see end of script for details)
# =============================================================================


# =============================================================================
# 1. REQUIRED PACKAGES
# =============================================================================

# Install if needed (uncomment):
# install.packages(c("lme4", "lmerTest", "emmeans", "multcomp", "ggplot2",
#                     "dplyr", "tidyr", "performance"))

library(lme4)       # Mixed-effects models
library(lmerTest)    # Satterthwaite degrees of freedom & p-values for lmer
library(emmeans)     # Estimated marginal means and contrasts
library(multcomp)    # Compact letter displays
library(ggplot2)     # Plots
library(dplyr)       # Data manipulation
library(tidyr)       # pivot_wider / unite (used in bootstrap section)
library(performance) # Model diagnostics


# =============================================================================
# 2. LOAD AND PREPARE DATA
# =============================================================================

# Resolve paths relative to this script's location so output files
# always land in the project root regardless of the working directory.
# Works with Rscript, source(), and RStudio.
get_script_dir <- function() {
  # Rscript via commandArgs
  args <- commandArgs(trailingOnly = FALSE)
  file_arg <- grep("^--file=", args, value = TRUE)
  if (length(file_arg) > 0) return(dirname(normalizePath(sub("^--file=", "", file_arg[1]))))
  # source()
  if (!is.null(sys.frame(1)$ofile)) return(dirname(normalizePath(sys.frame(1)$ofile)))
  # fallback: working directory
  return(getwd())
}
script_dir <- get_script_dir()
project_root <- normalizePath(file.path(script_dir, ".."))
out <- function(filename) file.path(project_root, filename)

df <- read.csv(out("experiment_data.csv"), stringsAsFactors = FALSE)

# Ensure factors are properly encoded.
# sentence_id and source must be factors for the random effects.
# treatment_type and pivot_config must be factors for the fixed effects.
df$sentence_id    <- as.factor(df$sentence_id)
df$source         <- as.factor(df$source)
df$treatment_type <- as.factor(df$treatment_type)
df$pivot_config   <- as.factor(df$pivot_config)

# Set the reference level for treatment_type to "direct" so that
# model coefficients are interpreted relative to direct translation.
df$treatment_type <- relevel(df$treatment_type, ref = "direct")

# Basic sanity checks
cat("=== Data summary ===\n")
cat("Total rows:", nrow(df), "\n")
cat("Unique sentences:", nlevels(df$sentence_id), "\n")
cat("Unique sources:", nlevels(df$source), "\n")
cat("Conditions per sentence:", nrow(df) / nlevels(df$sentence_id), "\n\n")

cat("=== Observations per treatment type ===\n")
print(table(df$treatment_type))
cat("\n")

cat("=== Observations per pivot_config ===\n")
print(table(df$treatment_type, df$pivot_config))
cat("\n")

cat("=== Sentences per source ===\n")
print(table(df$source))
cat("\n")

# Verify the design is complete: every sentence should appear in all 29 conditions.
conditions_per_sentence <- df %>%
  group_by(sentence_id) %>%
  summarise(n_conditions = n_distinct(pivot_config))

if (any(conditions_per_sentence$n_conditions != 29)) {
  warning("DESIGN NOT COMPLETE: some sentences are missing conditions!")
  print(conditions_per_sentence %>% filter(n_conditions != 29))
} else {
  cat("Design check PASSED: all sentences appear in all 29 conditions.\n\n")
}


# =============================================================================
# 3. DESCRIPTIVE STATISTICS
# =============================================================================

cat("=== Descriptive statistics by treatment type ===\n")
desc_type <- df %>%
  group_by(treatment_type) %>%
  summarise(
    mean   = mean(score),
    sd     = sd(score),
    median = median(score),
    min    = min(score),
    max    = max(score),
    n      = n()
  )
print(desc_type)
cat("\n")

cat("=== Descriptive statistics by pivot_config (single-pivot) ===\n")
desc_single <- df %>%
  filter(treatment_type == "single_pivot") %>%
  group_by(pivot_config) %>%
  summarise(
    mean   = mean(score),
    sd     = sd(score),
    median = median(score),
    n      = n()
  ) %>%
  arrange(desc(mean))
print(desc_single)
cat("\n")

cat("=== Descriptive statistics by pivot_config (dual-pivot) ===\n")
desc_dual <- df %>%
  filter(treatment_type == "dual_pivot") %>%
  group_by(pivot_config) %>%
  summarise(
    mean   = mean(score),
    sd     = sd(score),
    median = median(score),
    n      = n()
  ) %>%
  arrange(desc(mean))
print(desc_dual)
cat("\n")


# =============================================================================
# 4. FIT THE LINEAR MIXED-EFFECTS MODEL
# =============================================================================

# Model specification:
#   - treatment_type: main fixed effect (3 levels)
#   - treatment_type:pivot_config: pivot configuration nested within treatment type
#   - (1 | source): random intercept for source (blocking factor — some software
#     programs are systematically harder to translate)
#   - (1 | source:sentence_id): random intercept for sentence nested within source
#     (accounts for repeated measures — each sentence is measured 29 times)
#
# REML = TRUE (default) is preferred for inference on fixed effects.
# Satterthwaite degrees of freedom are used (loaded via lmerTest).

model <- lmer(
  score ~ treatment_type + treatment_type:pivot_config +
    (1 | source) + (1 | source:sentence_id),
  data = df
)

cat("=== Model summary ===\n")
print(summary(model))
cat("\n")

# Variance components: inspect how much variance is attributable to
# source vs sentence-within-source vs residual.
cat("=== Variance components ===\n")
print(VarCorr(model))
cat("\n")

# The source variance tells you whether software programs differ in
# translation difficulty. If it is near zero, source-level blocking
# contributes little, but it costs nothing to include it.


# =============================================================================
# 5. TYPE III ANOVA TABLE
# =============================================================================

# Type III tests with Satterthwaite degrees of freedom.
# This gives F-tests for:
#   - treatment_type: do the three treatment types differ?
#   - treatment_type:pivot_config: do pivot configurations differ within types?
#     (pooled across single-pivot and dual-pivot; direct contributes 0 df)

cat("=== Type III ANOVA ===\n")
anova_table <- anova(model, type = "III", ddf = "Satterthwaite")
print(anova_table)
cat("\n")


# =============================================================================
# 6. MODEL DIAGNOSTICS
# =============================================================================

# 6a. Residual normality
# With ~112,000 observations, the QQ plot will show deviations in the tails
# even for well-behaved data. Focus on the central part of the distribution.
# If you are using BLEU scores, expect right-skew and zero-inflation.
# COMET scores are generally better-behaved.

png(out("diagnostics_qqplot.png"), width = 800, height = 600)
qqnorm(resid(model), main = "QQ Plot of Residuals")
qqline(resid(model), col = "red")
dev.off()
cat("Saved: diagnostics_qqplot.png\n")

# 6b. Homoscedasticity (residuals vs fitted values)
# Look for a fan shape or systematic pattern. If present, consider
# a variance-stabilizing transformation (log, logit for bounded scores).

png(out("diagnostics_residuals_vs_fitted.png"), width = 800, height = 600)
plot(fitted(model), resid(model),
     xlab = "Fitted values", ylab = "Residuals",
     main = "Residuals vs Fitted Values",
     pch = ".", col = rgb(0, 0, 0, 0.1))
abline(h = 0, col = "red", lty = 2)
dev.off()
cat("Saved: diagnostics_residuals_vs_fitted.png\n")

# 6c. Distribution of residuals (histogram)
png(out("diagnostics_residual_hist.png"), width = 800, height = 600)
hist(resid(model), breaks = 100,
     main = "Distribution of Residuals",
     xlab = "Residual", col = "steelblue", border = "white")
dev.off()
cat("Saved: diagnostics_residual_hist.png\n")

# 6d. Random effects diagnostics
# Check that random effects are approximately normal.
png(out("diagnostics_ranef_source.png"), width = 800, height = 600)
qqnorm(ranef(model)$source[, 1], main = "QQ Plot of Source Random Effects")
qqline(ranef(model)$source[, 1], col = "red")
dev.off()
cat("Saved: diagnostics_ranef_source.png\n")

cat("\n=== Diagnostic plots saved. Inspect them before interpreting results. ===\n")
cat("If residuals are severely non-normal (common with BLEU):\n")
cat("  - Consider using COMET scores instead\n")
cat("  - Or apply a transformation (e.g., logit for scores bounded in [0,1])\n")
cat("  - Or use a non-parametric bootstrap (see Section 9)\n\n")


# =============================================================================
# 7. RESEARCH QUESTIONS — ESTIMATED MARGINAL MEANS AND CONTRASTS
# =============================================================================

# -----------------------------------------------------------------------------
# Q1: Do treatment types differ?
# -----------------------------------------------------------------------------
# emmeans with the nesting declaration so it knows pivot_config lives inside
# treatment_type. This lets it properly average over pivot_configs.

cat("=== Q1: Treatment type comparison ===\n\n")

emm_type <- emmeans(model, ~ treatment_type, weights = "equal",
                     nesting = list(pivot_config = "treatment_type"))
cat("Estimated marginal means per treatment type:\n")
print(summary(emm_type))
cat("\n")

# Pairwise comparisons with Bonferroni adjustment (3 comparisons)
pairs_type <- pairs(emm_type, adjust = "bonferroni")
cat("Pairwise comparisons (Bonferroni-adjusted):\n")
print(pairs_type)
cat("\n")

# Confidence intervals for the pairwise differences
cat("Confidence intervals for pairwise differences:\n")
print(confint(pairs_type))
cat("\n")

# Effect sizes (Cohen's d)
cat("Effect sizes (Cohen's d):\n")
eff_type <- eff_size(pairs_type, sigma = sigma(model), edf = df.residual(model))
print(eff_type)
cat("\n")


# -----------------------------------------------------------------------------
# Q2: Do pivot languages differ (single-pivot)?
# -----------------------------------------------------------------------------
# Fit a sub-model on single-pivot data only. This avoids the nesting
# complexity and gives a clean comparison among the 7 pivot languages.
# The random-effects structure is identical to the main model.

cat("=== Q2: Single-pivot configuration comparison ===\n\n")

df_single <- df %>% filter(treatment_type == "single_pivot")
df_single$pivot_config <- droplevels(df_single$pivot_config)

model_single <- lmer(
  score ~ pivot_config + (1 | source) + (1 | source:sentence_id),
  data = df_single
)

emm_single <- emmeans(model_single, ~ pivot_config)
cat("Estimated marginal means per pivot language:\n")
print(summary(emm_single))
cat("\n")

# Pairwise comparisons with Tukey adjustment (21 comparisons among 7 levels)
pairs_single <- pairs(emm_single, adjust = "tukey")
cat("Pairwise comparisons (Tukey-adjusted):\n")
print(pairs_single)
cat("\n")

# Compact letter display: languages sharing a letter are NOT significantly different.
# This is the clearest way to present the ranking in a paper.
cat("Compact letter display (shared letters = not significantly different):\n")
cld_single <- cld(emm_single, Letters = letters, adjust = "tukey")
print(cld_single)
cat("\n")


# -----------------------------------------------------------------------------
# Q3: Do pivot-language pairs differ (dual-pivot)?
# -----------------------------------------------------------------------------
# Same approach: fit a sub-model on dual-pivot data only.

cat("=== Q3: Dual-pivot configuration comparison ===\n\n")

df_dual <- df %>% filter(treatment_type == "dual_pivot")
df_dual$pivot_config <- droplevels(df_dual$pivot_config)

model_dual <- lmer(
  score ~ pivot_config + (1 | source) + (1 | source:sentence_id),
  data = df_dual
)

emm_dual <- emmeans(model_dual, ~ pivot_config)
cat("Estimated marginal means per pivot-language pair:\n")
print(summary(emm_dual))
cat("\n")

# Full pairwise: 210 comparisons. Printed for completeness but likely
# too many to report in a paper. See below for a focused alternative.
pairs_dual <- pairs(emm_dual, adjust = "tukey")
cat("Pairwise comparisons (Tukey-adjusted, 210 comparisons):\n")
print(pairs_dual)
cat("\n")

# Compact letter display for dual-pivot
cat("Compact letter display:\n")
cld_dual <- cld(emm_dual, Letters = letters, adjust = "tukey")
print(cld_dual)
cat("\n")

# Focused alternative: compare all configurations against the best one
# (Dunnett-style). This is more interpretable for the paper.
dual_summary <- summary(emm_dual)
best_idx <- which.max(dual_summary$emmean)
best_config <- as.character(dual_summary$pivot_config[best_idx])
cat("Best dual-pivot configuration:", best_config, "\n\n")

# Dunnett comparisons against the best
cat("Dunnett-style comparisons against the best configuration:\n")
dunnett_dual <- contrast(emm_dual, method = "trt.vs.ctrl", ref = best_idx,
                          adjust = "dunnett")
print(dunnett_dual)
cat("\n")


# =============================================================================
# 8. PRACTICAL SIGNIFICANCE
# =============================================================================

# With ~3,900 sentences you have enormous statistical power. Many differences
# will be statistically significant but practically meaningless.
# Always report and discuss the raw difference in score points alongside
# p-values and CIs.

cat("=== Practical significance note ===\n")
cat("Check the 'estimate' column in pairwise comparisons.\n")
cat("A difference of, e.g., 0.3 COMET points may be p < 0.001 but\n")
cat("practically irrelevant. Discuss what magnitude of difference\n")
cat("matters for your application.\n\n")


# =============================================================================
# 9. BOOTSTRAP CONFIDENCE INTERVALS (OPTIONAL BUT RECOMMENDED)
# =============================================================================

# The MT/NLP community commonly uses paired bootstrap resampling
# (Koehn, 2004) to construct confidence intervals. This section provides
# a non-parametric bootstrap that does not rely on LMM normality assumptions.
# It complements the parametric analysis above.
#
# This resamples sentences (the unit of observation) with replacement,
# respecting the within-subjects structure.

cat("=== Bootstrap confidence intervals (resampling sentences) ===\n")
cat("This may take a few minutes...\n\n")

set.seed(42)  # Reproducibility
n_boot <- 10000

# Pivot data to wide format: one row per sentence, one column per condition
wide <- df %>%
  select(sentence_id, treatment_type, pivot_config, score) %>%
  unite("condition", treatment_type, pivot_config, sep = "::") %>%
  pivot_wider(names_from = condition, values_from = score)

sentence_ids <- wide$sentence_id
score_matrix <- as.matrix(wide[, -1])  # Remove sentence_id column
n_sentences  <- nrow(score_matrix)

# Identify column indices for each treatment type.
# Column names are "treatment_type::pivot_config".
col_names     <- colnames(score_matrix)
direct_cols   <- grep("^direct::", col_names)
single_cols   <- grep("^single_pivot::", col_names)
dual_cols     <- grep("^dual_pivot::", col_names)

# Bootstrap: resample sentences with replacement
# Note: na.rm = TRUE handles the 876 sentences from diffutils/nano
# that are missing one condition each.
boot_diffs <- matrix(NA, nrow = n_boot, ncol = 3)
colnames(boot_diffs) <- c("direct_vs_single", "direct_vs_dual", "single_vs_dual")

for (b in 1:n_boot) {
  idx <- sample(1:n_sentences, n_sentences, replace = TRUE)
  boot_sample <- score_matrix[idx, ]

  # Marginal means per treatment type (equal weight across configs)
  mean_direct <- mean(boot_sample[, direct_cols], na.rm = TRUE)
  mean_single <- mean(rowMeans(boot_sample[, single_cols], na.rm = TRUE), na.rm = TRUE)
  mean_dual   <- mean(rowMeans(boot_sample[, dual_cols], na.rm = TRUE), na.rm = TRUE)

  boot_diffs[b, 1] <- mean_direct - mean_single
  boot_diffs[b, 2] <- mean_direct - mean_dual
  boot_diffs[b, 3] <- mean_single - mean_dual
}

# 95% percentile bootstrap CIs
cat("Bootstrap 95% CIs for treatment-type differences:\n")
for (j in 1:3) {
  ci <- quantile(boot_diffs[, j], probs = c(0.025, 0.975))
  cat(sprintf("  %s: mean = %.4f, 95%% CI = [%.4f, %.4f]\n",
              colnames(boot_diffs)[j], mean(boot_diffs[, j]), ci[1], ci[2]))
}
cat("\n")


# =============================================================================
# 10. VISUALIZATION
# =============================================================================

# Helper: normalize CI column names from emmeans summary.
# With large N, emmeans uses asymptotic df and names columns
# "asymp.LCL"/"asymp.UCL" instead of "lower.CL"/"upper.CL".
normalize_ci <- function(df) {
  names(df) <- gsub("^asymp\\.LCL$", "lower.CL", names(df))
  names(df) <- gsub("^asymp\\.UCL$", "upper.CL", names(df))
  df
}

# 10a. Treatment type comparison
emm_type_df <- normalize_ci(as.data.frame(summary(emm_type)))
p1 <- ggplot(emm_type_df, aes(x = treatment_type, y = emmean)) +
  geom_point(size = 3) +
  geom_errorbar(aes(ymin = lower.CL, ymax = upper.CL), width = 0.2) +
  labs(title = "Q1: Treatment Type Comparison",
       subtitle = "Estimated marginal means with 95% CIs",
       x = "Treatment Type", y = "Score") +
  theme_minimal(base_size = 14)
ggsave(out("plot_q1_treatment_types.png"), p1, width = 8, height = 6)
cat("Saved: plot_q1_treatment_types.png\n")

# 10b. Single-pivot ranking
cld_single_df <- normalize_ci(as.data.frame(cld_single))
cld_single_df$.group <- trimws(cld_single_df$.group)
cld_single_df <- cld_single_df %>% arrange(desc(emmean))

p2 <- ggplot(cld_single_df,
             aes(x = reorder(pivot_config, emmean), y = emmean)) +
  geom_point(size = 3) +
  geom_errorbar(aes(ymin = lower.CL, ymax = upper.CL), width = 0.2) +
  geom_text(aes(label = .group), vjust = -1, size = 4) +
  labs(title = "Q2: Single-Pivot Language Ranking",
       subtitle = "Shared letters = not significantly different (Tukey)",
       x = "Pivot Language", y = "Score") +
  theme_minimal(base_size = 14) +
  coord_flip()
ggsave(out("plot_q2_single_pivot.png"), p2, width = 8, height = 6)
cat("Saved: plot_q2_single_pivot.png\n")

# 10c. Dual-pivot ranking (top 10 for readability)
cld_dual_df <- normalize_ci(as.data.frame(cld_dual))
cld_dual_df$.group <- trimws(cld_dual_df$.group)
cld_dual_df <- cld_dual_df %>% arrange(desc(emmean))

p3 <- ggplot(cld_dual_df %>% head(10),
             aes(x = reorder(pivot_config, emmean), y = emmean)) +
  geom_point(size = 3) +
  geom_errorbar(aes(ymin = lower.CL, ymax = upper.CL), width = 0.2) +
  geom_text(aes(label = .group), vjust = -1, size = 4) +
  labs(title = "Q3: Top 10 Dual-Pivot Pairs",
       subtitle = "Shared letters = not significantly different (Tukey)",
       x = "Pivot Language Pair", y = "Score") +
  theme_minimal(base_size = 14) +
  coord_flip()
ggsave(out("plot_q3_dual_pivot_top10.png"), p3, width = 10, height = 6)
cat("Saved: plot_q3_dual_pivot_top10.png\n")


# =============================================================================
# 11. EXPORT RESULTS TO CSV (for inclusion in paper tables)
# =============================================================================

write.csv(emm_type_df,
          out("results_q1_treatment_means.csv"), row.names = FALSE)

write.csv(as.data.frame(pairs_type),
          out("results_q1_pairwise.csv"), row.names = FALSE)

write.csv(cld_single_df,
          out("results_q2_single_pivot_cld.csv"), row.names = FALSE)

write.csv(cld_dual_df,
          out("results_q3_dual_pivot_cld.csv"), row.names = FALSE)

write.csv(as.data.frame(dunnett_dual),
          out("results_q3_dunnett_vs_best.csv"), row.names = FALSE)

cat("\nAll result tables saved as CSV files.\n")


# =============================================================================
# CSV INPUT FILE FORMAT
# =============================================================================
#
# File name: experiment_data.csv
# Encoding: UTF-8
# Separator: comma
# One row per sentence x condition combination (~112,000 rows + header)
#
# Columns:
#   sentence_id    - Unique identifier for each sentence (e.g., "s00001")
#   source         - Software program the sentence comes from (e.g.,
#                    "aspell_v0.60.8.1", "wget_v1.25.0"). Blocking factor.
#   treatment_type - One of: "direct", "single_pivot", "dual_pivot"
#   pivot_config   - Specific configuration within the treatment type:
#                      - "none" for direct translation
#                      - Language code for single-pivot (e.g., "ru", "fr", "de",
#                        "es", "id", "vi", "zh_cn")
#                      - Language pair for dual-pivot, sorted alphabetically and
#                        joined with underscore (e.g., "de_fr", "es_zh_cn")
#                        IMPORTANT: always use the same order (alphabetical) so
#                        that "ru_fr" and "fr_ru" are not treated as different
#                        conditions.
#   score          - Translation quality metric (BLEU score).
#                    If using BLEU, expect assumption violations and consider
#                    the bootstrap analysis (Section 9) as the primary result.
#
# =============================================================================
