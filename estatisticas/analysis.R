# =============================================================================
# Analysis of Multi-Source Translation with Small Language Models
# =============================================================================
#
# Design: Nested within-subjects (repeated measures)
#   - Fixed factor A: treatment_type (3 levels: direct, single_context, dual_context)
#   - Fixed factor B(A): context_config, nested within treatment_type
#       - direct:       1 level  ("none")
#       - single_context: 7 levels (one per context language)
#       - dual_context:  21 levels (one per pair of context languages)
#   - Random factor: sentence nested within source_project (blocking)
#   - Every sentence is observed under all 29 conditions
#
# Research questions:
#   Q1: Do treatment types differ (direct vs single-context vs dual-context)?
#   Q2: Do context languages differ within the single-context treatment?
#   Q3: Do context-language pairs differ within the dual-context treatment?
#
# CSV file format (see end of script for details)
# =============================================================================


# =============================================================================
# 1. REQUIRED PACKAGES
# =============================================================================

library(lme4) # Mixed-effects models
library(lmerTest) # Satterthwaite degrees of freedom & p-values for lmer
library(emmeans) # Estimated marginal means and contrasts
library(multcomp) # Compact letter displays
library(ggplot2) # Plots
library(dplyr) # Data manipulation
library(tidyr) # pivot_wider / unite (used in bootstrap section)
library(performance) # Model diagnostics


# =============================================================================
# 2. LOAD AND PREPARE DATA
# =============================================================================

# Resolve paths relative to this script's location so output files
# always land in estatisticas/ regardless of the working directory.
# Works with Rscript, source(), and RStudio.
get_script_dir <- function() {
  # Rscript via commandArgs
  args <- commandArgs(trailingOnly = FALSE)
  file_arg <- grep("^--file=", args, value = TRUE)
  if (length(file_arg) > 0) {
    return(dirname(normalizePath(sub("^--file=", "", file_arg[1]))))
  }
  # source()
  if (!is.null(sys.frame(1)$ofile)) {
    return(dirname(normalizePath(sys.frame(1)$ofile)))
  }
  # fallback: working directory
  return(getwd())
}
script_dir <- get_script_dir()
out <- function(filename) file.path(script_dir, filename)

df <- read.csv(out("experiment_data.csv"), stringsAsFactors = FALSE)

# Ensure factors are properly encoded.
# sentence_id and source_project must be factors for the random effects.
# treatment_type and context_config must be factors for the fixed effects.
df$sentence_id <- as.factor(df$sentence_id)
df$source_project <- as.factor(df$source_project)
df$treatment_type <- as.factor(df$treatment_type)
df$context_config <- as.factor(df$context_config)

# Set the reference level for treatment_type to "direct" so that
# model coefficients are interpreted relative to direct translation.
df$treatment_type <- relevel(df$treatment_type, ref = "direct")

# Basic sanity checks
cat("=== Data summary ===\n")
cat("Total rows:", nrow(df), "\n")
cat("Unique sentences:", nlevels(df$sentence_id), "\n")
cat("Unique sources:", nlevels(df$source_project), "\n")
cat("Conditions per sentence:", nrow(df) / nlevels(df$sentence_id), "\n\n")

cat("=== Observations per treatment type ===\n")
print(table(df$treatment_type))
cat("\n")

cat("=== Observations per context_config ===\n")
print(table(df$treatment_type, df$context_config))
cat("\n")

cat("=== Sentences per source_project ===\n")
print(table(df$source_project))
cat("\n")

# Verify the design is complete: every sentence should appear in all 29 conditions.
conditions_per_sentence <- df %>%
  group_by(sentence_id) %>%
  summarise(n_conditions = n_distinct(context_config))

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

cat("=== Descriptive statistics by context_config (single-context) ===\n")
desc_single <- df %>%
  filter(treatment_type == "single_context") %>%
  group_by(context_config) %>%
  summarise(
    mean   = mean(score),
    sd     = sd(score),
    median = median(score),
    n      = n()
  ) %>%
  arrange(desc(mean))
print(desc_single)
cat("\n")

cat("=== Descriptive statistics by context_config (dual-context) ===\n")
desc_dual <- df %>%
  filter(treatment_type == "dual_context") %>%
  group_by(context_config) %>%
  summarise(
    mean   = mean(score),
    sd     = sd(score),
    median = median(score),
    n      = n()
  ) %>%
  arrange(desc(mean))
print(desc_dual)
cat("\n")

cat("=== Descriptive statistics by source_project ===\n")
desc_source <- df %>%
  group_by(source_project) %>%
  summarise(
    mean       = mean(score),
    sd         = sd(score),
    median     = median(score),
    min        = min(score),
    max        = max(score),
    n          = n(),
    n_sentences = n_distinct(sentence_id)
  ) %>%
  arrange(desc(mean))
print(desc_source)
cat("\n")

# Export descriptive statistics to CSV
write.csv(desc_type, out("desc_by_treatment_type.csv"), row.names = FALSE)
write.csv(desc_single, out("desc_by_single_context.csv"), row.names = FALSE)
write.csv(desc_dual, out("desc_by_dual_context.csv"), row.names = FALSE)
write.csv(desc_source, out("desc_by_source_project.csv"), row.names = FALSE)
cat("Saved: desc_by_treatment_type.csv, desc_by_single_context.csv,\n")
cat("       desc_by_dual_context.csv, desc_by_source_project.csv\n\n")


# =============================================================================
# 4. FIT THE LINEAR MIXED-EFFECTS MODEL
# =============================================================================

# Model specification:
#   - treatment_type: main fixed effect (3 levels)
#   - treatment_type:context_config: context configuration nested within treatment type
#   - (1 | source_project): random intercept for source_project (blocking factor —
#     some software programs are systematically harder to translate)
#   - (1 | source_project:sentence_id): random intercept for sentence nested within
#     source_project
#     (accounts for repeated measures — each sentence is measured 29 times)
#
# REML = TRUE (default) is preferred for inference on fixed effects.
# Satterthwaite degrees of freedom are used (loaded via lmerTest).

model <- lmer(
  score ~ treatment_type + treatment_type:context_config +
    (1 | source_project) + (1 | source_project:sentence_id),
  data = df
)

cat("=== Model summary ===\n")
print(summary(model))
cat("\n")

# Variance components: inspect how much variance is attributable to
# source_project vs sentence-within-source_project vs residual.
cat("=== Variance components ===\n")
print(VarCorr(model))
cat("\n")

# The source_project variance tells you whether software programs differ in
# translation difficulty. If it is near zero, source_project-level blocking
# contributes little, but it costs nothing to include it.

# R² (Nakagawa & Schielzeth, 2013):
#   - Marginal R²:    variance explained by fixed effects alone
#   - Conditional R²: variance explained by fixed + random effects
cat("=== R² (Nakagawa) ===\n")
r2 <- r2_nakagawa(model)
print(r2)
cat("\n")


# =============================================================================
# 5. TYPE III ANOVA TABLE
# =============================================================================

# Type III tests with Satterthwaite degrees of freedom.
# This gives F-tests for:
#   - treatment_type: do the three treatment types differ?
#   - treatment_type:context_config: do context configurations differ within types?
#     (pooled across single-context and dual-context; direct contributes 0 df)

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
  pch = ".", col = rgb(0, 0, 0, 0.1)
)
abline(h = 0, col = "red", lty = 2)
dev.off()
cat("Saved: diagnostics_residuals_vs_fitted.png\n")

# 6c. Distribution of residuals (histogram)
png(out("diagnostics_residual_hist.png"), width = 800, height = 600)
hist(resid(model),
  breaks = 100,
  main = "Distribution of Residuals",
  xlab = "Residual", col = "steelblue", border = "white"
)
dev.off()
cat("Saved: diagnostics_residual_hist.png\n")

# 6d. Random effects diagnostics
# Check that random effects are approximately normal.
png(out("diagnostics_ranef_source.png"), width = 800, height = 600)
qqnorm(ranef(model)$source_project[, 1], main = "QQ Plot of Source Random Effects")
qqline(ranef(model)$source_project[, 1], col = "red")
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
# emmeans with the nesting declaration so it knows context_config lives inside
# treatment_type. This lets it properly average over context_configs.

cat("=== Q1: Treatment type comparison ===\n\n")

emm_type <- emmeans(model, ~treatment_type,
  weights = "equal",
  nesting = list(context_config = "treatment_type")
)
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
# Q2: Do context languages differ (single-context)?
# -----------------------------------------------------------------------------
# Fit a sub-model on single-context data only. This avoids the nesting
# complexity and gives a clean comparison among the 7 context languages.
# The random-effects structure is identical to the main model.

cat("=== Q2: Single-context configuration comparison ===\n\n")

df_single <- df %>% filter(treatment_type == "single_context")
df_single$context_config <- droplevels(df_single$context_config)

model_single <- lmer(
  score ~ context_config + (1 | source_project) + (1 | source_project:sentence_id),
  data = df_single
)

emm_single <- emmeans(model_single, ~context_config)
cat("Estimated marginal means per context language:\n")
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
# Q3: Do context-language pairs differ (dual-context)?
# -----------------------------------------------------------------------------
# Same approach: fit a sub-model on dual-context data only.

cat("=== Q3: Dual-context configuration comparison ===\n\n")

df_dual <- df %>% filter(treatment_type == "dual_context")
df_dual$context_config <- droplevels(df_dual$context_config)

model_dual <- lmer(
  score ~ context_config + (1 | source_project) + (1 | source_project:sentence_id),
  data = df_dual
)

emm_dual <- emmeans(model_dual, ~context_config)
cat("Estimated marginal means per context-language pair:\n")
print(summary(emm_dual))
cat("\n")

# Full pairwise: 210 comparisons. Printed for completeness but likely
# too many to report in a paper. See below for a focused alternative.
pairs_dual <- pairs(emm_dual, adjust = "tukey")
cat("Pairwise comparisons (Tukey-adjusted, 210 comparisons):\n")
print(pairs_dual)
cat("\n")

# Compact letter display for dual-context
cat("Compact letter display:\n")
cld_dual <- cld(emm_dual, Letters = letters, adjust = "tukey")
print(cld_dual)
cat("\n")

# Focused alternative: compare all configurations against the best one
# (Dunnett-style). This is more interpretable for the paper.
dual_summary <- summary(emm_dual)
best_idx <- which.max(dual_summary$emmean)
best_config <- as.character(dual_summary$context_config[best_idx])
cat("Best dual-context configuration:", best_config, "\n\n")

# Dunnett comparisons against the best
cat("Dunnett-style comparisons against the best configuration:\n")
dunnett_dual <- contrast(emm_dual,
  method = "trt.vs.ctrl", ref = best_idx,
  adjust = "dunnett"
)
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
# HOW THE BOOTSTRAP WORKS
#
# The bootstrap is a resampling technique for estimating the sampling
# distribution of a statistic without relying on parametric assumptions
# (Efron and Tibshirani, 1993). The core idea is simple: if the observed
# sample is the best available approximation of the population, then
# drawing repeated samples *from the observed data itself* (with
# replacement) simulates what would happen if the experiment were
# repeated many times.
#
# In this experiment, the unit of resampling is the sentence (not the
# individual score). Each sentence has 29 scores (one per condition),
# and all 29 scores travel together when a sentence is resampled. This
# preserves the within-subjects (repeated-measures) pairing: every
# bootstrap sample compares the same sentences under different
# treatments, just as the original experiment does. This is why it is
# called a "paired" bootstrap — the pairing of scores within sentences
# is maintained.
#
# STEP-BY-STEP PROCEDURE
#
# 1. Reshape the data to wide format: one row per sentence, one column
#    per condition (29 columns). This creates a 3,896 x 29 score matrix.
#
# 2. For each bootstrap iteration (10,000 total):
#    a. Draw a random sample of 3,896 sentences WITH REPLACEMENT from
#       the 3,896 original sentences. Some sentences will appear
#       multiple times, others not at all — this is intentional and is
#       what generates sampling variability.
#    b. For the resampled set, compute the mean score for each treatment
#       type. Within single-context and dual-context, each context
#       configuration is weighted equally (by computing per-sentence
#       row means first, then averaging across sentences), matching the
#       equal-weight approach used by emmeans in the LMM analysis.
#    c. Compute the three pairwise differences between treatment-type
#       means and store them.
#
# 3. After all 10,000 iterations, the stored differences form the
#    bootstrap sampling distribution. The 2.5th and 97.5th percentiles
#    of this distribution give the 95% bootstrap confidence interval.
#
# INTERPRETATION
#
# If the 95% CI for a difference excludes zero, the difference is
# statistically significant at the 5% level. The bootstrap CI is
# analogous to the parametric CI from the LMM but makes no assumptions
# about the shape of the score distribution. When both methods agree
# (as they do here), this strengthens confidence in the results.

cat("=== Bootstrap confidence intervals (resampling sentences) ===\n")
cat("This may take a few minutes...\n\n")

set.seed(42) # Reproducibility
n_boot <- 10000

# Pivot data to wide format: one row per sentence, one column per condition
wide <- df %>%
  select(sentence_id, treatment_type, context_config, score) %>%
  unite("condition", treatment_type, context_config, sep = "::") %>%
  pivot_wider(names_from = condition, values_from = score)

sentence_ids <- wide$sentence_id
score_matrix <- as.matrix(wide[, -1]) # Remove sentence_id column
n_sentences <- nrow(score_matrix)

# Identify column indices for each treatment type.
# Column names are "treatment_type::context_config".
col_names <- colnames(score_matrix)
direct_cols <- grep("^direct::", col_names)
single_cols <- grep("^single_context::", col_names)
dual_cols <- grep("^dual_context::", col_names)

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
  mean_dual <- mean(rowMeans(boot_sample[, dual_cols], na.rm = TRUE), na.rm = TRUE)

  boot_diffs[b, 1] <- mean_direct - mean_single
  boot_diffs[b, 2] <- mean_direct - mean_dual
  boot_diffs[b, 3] <- mean_single - mean_dual
}

# 95% percentile bootstrap CIs
cat("Bootstrap 95% CIs for treatment-type differences:\n")
for (j in 1:3) {
  ci <- quantile(boot_diffs[, j], probs = c(0.025, 0.975))
  cat(sprintf(
    "  %s: mean = %.4f, 95%% CI = [%.4f, %.4f]\n",
    colnames(boot_diffs)[j], mean(boot_diffs[, j]), ci[1], ci[2]
  ))
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
  labs(
    title = "Q1: Treatment Type Comparison",
    subtitle = "Estimated marginal means with 95% CIs",
    x = "Treatment Type", y = "Score"
  ) +
  theme_minimal(base_size = 14)
ggsave(out("plot_q1_treatment_types.png"), p1, width = 8, height = 6)
cat("Saved: plot_q1_treatment_types.png\n")

# 10b. Single-context ranking
cld_single_df <- normalize_ci(as.data.frame(cld_single))
cld_single_df$.group <- trimws(cld_single_df$.group)
cld_single_df <- cld_single_df %>% arrange(desc(emmean))

p2 <- ggplot(
  cld_single_df,
  aes(x = reorder(context_config, emmean), y = emmean)
) +
  geom_point(size = 3) +
  geom_errorbar(aes(ymin = lower.CL, ymax = upper.CL), width = 0.2) +
  geom_text(aes(label = .group), vjust = -1, size = 4) +
  labs(
    title = "Q2: Single-context Language Ranking",
    subtitle = "Shared letters = not significantly different (Tukey)",
    x = "Context Language", y = "Score"
  ) +
  theme_minimal(base_size = 14) +
  coord_flip()
ggsave(out("plot_q2_single_context.png"), p2, width = 8, height = 6)
cat("Saved: plot_q2_single_context.png\n")

# 10c. Dual-context ranking (top 10 for readability)
cld_dual_df <- normalize_ci(as.data.frame(cld_dual))
cld_dual_df$.group <- trimws(cld_dual_df$.group)
cld_dual_df <- cld_dual_df %>% arrange(desc(emmean))

p3 <- ggplot(
  cld_dual_df %>% head(10),
  aes(x = reorder(context_config, emmean), y = emmean)
) +
  geom_point(size = 3) +
  geom_errorbar(aes(ymin = lower.CL, ymax = upper.CL), width = 0.2) +
  geom_text(aes(label = .group), vjust = -1, size = 4) +
  labs(
    title = "Q3: Top 10 Dual-Context Pairs",
    subtitle = "Shared letters = not significantly different (Tukey)",
    x = "Context Language Pair", y = "Score"
  ) +
  theme_minimal(base_size = 14) +
  coord_flip()
ggsave(out("plot_q3_dual_context_top10.png"), p3, width = 10, height = 6)
cat("Saved: plot_q3_dual_context_top10.png\n")

# 10d. Score distribution by treatment type (boxplot)
# Order: direct, single_context, dual_context
df$treatment_type <- factor(df$treatment_type,
  levels = c("direct", "single_context", "dual_context"))
p4 <- ggplot(df, aes(x = treatment_type, y = score, fill = treatment_type)) +
  geom_boxplot(outlier.size = 0.3, outlier.alpha = 0.2) +
  labs(
    title = "Score Distribution by Treatment Type",
    x = "Treatment Type", y = "BLEU Score"
  ) +
  theme_minimal(base_size = 14) +
  theme(legend.position = "none")
ggsave(out("plot_dist_treatment_type.png"), p4, width = 8, height = 6)
cat("Saved: plot_dist_treatment_type.png\n")

# 10e. Score distribution by context language (single-context only)
# Alphabetical order
p5 <- ggplot(
  df %>% filter(treatment_type == "single_context"),
  aes(x = context_config, y = score, fill = context_config)
) +
  geom_boxplot(outlier.size = 0.3, outlier.alpha = 0.2) +
  labs(
    title = "Score Distribution by Context Language (Single-Context)",
    x = "Context Language", y = "BLEU Score"
  ) +
  theme_minimal(base_size = 14) +
  theme(legend.position = "none") +
  coord_flip()
ggsave(out("plot_dist_single_context.png"), p5, width = 8, height = 6)
cat("Saved: plot_dist_single_context.png\n")

# 10f. Score distribution by source project (alphabetical order)
p6 <- ggplot(df, aes(x = source_project, y = score, fill = source_project)) +
  geom_boxplot(outlier.size = 0.3, outlier.alpha = 0.2) +
  labs(
    title = "Score Distribution by Source Project",
    x = "Source Project", y = "BLEU Score"
  ) +
  theme_minimal(base_size = 14) +
  theme(legend.position = "none") +
  coord_flip()
ggsave(out("plot_dist_source_project.png"), p6, width = 10, height = 8)
cat("Saved: plot_dist_source_project.png\n")

# 10g. Score histogram faceted by treatment type
# Order: direct, single_context, dual_context
p7 <- ggplot(df, aes(x = score, fill = treatment_type)) +
  geom_histogram(binwidth = 2, boundary = 0, color = "white", linewidth = 0.1) +
  facet_wrap(~treatment_type, ncol = 1, scales = "free_y") +
  labs(
    title = "Score Histogram by Treatment Type",
    x = "BLEU Score", y = "Count"
  ) +
  theme_minimal(base_size = 14) +
  theme(legend.position = "none")
ggsave(out("plot_hist_treatment_type.png"), p7, width = 8, height = 8)
cat("Saved: plot_hist_treatment_type.png\n")


# =============================================================================
# 11. EXPORT RESULTS TO CSV (for inclusion in paper tables)
# =============================================================================

write.csv(emm_type_df,
  out("results_q1_treatment_means.csv"),
  row.names = FALSE
)

write.csv(as.data.frame(pairs_type),
  out("results_q1_pairwise.csv"),
  row.names = FALSE
)

write.csv(cld_single_df,
  out("results_q2_single_context_cld.csv"),
  row.names = FALSE
)

write.csv(cld_dual_df,
  out("results_q3_dual_context_cld.csv"),
  row.names = FALSE
)

write.csv(as.data.frame(dunnett_dual),
  out("results_q3_dunnett_vs_best.csv"),
  row.names = FALSE
)

cat("\nAll result tables saved as CSV files.\n")

cat("\n=== Generated files ===\n")
generated <- c(
  "desc_by_treatment_type.csv",
  "desc_by_single_context.csv",
  "desc_by_dual_context.csv",
  "desc_by_source_project.csv",
  "diagnostics_qqplot.png",
  "diagnostics_residuals_vs_fitted.png",
  "diagnostics_residual_hist.png",
  "diagnostics_ranef_source.png",
  "plot_q1_treatment_types.png",
  "plot_q2_single_context.png",
  "plot_q3_dual_context_top10.png",
  "plot_dist_treatment_type.png",
  "plot_dist_single_context.png",
  "plot_dist_source_project.png",
  "plot_hist_treatment_type.png",
  "results_q1_treatment_means.csv",
  "results_q1_pairwise.csv",
  "results_q2_single_context_cld.csv",
  "results_q3_dual_context_cld.csv",
  "results_q3_dunnett_vs_best.csv"
)
for (f in generated) {
  path <- out(f)
  if (file.exists(path)) {
    cat(sprintf("  %s (%s)\n", f, format(file.size(path), big.mark = ",")))
  } else {
    cat(sprintf("  %s (MISSING)\n", f))
  }
}


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
#   source_project - Software program the sentence comes from (e.g.,
#                    "aspell_v0.60.8.1", "wget_v1.25.0"). Blocking factor.
#   treatment_type - One of: "direct", "single_context", "dual_context"
#   context_config   - Specific configuration within the treatment type:
#                      - "none" for direct translation
#                      - Language code for single-context (e.g., "ru", "fr", "de",
#                        "es", "id", "vi", "zh_cn")
#                      - Language pair for dual-context, sorted alphabetically and
#                        joined with underscore (e.g., "de_fr", "es_zh_cn")
#                        IMPORTANT: always use the same order (alphabetical) so
#                        that "ru_fr" and "fr_ru" are not treated as different
#                        conditions.
#   score          - Translation quality metric (BLEU score).
#                    If using BLEU, expect assumption violations and consider
#                    the bootstrap analysis (Section 9) as the primary result.
#
# =============================================================================
