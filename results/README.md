# Results layout

The result folders contain reproducible checkpoints and preserved model
outputs. Do not delete `calls.csv`, `promises.csv`, `raw_qwen3.5-4b.json`,
`selected_inputs.json`, or `summary.json` from completed batches.

- `batches/`: full listing-level LLM runs.
- `batches/qwen35_4b_1000/`: canonical corrected first 1,000-listing run,
  including the human-audit packet and listing-level exploratory analysis.
- `batches/qwen35_4b_next/`: the next 1,000 listings, processed in ten
  100-listing batches.
- `batches/qwen35_4b_1000_sample_02/`: an additional preserved 1,000-listing
  sample and its batch outputs.

For statistical analysis, prefer the corrected merged files in
`qwen35_4b_1000/` and concatenate the batch-level `promises.csv` and
`calls.csv` files from the other preserved runs only when their sample and
configuration are explicitly part of the analysis.
