# Batch results

Each completed batch normally contains:

- `calls.csv`: one row per listing/API attempt, including JSON and schema
  validity.
- `promises.csv`: model-extracted promise rows with evidence validation fields.
- `raw_qwen3.5-4b.json`: raw model responses.
- `selected_inputs.json`: exact listing descriptions and selected reviews sent
  to the model.
- `run_config.json`: sampling and model settings.
- `summary.json`: batch-level quality and label summary.

The folders use different names because they represent separate fixed
samples. Keep them separate unless the analysis explicitly combines the
samples after checking overlap and configuration.
