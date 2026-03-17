Experimental Design: Multi-Source Translation with Small Language Models
========================================================================


1. Goal
-------

The experiment investigates whether multi-source translation improves
the quality of machine translation from English to Brazilian Portuguese
when using small language models (SLMs).

Multi-source translation is a well-established approach in which the
translation system receives the same sentence in multiple languages and
uses all of them together to produce the target translation (Zoph and
Knight, 2016). Rather than translating from a single source, the system
leverages parallel inputs in additional languages as complementary
signals that help resolve ambiguities in word choice, word ordering,
and meaning.

This is distinct from pivot translation, where the source text is
translated to an intermediate language and then translated from that
intermediate language to the target, with the original source discarded
after the first step. In multi-source translation, the original source
is always retained alongside the additional inputs.

In the neural machine translation literature, the additional languages
in a multi-source setup are typically called auxiliary source languages
(Xu et al., 2021) and are fed through dedicated encoder components.
When multi-source translation is instead implemented via in-context
prompting of large or small language models, the additional translations
are provided as textual context within the prompt. Following
Shahnazaryan et al. (2025), who study this exact prompting strategy,
this experiment refers to the additional languages as context languages
and adopts their naming schema for the treatment types.

In the present experiment, the SLM receives the English source sentence
together with human-produced translations of that sentence in one or
two context languages, and is prompted to produce the Brazilian
Portuguese translation using all provided inputs. The experiment
evaluates whether this approach produces better results than direct
source-to-target translation, whether using two context languages is
better than one, and which context language or combination of context
languages yields the highest translation quality for the English–
Brazilian Portuguese pair.


2. Variables
------------

The dependent variable (response variable) is translation quality,
measured per sentence using BLEU (Bilingual Evaluation Understudy).
BLEU is a standard automatic metric in machine translation research
that measures n-gram overlap between the machine translation and a
human reference translation. At the sentence level, BLEU scores are
bounded between 0 and 1 (or 0 and 100 when scaled) and tend to be
noisy, zero-inflated (many sentences receive a score of exactly zero),
and right-skewed. These properties can violate the normality
assumptions of linear mixed-effects models. The analysis therefore
includes diagnostic checks for residual normality and provides a
non-parametric paired bootstrap as a complementary inference method
that does not rely on distributional assumptions.

The independent variables are all variables in the process that are
manipulated or controlled:

  - Treatment type and context configuration (factors): which
    translation strategy is applied and which context language(s) are
    provided to the SLM. These are the variables whose effect the
    experiment seeks to study. They are structured as two nested
    factors (see Section 3).

  - Source project: the software program from which each sentence
    originates. This independent variable is not a factor — it is not
    manipulated to study its effect — but it is controlled through
    blocking (see Section 5).

  - Source language (English), target language (Brazilian Portuguese),
    the SLM used, the prompt template, and all other aspects of the
    translation pipeline are held constant throughout the experiment.


3. Factors and Treatments
--------------------------

The experiment has two factors arranged in a nested hierarchy.

Treatment type is the main factor, with three levels (following the
naming schema of Shahnazaryan et al., 2025):

  - Direct translation: the SLM receives only the source sentence in
    English and translates it directly to Brazilian Portuguese.

  - Single-context translation: the SLM receives the source sentence
    in English together with a human-produced translation of that
    sentence in one context language, and uses both to produce the
    Brazilian Portuguese translation.

  - Double-context translation: the SLM receives the source sentence
    in English together with human-produced translations of that
    sentence in two context languages, and uses all three to produce
    the Brazilian Portuguese translation.

Context configuration is the second factor, nested within treatment
type. It specifies which context language(s) are provided in each
condition:

  - Within direct translation: 1 level (none — no context language is
    provided).
  - Within single-context translation: 7 levels (one per context
    language).
  - Within double-context translation: 21 levels (one per unordered
    pair of context languages, i.e., C(7,2) = 21).

Context configuration is nested, not crossed, because its levels only
exist within the context of their parent treatment type. A single-
context configuration such as "Russian" and a double-context
configuration such as "Russian + French" are not comparable levels of
the same variable — they belong to different treatment types and
involve structurally different inputs to the SLM. This nesting produces
an inherently unequal number of sub-conditions per treatment type (1,
7, and 21), which is a structural feature of the design, not a flaw.
Montgomery (2019) discusses nested factor designs in detail; the
present design extends the standard nested layout with repeated
measures across all treatments.

A treatment is one specific value of the combined factors — that is,
one particular translation strategy applied to the SLM. The experiment
has 29 treatments in total: 1 direct treatment, 7 single-context
treatments (one per context language), and 21 double-context treatments
(one per pair of context languages).

The seven context languages are fixed and identical across all
treatments that use them. The context translations are human-produced
and taken from existing multilingual corpora; they are not generated by
the SLM.


4. Objects
----------

The objects are the sentences to which the treatments are applied. The
experiment uses approximately 3,900 sentences, all of which are UI
strings from open-source software programs. Every sentence is translated
under all 29 treatments, which makes this a within-subjects (repeated-
measures) design: the same object is observed across all treatments,
controlling for inherent differences in translation difficulty by
allowing each object to serve as its own baseline.


5. Blocking and Nesting of Objects
----------------------------------

The approximately 3,900 sentences originate from 17 different software
programs (e.g., aspell, wget, nano). Each software program
constitutes a source project. Sentences within the same source project
share characteristics — vocabulary, domain jargon, sentence complexity,
interface conventions — that affect translation difficulty but are not
of research interest.

Source project is a blocking factor: it is included in the statistical
model to absorb this nuisance variation, not because the researcher
wants to study its effect. As Montgomery (2019) describes, blocking is
a technique to reduce the impact of known nuisance variables by
grouping experimental units into homogeneous blocks; variability among
blocks is then separated from the experimental error, yielding more
precise comparisons of the treatments.

Each sentence is identified by its source project and its position
within that project. It is possible for the same text to appear in more
than one project (e.g., a common UI string like "OK" or "Cancel"), but
such occurrences are treated as distinct objects because they belong to
different source projects and their translations exist in different
multilingual corpora with potentially different reference translations.
The unit of observation is therefore the combination of source project
and sentence, not the sentence text alone.

This creates a two-level grouping structure among the objects:

  - Upper level: source project (the software program).
  - Lower level: sentence within source project (the individual UI
    string in the context of its program).

Both levels are modeled as random effects. To explain what this means:
in a linear model, the intercept is the baseline value of the dependent
variable — the expected score before any treatment effect is applied. A
random intercept allows this baseline to vary across groups. In this
experiment, a random intercept for source project means that each
software program gets its own baseline translation difficulty: some
programs (with simpler, more common vocabulary) have a higher baseline
score, while others (with specialized or complex terminology) have a
lower one. Similarly, a random intercept for sentence within source
project means that each individual sentence gets its own baseline
difficulty above or below its program's average.

Concretely, the two random intercepts capture two distinct sources of
nuisance variation:

  - The source-project-level random intercept captures the fact that
    all sentences from the same program share a common baseline
    difficulty. Without this term, the model would treat sentences from
    the same program as independent, underestimating standard errors
    and producing overconfident results — particularly for programs
    contributing many sentences.

  - The sentence-within-source-project random intercept captures the
    fact that individual sentences within the same program still differ
    from one another, and that each sentence is measured 29 times (once
    per treatment). This accounts for the repeated-measures structure
    of the design.

Source project is modeled as a random (rather than fixed) effect
because the goal is to generalize beyond these specific 17 programs to
UI string translation in general. The 17 programs are treated as a
sample from a larger population of possible software programs. The
number of sentences per source project is unequal — some contribute as
few as 7 sentences, others as many as 614. Random effects handle this
gracefully through partial pooling: estimates for source projects with
few sentences are shrunk toward the overall average, borrowing strength
from the larger ones.


6. Tests
--------

A test (or trial) is one combination of treatment and object — that is,
one specific treatment applied to one specific sentence in the context
of its source project. The experiment consists of 29 treatments applied
to each of the approximately 3,900 objects, yielding approximately
112,000 tests in total. Each test produces one BLEU score. The number of
tests determines the experimental error, which in turn determines how
much confidence can be placed in the results (Wohlin et al., 2012).


7. Design Classification
------------------------

The experiment follows a nested within-subjects design with blocking:

  - Nested: context configuration is nested within treatment type.
  - Within-subjects: every object is observed under every treatment.
  - Blocked: objects are grouped by source project (software program),
    and this grouping introduces correlated variation that the model
    accounts for.


8. Fixed vs. Random Effects
----------------------------

Fixed effects are what the experiment seeks to study and draw specific
conclusions about. Treatment type and context configuration are fixed
because the researcher deliberately chose these specific 3 treatment
types and these specific 7 context languages, and wishes to make
claims about them specifically.

Random effects are what the experiment seeks to control for and
generalize beyond. Source project and sentence within source project are
random because the researcher does not care about aspell vs. nano
specifically — they are a sample from a larger population of software
programs. The approximately 3,900 sentences are a sample of possible UI
strings. Modeling them as random allows the conclusions to generalize to
new programs and new sentences not included in the experiment.


9. Statistical Model
---------------------

The data are analyzed using a linear mixed-effects model (LMM):

  score ~ treatment_type + treatment_type:context_config
          + (1 | source_project) + (1 | source_project:sentence_id)

Where:

  - score is the dependent variable (sentence-level BLEU).
  - treatment_type is the main fixed factor (3 levels: direct,
    single-context, double-context).
  - treatment_type:context_config is the nested fixed factor (context
    configuration within treatment type, 29 levels total).
  - (1 | source_project) is the random intercept for source project,
    capturing program-level baseline difficulty.
  - (1 | source_project:sentence_id) is the random intercept for
    sentence nested within source project, capturing sentence-level
    baseline difficulty and accounting for the repeated-measures
    structure.

Estimation uses restricted maximum likelihood (REML) with Satterthwaite
degrees of freedom. Estimated marginal means with equal weights across
context configurations within each treatment type are used for
treatment-type comparisons, ensuring that each context configuration
contributes equally regardless of the unequal number of sub-conditions
per type.

Because sentence-level BLEU scores are zero-inflated and right-skewed,
the normality assumption of the LMM may be violated. The analysis
includes residual diagnostic plots to assess the severity of this
violation. If the violation is substantial, the primary inferential
results are drawn from a non-parametric paired bootstrap resampling
procedure (Koehn, 2004), which makes no distributional assumptions and
is standard practice in the machine translation community. The LMM
results are reported alongside as a complementary analysis.


9.1 Paired Bootstrap Resampling
................................

The bootstrap (Efron and Tibshirani, 1993) is a resampling method for
estimating the sampling distribution of a statistic without relying on
parametric assumptions about the data's distribution.

The core idea is straightforward: the observed sample is treated as
the best available approximation of the population. By drawing
repeated samples from the observed data itself — with replacement —
the procedure simulates what would happen if the experiment were
repeated many times. Each resampled dataset produces a value of the
statistic of interest (here, the difference in mean BLEU between two
treatment types), and the collection of these values across many
resamples approximates the sampling distribution of that statistic.

In this experiment the resampling unit is the sentence, not the
individual score. Each sentence carries all 29 of its scores (one per
condition) as a single bundle. When a sentence is selected during
resampling, all 29 of its scores are included together. This preserves
the within-subjects pairing: every bootstrap sample compares the same
sentences across treatments, exactly as the original experiment does.
This is why the procedure is called a "paired" bootstrap — the pairing
of scores within sentences is maintained throughout.

The procedure works as follows:

  1. Reshape the data to wide format: one row per sentence, one column
     per condition (29 columns total), producing a matrix of 3,896 rows
     by 29 columns.

  2. Repeat the following 10,000 times:
     a. Draw a sample of 3,896 rows from the matrix with replacement.
        Some sentences will appear more than once, others not at all.
        This is intentional: it is what introduces sampling variability
        and allows the procedure to estimate uncertainty.
     b. For the resampled matrix, compute the mean score for each
        treatment type. Within single-context and double-context
        treatments, each context configuration receives equal weight:
        per-sentence row means are computed first (averaging across
        the 7 or 21 context configurations for that sentence), then
        the grand mean is taken across sentences. This matches the
        equal-weight approach used in the LMM analysis.
     c. Compute the three pairwise differences between treatment-type
        means (direct vs. single-context, direct vs. double-context,
        single-context vs. double-context) and store them.

  3. After all 10,000 iterations, the 2.5th and 97.5th percentiles of
     each stored difference give the 95% confidence interval. If this
     interval excludes zero, the difference is statistically significant
     at the 5% level.

The bootstrap confidence interval is analogous to the confidence
interval from the LMM, but makes no assumptions about normality,
homoscedasticity, or the shape of the error distribution. When both
methods agree — as they do in this analysis — confidence in the
findings is strengthened, because the conclusions do not depend on
any single set of statistical assumptions.


10. Research Questions
----------------------

The experiment addresses three research questions:

  Q1. Do the three treatment types (direct, single-context, double-
      context) differ in translation quality?

  Q2. Within single-context translation, do the seven context
      languages yield different translation quality?

  Q3. Within double-context translation, do the 21 context-language
      pairs yield different translation quality?

All three questions are addressed within the single model through
planned contrasts and estimated marginal means, using Bonferroni
adjustment for the treatment-type comparisons (Q1) and Tukey adjustment
for the within-type comparisons (Q2 and Q3).


11. Summary Table
-----------------

  Aspect                      Value
  --------------------------  -------------------------------------------
  Design                      Nested within-subjects with blocking
  Dependent variable          Translation quality (sentence-level BLEU)
  Independent variables       Treatment type and context configuration
                                (factors); source project (blocking
                                variable); all others held constant
  Fixed factor A              Treatment type (3 levels: direct,
                                single-context, double-context)
  Fixed factor B(A)           Context configuration, nested in A
                                (1 + 7 + 21 = 29 levels total)
  Treatments                  29 (one per combination of factors)
  Objects                     Sentences (approx. 3,900 UI strings)
  Blocking factor             Source project — software program
                                (17 levels, unequal sizes)
  Random effects              Source project; sentence nested within
                                source project
  Tests                       Approx. 112,000
                                (29 treatments x approx. 3,900 objects)
  Source language              English (fixed, held constant)
  Target language              Brazilian Portuguese (fixed, held
                                constant)


12. References
--------------

Efron, B. and Tibshirani, R. J. (1993). An Introduction to the
Bootstrap. Chapman and Hall/CRC.

Koehn, P. (2004). Statistical Significance Tests for Machine
Translation Evaluation. In Proceedings of the 2004 Conference on
Empirical Methods in Natural Language Processing, pages 388-395.
Association for Computational Linguistics.

Montgomery, D. C. (2019). Design and Analysis of Experiments (10th
ed.). Wiley.

Shahnazaryan, L., Simianer, P., and Wuebker, J. (2025). Contextual
Cues in Machine Translation: Investigating the Potential of Multi-
Source Input Strategies in LLMs and NMT Systems. In Proceedings of the
15th International Conference on Recent Advances in Natural Language
Processing, pages 1099-1108, Varna, Bulgaria. INCOMA Ltd.

Wohlin, C., Runeson, P., Höst, M., Ohlsson, M. C., Regnell, B., and
Wesslén, A. (2012). Experimentation in Software Engineering. Springer.

Xu, W., Yin, Y., Ma, S., Zhang, D., and Huang, H. (2021). Improving
Multilingual Neural Machine Translation with Auxiliary Source
Languages. In Findings of the Association for Computational
Linguistics: EMNLP 2021, pages 3029-3041. Association for
Computational Linguistics.

Zoph, B. and Knight, K. (2016). Multi-Source Neural Translation. In
Proceedings of the 2016 Conference of the North American Chapter of the
Association for Computational Linguistics: Human Language Technologies,
pages 30-34. Association for Computational Linguistics.

---
Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>

