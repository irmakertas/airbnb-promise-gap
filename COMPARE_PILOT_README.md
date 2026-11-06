# Airbnb promise gap: batch runs

## Current fast-mode settings

The tested fast configuration uses Qwen 3.5 4B with thinking disabled, Python review retrieval, five reviews per listing, up to four promises, concise evidence quotes, no free-text reasoning, and a 900-token output ceiling. Ten calls averaged 12.4 seconds; speed can vary by listing and system load.

## Run the 1,000-listing sample in batches

From PowerShell, with Qwen 3.5 4B loaded in Bionic/LM Studio:

Each part uses the same fixed sample seed and takes a separate, non-overlapping slice of the same 1,000-listing population. Start with part 1:

```powershell
python .\compare_pilot.py --only-model qwen3.5-4b --batch-mode --listings 50 --total-listings 1000 --batch-index 0 --max-reviews 5 --max-promises 4 --max-tokens 900 --fast-mode --output-dir results\batches\qwen35_4b_1000\part_001
```

Turn **Enable Thinking** off in the model settings. The script also requests
thinking off, but the model setting was needed for this setup.

Listings 1–100 were initially run as two 50-listing parts. Later 100-listing parts covered listings 101–1,000 using indexes 1–9. All ten slices are complete; the canonical merged outputs are `calls_all_1000_corrected.csv`, `promises_all_1000_corrected.csv`, and `summary_first_1000_corrected.json` in the batch folder. To rerun an individual slice, use its original index and a new output folder. The next command shown is the historical command for listings 801–900:

```powershell
python .\compare_pilot.py --only-model qwen3.5-4b --batch-mode --listings 100 --total-listings 1000 --batch-index 8 --max-reviews 5 --max-promises 4 --max-tokens 900 --fast-mode --output-dir results\batches\qwen35_4b_1000\part_017_018
```

Do not change the batch size or seed for later indexes without recalculating offsets. Each listing is checkpointed; if interrupted, rerun the exact same command and completed listings are skipped. `run_config.json` prevents resuming with different settings or a different selected sample. The latest 100-listing batches averaged about 10.56 seconds per listing (one call exceeded 20 seconds in the first such batch), or around 17.6 minutes of model time per 100. Actual speed varies.

## Continue after the completed 1,000 listings

The original 1,000-listing sample cannot be extended safely by changing only
`--total-listings`: that would create a different random population. Instead,
pass the completed calls CSV so those IDs are excluded, then create a new
fixed population (for example, 3,000 listings) and process it in 100-listing
batches:

```powershell
python .\compare_pilot.py --only-model qwen3.5-4b --batch-mode --listings 100 --total-listings 3000 --batch-index 0 --exclude-listings-file results\batches\qwen35_4b_1000\calls_all_1000_corrected.csv --max-reviews 5 --max-promises 4 --max-tokens 900 --fast-mode --output-dir results\batches\qwen35_4b_next\part_001
```

Run the same command for indexes `0` through `29`, changing only
`--batch-index` and `--output-dir`. Keep the seed at its default `42` and use
the same exclude file for every batch. The exclude CSV must contain a
`listing_id` or `id` column.

The runner displays a `tqdm` progress bar for each batch, including completed
listings skipped from an existing checkpoint. The bar shows the current
listing count and the elapsed time of the latest model call.

To automate 1,000 additional listings (ten 100-listing batches), use the
PowerShell runner after the currently running batch has finished:

```powershell
.\run_continuation_batches.ps1
```

It processes indexes `0` through `9` in order and stores them under
`results\batches\qwen35_4b_next\part_001` through `part_010`. If a batch
fails, fix the cause and rerun with its index, for example:

```powershell
.\run_continuation_batches.ps1 -StartBatch 4
```

Completed batches are checkpointed by `compare_pilot.py`, so rerunning from
index `0` is also safe when the same settings and output folders are kept.
Individual model responses are first appended to a low-memory `.jsonl`
checkpoint and consolidated into the regular `.json` file after the batch
finishes. If a process stops during a batch, the `.jsonl` checkpoint is
loaded automatically on the next run.

The runner now sends a strict JSON schema to LM Studio, in addition to the prompt, so it can constrain the response shape and labels. LM Studio accepted the schema with Qwen3.5 4B in a single-listing API check. JSON arrays returned without the required outer object are normalized to the expected `promises` object before validation; malformed JSON remains invalid and is never guessed or silently repaired.

### First part status (2026-10-31)

Part 1 (`batch-index 0`) completed all 50 listings in 593.8 seconds of model time (11.88 seconds average; 28.77 seconds maximum). It was run before schema-constrained output was added: 46/50 responses parsed as JSON, while only 42/50 followed the expected object schema. The four valid-JSON root arrays and four malformed responses remain flagged in this original run; no contents were guessed or repaired. The 42 schema-valid responses yielded 177 promise rows. Across those rows, 88.1% of evidence quotes matched a selected source review, 96.0% of cited IDs were valid, and 81.9% of quote source IDs aligned with the IDs supplied by the model.

The first 50 listings were rerun in `part_001_schema_v2` with strict JSON-schema output. Its selected listing and review inputs are byte-identical to the original Part 1. This rerun returned 50/50 schema-valid responses and is the authoritative Part 1 for analysis; the earlier `part_001` run is preserved only as a formatting baseline.

Part 2 (`batch-index 1`) used LM Studio's schema-constrained response format and completed 50/50 schema-valid responses. Average latency was 10.33 seconds (maximum 13.75 seconds; no calls over 20 seconds); total model time was 516.3 seconds. It produced 197 promise rows: 151 positive, 30 negative, 14 mixed, and 2 insufficient-evidence. Quote source-match rate was 88.7%, cited-ID validity 98.5%, citation alignment 87.3%, and combined evidence validation 87.8%. The first two parts have no overlapping listings. These preliminary figures do not replace the human audit. Part 1's original failures remain flagged; before final aggregation, either rerun it under the corrected format or explicitly report the lower completeness.

Part 3/4 (`batch-index 1`, batch size 100) used the same strict schema on listings 101–200. It completed 100/100 schema-valid responses in 1,056.1 seconds (10.56 seconds average; 27.62 seconds maximum; one call over 20 seconds). It yielded 398 promise rows: 307 positive, 63 negative, 27 mixed, and 1 insufficient-evidence. Quote source-match rate was 89.3%, cited-ID validity 99.0%, citation alignment 86.1%, and combined evidence validation 88.7%. No listings overlapped the first 100. Detailed outputs are under `results/batches/qwen35_4b_1000/part_003_004`.

Part 5/6 (`batch-index 2`, batch size 100) covered listings 201–300. It completed 100/100 schema-valid responses in 1,055.8 seconds (10.56 seconds average; 15.82 seconds maximum; no calls over 20 seconds). It yielded 400 promise rows: 312 positive, 52 negative, 34 mixed, and 2 insufficient-evidence. Quote source-match rate was 88.5%, cited-ID validity 98.3%, citation alignment 85.3%, and combined evidence validation 88.0%. No listings overlapped the first 200. Detailed outputs are under `results/batches/qwen35_4b_1000/part_005_006`.

Part 7/8 (`batch-index 3`, batch size 100) covered listings 301–400. It completed 100/100 schema-valid responses in 1,025.1 seconds (10.25 seconds average; 14.12 seconds maximum; no calls over 20 seconds). It yielded 400 promise rows: 318 positive, 53 negative, 28 mixed, and 1 insufficient-evidence. Quote source-match rate was 91.0%, cited-ID validity 98.5%, citation alignment 87.5%, and combined evidence validation 90.5%. No listings overlapped the first 300. Detailed outputs are under `results/batches/qwen35_4b_1000/part_007_008`.

The corrected first 400 have 400/400 schema-valid responses and 1,595 promise rows. Aggregate source-match rate is 89.4%, cited-ID validity 98.4%, citation alignment 86.5%, and combined evidence validation 88.8%. These are preliminary model outputs and still require the planned human audit. The cumulative file is `results/batches/qwen35_4b_1000/summary_first_400_corrected.json`.

Part 9/10 (`batch-index 4`, batch size 100) covered listings 401–500. It completed 100/100 schema-valid responses in 1,065.6 seconds (10.66 seconds average; 18.03 seconds maximum; no calls over 20 seconds). It yielded 400 promise rows: 315 positive, 49 negative, 35 mixed, and 1 insufficient-evidence. Quote source-match rate was 92.2%, cited-ID validity 97.8%, citation alignment 89.0%, and combined evidence validation 91.8%. No listings overlapped the first 400. Detailed outputs are under `results/batches/qwen35_4b_1000/part_009_010`.

Part 11/12 (`batch-index 5`, batch size 100) covered listings 501–600. It completed 100/100 schema-valid responses in 1,038.7 seconds (10.39 seconds average; 14.10 seconds maximum; no calls over 20 seconds). It yielded 400 promise rows: 322 positive, 46 negative, 30 mixed, and 2 insufficient-evidence. Quote source-match rate was 92.0%, cited-ID validity 99.5%, citation alignment 90.2%, and combined evidence validation 91.0%. No listings overlapped the first 500. Detailed outputs are under `results/batches/qwen35_4b_1000/part_011_012`.

Part 13/14 (`batch-index 6`, batch size 100) covered listings 601–700. It completed 100/100 schema-valid responses in 1,019.3 seconds (10.19 seconds average; 13.93 seconds maximum; no calls over 20 seconds). It yielded 400 promise rows: 323 positive, 50 negative, 25 mixed, and 2 insufficient-evidence. Quote source-match rate was 88.6%, cited-ID validity 97.3%, citation alignment 84.9%, and combined evidence validation 87.8%. No listings overlapped the first 600. Detailed outputs are under `results/batches/qwen35_4b_1000/part_013_014`.

Part 15/16 (`batch-index 7`, batch size 100) covered listings 701–800. It completed 100/100 schema-valid responses in 1,035.7 seconds (10.36 seconds average; 16.91 seconds maximum; no calls over 20 seconds). It yielded 400 promise rows: 322 positive, 46 negative, 32 mixed, and no insufficient-evidence labels. Quote source-match rate was 90.8%, cited-ID validity 98.5%, citation alignment 85.3%, and combined evidence validation 90.3%. No listings overlapped the first 700. Detailed outputs are under `results/batches/qwen35_4b_1000/part_015_016`.

The corrected first 800 have 800/800 schema-valid responses and 3,195 promise rows. Aggregate source-match rate is 90.2%, cited-ID validity 98.3%, citation alignment 86.9%, and combined evidence validation 89.5%. These are preliminary model outputs and still require the planned human audit. The cumulative file is `results/batches/qwen35_4b_1000/summary_first_800_corrected.json`.


### Completed 1,000-listing run (2026-11-01)

The fixed sample contains 1,000 unique listings and five Python-retrieved reviews per listing. The ten canonical slices are `part_001_schema_v2`, `part_002`, and `part_003_004` through `part_019_020`. Initial runs produced 999/1,000 schema-valid records (99.9%). Listing `1402838197531909461` was cut off at the 900-token output ceiling (`finish_reason=length`); it was rerun against the same five selected reviews with a 1,600-token ceiling and returned valid JSON/schema. The final merged analytical files therefore contain 1,000/1,000 valid listing records. The original failed attempt remains in its part folder and is counted in the attempt log; the separate successful retry is under `retry2_listing_1402838197531909461`.

The merged result contains 3,995 promise rows: 3,163 positive, 520 negative, 291 mixed, and 21 insufficient-evidence. Across 4,283 evidence quotes, 89.4% matched a selected source review; 77.9% were exact as emitted and 11.4% were matched after allowed normalization/repair. At promise-row level, cited-ID validity was 98.3%, citation alignment 85.9%, and combined evidence validation 88.7%. The output quotes and IDs retain raw and validated fields for inspection.

The 1,000 initial calls plus one targeted retry used 10,393 seconds of cumulative model time (2.89 hours; 10.39 seconds per unique listing). Two attempts exceeded 20 seconds: one valid response at 27.62 seconds and the truncated response at 30.64 seconds. This confirms that a sub-20-second ceiling cannot be guaranteed. All counts and rates are recorded in `summary_first_1000_corrected.json`.

Exploratory rating check: all 1,000 sampled listings have a platform rating. The Spearman correlation between rating and each listing’s share of negative promise labels is −0.225; listings with at least one negative label average 4.674 versus 4.760 for listings without one. This is only a preliminary association in un-audited model labels, with no causal interpretation. See `rating_association_exploratory.json`.

These are model-generated descriptive outputs, not audited findings. A deterministic, proportionally stratified 100-listing audit packet is ready in `audit_sample_100.csv`; use `AUDIT_GUIDE.md` to complete it. The listing-level merged table is `listing_level_analysis_1000.csv`. Before treating rating associations as findings, complete the human audit and report agreement/error rates.

## Output files

- `selected_inputs.json`: exact listing descriptions and retrieved review IDs/text.
- `run_config.json`: model, sample, and prompt settings required for a safe resume.
- `calls.csv`: latency, JSON/schema validity, errors, finish reason, and token counts.
- `promises.csv`: claims, labels, raw model quotes/IDs, canonical source quotes, and validation flags.
- `raw_qwen3.5-4b.json`: unmodified model responses, checkpointed after each listing.
- `summary.json`: timing, quote/ID validation, label counts, and run settings.
- `calls_all_1000_corrected.csv` and `promises_all_1000_corrected.csv`: merged, corrected one-row-per-listing calls and promise-level outputs.
- `listing_level_analysis_1000.csv`: promise label counts/shares joined to platform rating and listing metadata; use as an exploratory analysis input.
- `audit_sample_100.csv`, `audit_sample_100_manifest.json`, and `AUDIT_GUIDE.md`: deterministic 100-listing manual audit packet.

## Evidence validation and analysis

The validator keeps the raw model quote and ID for audit. Exact review substrings are retained; case/punctuation-only differences are mapped back to the exact source substring. If a quote exactly matches a different selected review than the model cited, the source ID is repaired and the model’s original ID is kept separately. Quotes that cannot be matched remain unverified and must be excluded from evidence-backed findings. Listing-description text is never accepted as review evidence.

For the full quality gates, aggregation plan, human audit, and closeout deliverables, see `PROJECT_ANALYSIS_PLAN.md`.
