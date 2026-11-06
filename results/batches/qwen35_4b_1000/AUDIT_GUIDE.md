# Human audit guide: 100 listings

The sample is a deterministic, proportionally stratified random sample of the completed 1,000-listing set (seed 20261101). The strata classify a listing by its strongest negative/mixed/insufficient label, so the sample preserves the dataset's label-pattern mix. This is for checking model quality, not for producing a second model answer.

For each listing, read the description and all five selected reviews, then compare them with `promises_json`. Fill the three audit columns:

- `audit_promise_coverage`: `complete`, `partial`, or `missed` — did the extracted promises cover the explicit, checkable claims that are supported by these reviews?
- `audit_label_agreement`: `all_agree`, `some_disagree`, or `all_disagree` — do the labels fit the supplied review evidence? Treat silence as insufficient evidence, not a failure.
- `audit_evidence_support`: `all_supported`, `some_unsupported`, or `all_unsupported` — do the cited review quotes actually support or contradict the corresponding promise, and are the cited review IDs correct?
- `audit_notes`: record the promise/quote and a brief reason for any disagreement.

Do not use listing descriptions as review evidence. Rate only claims reasonably checked using the five supplied reviews. Keep `review_scores_rating` separate from audit judgments; it is an existing platform score, not ground truth for a specific promise. After the audit, report coverage, label agreement, and evidence support separately, with the denominator and disagreement examples.
