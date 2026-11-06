# Airbnb Promise Gap: analysis and project closeout

## Dataset design

- Target: a reproducible sample of 1,000 eligible listings with descriptions and guest reviews.
- Per listing, Python retrieves up to five relevant reviews using the current hybrid topic/description-overlap ranker.
- Qwen 3.5 4B returns up to four distinct promises with a label and review IDs. Compact mode omits free-text reasoning to preserve the measured speed.
- Preserve raw model responses, exact selected inputs, run settings, and one result checkpoint per completed listing.

## Quality checks before interpretation

1. Confirm the number of attempted, completed, and failed listings; report schema-valid responses and elapsed time.
2. Resolve each model-provided quote against the selected review text. Exact matches stay unchanged. Case/punctuation-only matches are replaced with the exact source substring. Quotes copied from another selected review can have their source ID repaired from that exact match. Keep the raw quote and raw model ID alongside any repaired value.
3. Leave unmatched quotes flagged as unverified; exclude them from evidence-backed findings. Never use listing description text as guest-review evidence.
4. Manually audit a stratified sample of 100 listings. Check whether the model found the important explicit promises, selected the right label, and cited evidence that actually supports or contradicts the promise. Report agreement and error examples; do not treat model output as ground truth.

## Main analysis

- Report positive, negative, mixed, and insufficient-evidence labels separately.
- Show both promise-level counts and listing-level rates. A listing that produces more extracted promises should not automatically carry more weight in listing-level comparisons.
- Treat negative as a supported promise gap, mixed as partial or inconsistent evidence, and insufficient evidence as unknown. Do not count missing evidence as a failed promise.
- Summarize verified promise gaps by promise category, property type, and neighborhood only where group sizes are adequate. These are descriptive associations, not causal effects.
- Derive promise categories with a transparent Python keyword taxonomy, then manually review unmatched/ambiguous claims. Do not add another LLM call to the fast path just for categorization.
- Include confidence intervals for headline proportions, plus the manually audited agreement/error rate.

## Proposed closeout gates

- At least 98% of selected listings have a completed, schema-valid result after retries.
- Every evidence quote retained in the final analytical dataset maps to an exact substring of its cited review; unverified quotes remain flagged and out of evidence-backed counts.
- Manual audit reports claim coverage, label agreement, and evidence support separately. If the audit shows a systematic error, revise the method and rerun before making substantive claims.
- Freeze the final CSV, the audit sample and decisions, the run configuration, a data dictionary, and a short report with figures, limitations, and reproduction instructions.

## Interpretation limits

The fast mode deliberately samples only five reviews and returns at most four promises per listing. The final findings therefore describe the strongest promises and evidence found under this retrieval rule; they do not establish that every promise or every guest experience was captured. A sample of 1,000 listings improves coverage, but validity still depends on the sampling frame, evidence checks, and human audit.

## Runtime and completed run

The ten-listing fast pilot averaged 12.4 seconds per listing. The completed fixed sample contains 1,000 unique listings, five retrieved reviews each, and 3,995 extracted promise rows. Initial calls were schema-valid for 999/1,000 listings; one response was truncated at the 900-token ceiling. A targeted retry used the exact same five reviews and a 1,600-token ceiling, yielding a final analytical dataset with 1,000/1,000 valid records. The failed initial response remains preserved in its original batch output; the corrected merged files substitute the valid retry.

Cumulative model time including the retry was 10,393 seconds (2.89 hours; 10.39 seconds per unique listing). Two of 1,001 attempts exceeded 20 seconds: the valid-response maximum was 27.62 seconds, and the truncated attempt took 30.64 seconds. Thus a hard 20-second ceiling is not supported by the observed run. The corrected outputs are `results/batches/qwen35_4b_1000/calls_all_1000_corrected.csv`, `promises_all_1000_corrected.csv`, and `summary_first_1000_corrected.json`.

The 3,995 promise labels are 3,163 positive, 520 negative, 291 mixed, and 21 insufficient-evidence. Across 4,283 evidence quotes, 89.4% matched a selected review; 77.9% were exact as emitted and 11.4% were mapped after normalization/repair. Promise-row ID validity is 98.3%, citation alignment 85.9%, and combined evidence validation 88.7%. These rates are quality diagnostics, not human-verified accuracy.

The original Part 1 was retained as a formatting baseline and excluded from the final aggregation; its exact 50 inputs were rerun in `part_001_schema_v2`. All final outputs use the corrected strict-schema run. The deterministic sample and per-part checkpoints are preserved under `results/batches/qwen35_4b_1000`.

## Human audit and ratings analysis

The deterministic, proportionally stratified 100-listing audit packet is prepared in `results/batches/qwen35_4b_1000/audit_sample_100.csv`, with instructions in `AUDIT_GUIDE.md` and sample counts in `audit_sample_100_manifest.json`. Score promise coverage, label agreement, and evidence support separately; retain disagreements and examples. The source platform rating is available for all 1,000 listings. `listing_level_analysis_1000.csv` keeps one row per listing so listings with more extracted promises do not receive extra weight.

An exploratory, not yet human-validated association is recorded in `rating_association_exploratory.json`: Spearman rho between platform rating and the listing-level share of negative promise labels is −0.225 (n=1,000); average ratings are 4.674 for listings with any negative label and 4.760 for those without. These model-based comparisons are descriptive only. Complete the audit before treating them as substantive findings; then report agreement/error rates, confidence intervals, subgroup sizes, missingness, and limitations.
