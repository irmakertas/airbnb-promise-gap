from __future__ import annotations

import argparse
import json
import re
import statistics
import time
from collections import Counter
from pathlib import Path

import pandas as pd
import requests
from tqdm import tqdm


API_BASE = "http://localhost:1235/v1"
PROJECT_DIR = Path(__file__).resolve().parent
LABELS = {"positive", "negative", "mixed", "insufficient_evidence"}
PROMISE_RESPONSE_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "airbnb_promise_analysis",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "promises": {
                    "type": "array",
                    "maxItems": 4,
                    "items": {
                        "type": "object",
                        "properties": {
                            "promise": {"type": "string"},
                            "label": {"type": "string", "enum": ["positive", "negative", "mixed", "insufficient_evidence"]},
                            "evidence_for": {"type": "array", "items": {"type": "string"}, "maxItems": 1},
                            "evidence_against": {"type": "array", "items": {"type": "string"}, "maxItems": 1},
                            "evidence_review_ids": {"type": "array", "items": {"type": "string"}, "maxItems": 2},
                        },
                        "required": ["promise", "label", "evidence_for", "evidence_against", "evidence_review_ids"],
                        "additionalProperties": False,
                    },
                },
            },
            "required": ["promises"],
            "additionalProperties": False,
        },
    },
}
RETRIEVAL_TERMS = {
    "cleanliness": ["clean", "dirty", "dust", "smell", "stain", "cleaning", "temiz", "kirli"],
    "comfort": ["comfortable", "comfort", "bed", "mattress", "noise", "cold", "hot", "comfortable", "rahat", "yatak"],
    "accuracy": ["exactly", "accurate", "photo", "picture", "described", "smaller", "larger", "fotoğraf", "aynı"],
    "location": ["location", "located", "walk", "distance", "near", "neighborhood", "metro", "station", "konum", "yakın"],
    "amenities": ["wifi", "wi-fi", "internet", "shower", "water", "kitchen", "air conditioning", "ac ", "heating", "ısıtma", "duş"],
    "host": ["host", "helpful", "responsive", "communication", "check-in", "check in", "welcome", "ev sahibi", "iletişim"],
    "value": ["value", "price", "worth", "expensive", "cheap", "cost", "fiyat"],
    "access": ["stairs", "staircase", "elevator", "lift", "parking", "accessible", "merdiven", "otopark"],
}


def clean_text(value) -> str:
    if pd.isna(value):
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def load_checkpoint_results(raw_path: Path) -> list[dict]:
    results_by_listing = {}
    jsonl_path = raw_path.with_suffix(".jsonl")
    if raw_path.exists() and raw_path.stat().st_size:
        try:
            raw_items = json.loads(raw_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            if not jsonl_path.exists():
                raise SystemExit(f"Checkpoint JSON is invalid: {raw_path}: {error}") from error
        else:
            for item in raw_items:
                results_by_listing[item["listing_id"]] = item
    if jsonl_path.exists():
        with jsonl_path.open(encoding="utf-8") as checkpoint:
            for line in checkpoint:
                if line.strip():
                    item = json.loads(line)
                    results_by_listing[item["listing_id"]] = item
    return list(results_by_listing.values())


def append_checkpoint_result(raw_path: Path, result: dict) -> None:
    jsonl_path = raw_path.with_suffix(".jsonl")
    with jsonl_path.open("a", encoding="utf-8") as checkpoint:
        checkpoint.write(json.dumps(result, ensure_ascii=False, separators=(",", ":")) + "\n")


def retrieval_score(text: str, description: str) -> tuple[int, int]:
    low = text.casefold()
    hit_count = sum(any(term in low for term in terms) for terms in RETRIEVAL_TERMS.values())
    term_count = sum(low.count(term) for terms in RETRIEVAL_TERMS.values() for term in terms)
    desc_terms = {w for w in re.findall(r"[a-zA-ZÀ-ÿ]{5,}", description.casefold())}
    review_terms = set(re.findall(r"[a-zA-ZÀ-ÿ]{5,}", low))
    return hit_count, term_count + min(4, len(desc_terms & review_terms))


def select_sample(listings: pd.DataFrame, reviews: pd.DataFrame, n: int, seed: int,
                  max_reviews: int) -> list[dict]:
    listings = listings.copy()
    listings["id"] = listings["id"].astype(str)
    reviews = reviews.copy()
    reviews["listing_id"] = reviews["listing_id"].astype(str)
    reviews["id"] = reviews["id"].astype(str)
    reviews["comments"] = reviews["comments"].map(clean_text)
    reviews = reviews[reviews["comments"].ne("")]
    eligible = listings[listings["id"].isin(reviews["listing_id"].unique())]
    sample = eligible.sample(n=min(n, len(eligible)), random_state=seed).sort_values("id")
    cases = []
    for row in sample.itertuples(index=False):
        desc = clean_text(getattr(row, "description", ""))
        if not desc:
            continue
        subset = reviews[reviews["listing_id"].eq(str(row.id))].copy()
        subset["_rank"] = subset["comments"].map(lambda x: retrieval_score(x, desc))
        subset = subset.sort_values(["_rank", "date", "id"], ascending=[False, False, True], kind="stable")
        chosen = subset.head(max_reviews)
        if chosen.empty:
            continue
        cases.append({
            "listing_id": str(row.id),
            "description": desc,
            "reviews": [{"id": str(r.id), "text": r.comments} for r in chosen.itertuples(index=False)],
        })
    return cases


def select_sample_streamed(data_dir: Path, batch_size: int, seed: int, max_reviews: int,
                           total_listings: int | None = None, batch_index: int = 0,
                           excluded_listing_ids: set[str] | None = None) -> list[dict]:
    listings = pd.read_csv(data_dir / "eligible_listings.csv", usecols=["id", "description"], low_memory=False)
    listings["id"] = listings["id"].astype(str)
    excluded_listing_ids = excluded_listing_ids or set()
    listings = listings[~listings["id"].isin(excluded_listing_ids)]
    total_listings = total_listings or batch_size
    pool_size = min(
        len(listings),
        max(total_listings + 100, total_listings * 2),
    )
    pool = listings.sample(n=pool_size, random_state=seed)
    candidate_ids = set(pool["id"])
    selected_chunks = []
    for chunk in pd.read_csv(
        data_dir / "eligible_reviews.csv",
        usecols=["listing_id", "id", "date", "comments"],
        dtype={"listing_id": str, "id": str},
        chunksize=50000,
        low_memory=False,
    ):
        chunk["comments"] = chunk["comments"].map(clean_text)
        keep = chunk["listing_id"].isin(candidate_ids) & chunk["comments"].ne("")
        if keep.any():
            selected_chunks.append(chunk.loc[keep])
    if not selected_chunks:
        return []
    reviews = pd.concat(selected_chunks, ignore_index=True)
    with_reviews = set(reviews["listing_id"].unique())
    population = pool[pool["id"].isin(with_reviews)].head(total_listings)
    start = batch_index * batch_size
    end = min(start + batch_size, total_listings)
    sample = population.iloc[start:end]
    if sample.empty:
        return []
    batch_ids = set(sample["id"])
    batch_reviews = reviews[reviews["listing_id"].isin(batch_ids)]
    return select_sample(sample, batch_reviews, len(sample), seed, max_reviews)


def make_prompt(case: dict, max_promises: int = 12, fast_mode: bool = False) -> str:
    review_text = "\n".join(f'Review ID: {r["id"]} | Review: {r["text"]}' for r in case["reviews"])
    if fast_mode:
        return f'''Listing description:\n{case["description"]}\n\nGuest reviews:\n{review_text}\n\nReturn ONLY JSON using this schema:\n{{"promises":[{{"promise":"short claim","label":"positive|negative|mixed|insufficient_evidence","evidence_for":["exact quote"],"evidence_against":["exact quote"],"evidence_review_ids":["ID"]}}]}}\nChoose up to {max_promises} of the most concrete, distinct promises. Keep each claim concise. Use at most one short quote (12 words max) per evidence array. Each quote must be ONLY a contiguous, verbatim substring from the review: no review ID, introduction, quotation wrapper, paraphrase, or ellipsis. IDs go only in evidence_review_ids and must match the reviews quoted. Omit reasoning. Do not infer failure from silence; use insufficient_evidence where needed.'''
    return f'''Listing description:\n{case["description"]}\n\nGuest reviews (Python retrieved):\n{review_text}\n\nIdentify distinct, explicit, checkable promises in the listing and assess evidence in the reviews. Return ONLY valid JSON in this schema:\n{{"promises":[{{"promise":"short claim","label":"positive|negative|mixed|insufficient_evidence","evidence_for":["exact review quote"],"evidence_against":["exact review quote"],"evidence_review_ids":["exact review ID"],"reasoning":"brief"}}]}}\nRules: Use only supplied text. Return up to {max_promises} distinct promises; prioritize concrete guest-facing claims and do not split one claim into duplicates. Include at most one short, verbatim sentence in each evidence array. Include only the IDs of reviews quoted. Keep reasoning to one short sentence (15 words maximum). Do not infer failure from silence; use insufficient_evidence when evidence is lacking.'''


def parse_json(text: str):
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.I)
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return {"promises": parsed}, None
        return parsed, None
    except Exception as first:
        match = re.search(r"\{.*\}", text, flags=re.S)
        if match:
            try:
                return json.loads(match.group()), None
            except Exception:
                pass
        return None, str(first)


def run_one(session: requests.Session, model: str, case: dict, timeout: int, max_promises: int,
             max_tokens: int, fast_mode: bool) -> dict:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a careful research assistant. Follow the JSON schema exactly."},
            {"role": "user", "content": make_prompt(case, max_promises, fast_mode)},
        ],
        "temperature": 0.1,
        "max_tokens": max_tokens,
        "stream": False,
        "response_format": PROMISE_RESPONSE_SCHEMA,
        "chat_template_kwargs": {"enable_thinking": False},
    }
    started = time.perf_counter()
    try:
        response = session.post(f"{API_BASE}/chat/completions", json=payload, timeout=timeout)
        response.raise_for_status()
        body = response.json()
        choice = body["choices"][0]
        content = choice["message"].get("content", "") or ""
        elapsed = time.perf_counter() - started
        parsed, error = parse_json(content)
        return {"model": model, "listing_id": case["listing_id"], "elapsed_seconds": round(elapsed, 3),
                "raw": content, "parsed": parsed, "json_valid": parsed is not None,
                "schema_valid": isinstance(parsed, dict) and isinstance(parsed.get("promises"), list),
                "parse_error": error, "api_error": None, "finish_reason": choice.get("finish_reason"),
                "prompt_tokens": body.get("usage", {}).get("prompt_tokens"),
                "completion_tokens": body.get("usage", {}).get("completion_tokens")}
    except Exception as exc:
        return {"model": model, "listing_id": case["listing_id"], "elapsed_seconds": round(time.perf_counter() - started, 3),
                "raw": "", "parsed": None, "json_valid": False, "schema_valid": False, "parse_error": None, "api_error": repr(exc),
                "finish_reason": None, "prompt_tokens": None, "completion_tokens": None}


def compact_chars(text: str) -> tuple[str, list[int]]:
    chars, positions = [], []
    for index, char in enumerate(text):
        if char.isalnum():
            chars.append(char.casefold())
            positions.append(index)
    return "".join(chars), positions


def quote_candidates(value) -> list[str]:
    raw = clean_text(value)
    if not raw:
        return []
    candidates = [raw]
    if "Review:" in raw:
        candidates.append(raw.rsplit("Review:", 1)[-1].strip())
    candidates.extend(
        x.strip() for x in re.findall(r"[\"'“‘](.+?)[\"'”’]", raw)
        if len(compact_chars(x.strip())[0]) >= 8
    )
    return list(dict.fromkeys(candidates))


def source_match(candidate: str, review_text: str) -> tuple[str | None, str | None]:
    if len(compact_chars(candidate)[0]) >= 8 and candidate in review_text:
        return candidate, "exact"
    qcompact, _ = compact_chars(candidate)
    tcompact, positions = compact_chars(review_text)
    if len(qcompact) >= 10:
        found = tcompact.find(qcompact)
        if found >= 0:
            start = positions[found]
            end = positions[found + len(qcompact) - 1] + 1
            return review_text[start:end], "normalized"
    parts = [x.strip() for x in re.split(r"(?:…|\.{2,})", candidate) if x.strip()]
    if len(parts) >= 2:
        spans = []
        cursor = 0
        for part in parts:
            pc, _ = compact_chars(part)
            if len(pc) < 6:
                spans = []
                break
            found = tcompact.find(pc, cursor)
            if found < 0:
                spans = []
                break
            start = positions[found]
            end = positions[found + len(pc) - 1] + 1
            spans.append((start, end))
            cursor = found + len(pc)
        if spans and spans[-1][1] - spans[0][0] <= 240:
            return review_text[spans[0][0]:spans[-1][1]], "ellipsis_reconstructed"
    return None, None


def find_quote_source(raw_quote, reviews: list[dict], cited_ids: list[str]) -> dict | None:
    candidates = quote_candidates(raw_quote)
    preferred = [str(i) for i in cited_ids]
    ordered = [r for r in reviews if r["id"] in preferred]
    ordered += [r for r in reviews if r["id"] not in preferred]
    for candidate in candidates:
        for review in ordered:
            quote, method = source_match(candidate, review["text"])
            if quote is not None:
                return {"quote": quote, "review_id": review["id"], "method": method}
    return None


def validate(result: dict, case: dict) -> list[dict]:
    if not isinstance(result.get("parsed"), dict):
        return []
    valid_review_ids = {r["id"] for r in case["reviews"]}
    rows = []
    promises = result["parsed"].get("promises", [])
    if not isinstance(promises, list):
        return [{"model": result["model"], "listing_id": case["listing_id"], "promise": "", "label": "", "quote_valid": False, "id_valid": False, "label_valid": False, "evidence_valid": False}]
    for p in promises:
        if not isinstance(p, dict):
            p = {}
        ids = p.get("evidence_review_ids", [])
        quotes_for = p.get("evidence_for", [])
        quotes_against = p.get("evidence_against", [])
        if not isinstance(ids, list): ids = []
        if not isinstance(quotes_for, list): quotes_for = []
        if not isinstance(quotes_against, list): quotes_against = []
        raw_ids = [str(i) for i in ids]
        id_valid = all(i in valid_review_ids for i in raw_ids)
        for_side = [find_quote_source(q, case["reviews"], raw_ids) for q in quotes_for]
        against_side = [find_quote_source(q, case["reviews"], raw_ids) for q in quotes_against]
        all_matches = for_side + against_side
        quote_count = len(quotes_for) + len(quotes_against)
        matched_count = sum(m is not None for m in all_matches)
        quote_valid = (matched_count == quote_count and quote_count > 0) or (
            label_is_insufficient := p.get("label") == "insufficient_evidence" and quote_count == 0
        )
        source_ids = list(dict.fromkeys(m["review_id"] for m in all_matches if m is not None))
        aligned = all(i in raw_ids for i in source_ids) if source_ids else (quote_count == 0 and id_valid)
        corrected_ids = source_ids or [i for i in raw_ids if i in valid_review_ids]
        repaired_count = sum(m is not None and (m["method"] != "exact" or m["review_id"] not in raw_ids) for m in all_matches)
        raw_exact_count = sum(m is not None and m["method"] == "exact" and m["review_id"] in raw_ids for m in all_matches)
        canonical_for = [m["quote"] if m is not None else clean_text(q) for q, m in zip(quotes_for, for_side)]
        canonical_against = [m["quote"] if m is not None else clean_text(q) for q, m in zip(quotes_against, against_side)]
        canonical_for = [q for q, m in zip(canonical_for, for_side) if m is not None]
        canonical_against = [q for q, m in zip(canonical_against, against_side) if m is not None]
        source_id_valid = all(i in valid_review_ids for i in corrected_ids)
        no_evidence_expected = p.get("label") == "insufficient_evidence" and quote_count == 0 and not raw_ids
        evidence_valid = no_evidence_expected or (quote_valid and bool(source_ids) and source_id_valid)
        label = p.get("label", "")
        label_valid = label in LABELS
        rows.append({"model": result["model"], "listing_id": case["listing_id"],
                     "promise": p.get("promise", ""), "label": label,
                     "quote_valid": quote_valid, "id_valid": id_valid, "citation_alignment_valid": aligned,
                     "source_id_valid": source_id_valid, "label_valid": label_valid, "evidence_valid": evidence_valid,
                     "evidence_quote_count": quote_count, "verified_quote_count": matched_count,
                     "repaired_quote_count": repaired_count, "raw_exact_quote_count": raw_exact_count,
                     "evidence_id_count": len(raw_ids),
                     "evidence_for": canonical_for, "evidence_against": canonical_against,
                     "evidence_for_raw": quotes_for, "evidence_against_raw": quotes_against,
                     "evidence_review_ids": corrected_ids, "model_cited_review_ids": raw_ids,
                     "quote_match_methods": [m["method"] if m else "unverified" for m in all_matches],
                     "reasoning": p.get("reasoning", "")})
    return rows


def main():
    parser = argparse.ArgumentParser(description="Fair same-input LM Studio pilot for Qwen 3.5 4B vs 9B")
    parser.add_argument("--data-dir", type=Path, default=PROJECT_DIR / "data" / "processed")
    parser.add_argument("--output-dir", type=Path, default=PROJECT_DIR / "results" / "compare_pilot")
    parser.add_argument("--models", nargs=2, default=["qwen3.5-9b", "qwen3.5-4b"], metavar=("BASELINE_9B", "CANDIDATE_4B"))
    parser.add_argument("--listings", type=int, default=3)
    parser.add_argument("--max-reviews", type=int, default=15)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--max-promises", type=int, default=12)
    parser.add_argument("--max-tokens", type=int, default=1800)
    parser.add_argument("--fast-mode", action="store_true", help="Use a compact output schema without free-text reasoning")
    parser.add_argument("--batch-mode", action="store_true", help="Run a resumable batch as part of a fixed sample")
    parser.add_argument("--total-listings", type=int, help="Total fixed sample size across all batches (up to 1,000)")
    parser.add_argument("--batch-index", type=int, default=0, help="Zero-based batch number within the fixed sample")
    parser.add_argument("--exclude-listings-file", type=Path,
                        help="CSV containing completed listing IDs in a listing_id or id column")
    parser.add_argument("--only-model", help="Run one model ID after loading that model in LM Studio")
    args = parser.parse_args()
    maximum = 100 if args.batch_mode else 10
    if args.listings < 1 or args.listings > maximum:
        parser.error(f"--listings must be between 1 and {maximum} per run.")
    total_listings = args.total_listings or args.listings
    if total_listings < args.listings or total_listings > 10000:
        parser.error("--total-listings must be at least the batch size and no more than 10,000.")
    if args.batch_mode and args.batch_index < 0:
        parser.error("--batch-index cannot be negative.")
    if not args.batch_mode and (args.total_listings is not None or args.batch_index != 0):
        parser.error("--total-listings and --batch-index require --batch-mode.")
    start_index = args.batch_index * args.listings
    if start_index >= total_listings:
        parser.error("--batch-index is outside the fixed sample.")
    expected_batch_size = min(args.listings, total_listings - start_index)
    if not 1 <= args.max_promises <= 12:
        parser.error("--max-promises must be between 1 and 12.")
    if not 256 <= args.max_tokens <= 4096:
        parser.error("--max-tokens must be between 256 and 4096.")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    selected_path = args.output_dir / "selected_inputs.json"
    config_path = args.output_dir / "run_config.json"
    models = [args.only_model] if args.only_model else args.models
    excluded_listing_ids = set()
    if args.exclude_listings_file:
        if not args.exclude_listings_file.exists():
            parser.error(f"Exclude file does not exist: {args.exclude_listings_file}")
        excluded = pd.read_csv(args.exclude_listings_file, usecols=lambda column: column in {"listing_id", "id"})
        id_column = "listing_id" if "listing_id" in excluded.columns else "id" if "id" in excluded.columns else None
        if id_column is None:
            parser.error("--exclude-listings-file must contain a listing_id or id column.")
        excluded_listing_ids = set(excluded[id_column].dropna().astype(str))
        if not excluded_listing_ids:
            parser.error("--exclude-listings-file contains no listing IDs.")
    static_config = {"models": models, "listings": args.listings, "max_reviews": args.max_reviews,
                     "max_promises": args.max_promises, "max_tokens": args.max_tokens,
                     "fast_mode": args.fast_mode, "batch_mode": args.batch_mode, "seed": args.seed,
                     "response_format": "strict_json_schema_v1",
                     "exclude_listings_file": str(args.exclude_listings_file) if args.exclude_listings_file else None,
                     "excluded_listing_count": len(excluded_listing_ids)}
    if args.batch_mode:
        static_config.update({"total_listings": total_listings, "batch_index": args.batch_index})
    cases = []
    saved_config = json.loads(config_path.read_text(encoding="utf-8")) if config_path.exists() else None
    if saved_config is not None:
        if any(saved_config.get(key) != value for key, value in static_config.items()):
            raise SystemExit(f"Run settings do not match the checkpoint in {config_path}. Choose a new output directory.")
        if not selected_path.exists():
            raise SystemExit(f"Checkpoint inputs are missing: {selected_path}")
        cases = json.loads(selected_path.read_text(encoding="utf-8"))
        if [case["listing_id"] for case in cases] != saved_config.get("listing_ids"):
            raise SystemExit(f"Selected inputs do not match the checkpoint in {config_path}.")
    elif selected_path.exists():
        cached = json.loads(selected_path.read_text(encoding="utf-8"))
        if len(cached) == expected_batch_size and all(len(c.get("reviews", [])) == args.max_reviews for c in cached):
            cases = cached
    if not cases:
        cases = select_sample_streamed(args.data_dir, expected_batch_size, args.seed, args.max_reviews,
                                       total_listings, args.batch_index, excluded_listing_ids)
    if not cases:
        raise SystemExit("No pilot cases found with a description and nonempty reviews.")
    if len(cases) != expected_batch_size:
        raise SystemExit(f"Only {len(cases)} listings had usable reviews; expected {expected_batch_size}. No model calls were made.")
    run_config = {**static_config, "listings": len(cases), "listing_ids": [case["listing_id"] for case in cases]}
    if saved_config is None:
        config_path.write_text(json.dumps(run_config, ensure_ascii=False, indent=2), encoding="utf-8")
        selected_path.write_text(json.dumps(cases, ensure_ascii=False, indent=2), encoding="utf-8")
    r = requests.get(f"{API_BASE}/models", timeout=10)
    r.raise_for_status()
    available = [x.get("id") for x in r.json().get("data", [])]
    print("LM Studio API models:", available)
    print("Selected listings:", [x["listing_id"] for x in cases])
    all_results, all_rows = [], []
    session = requests.Session()
    for model in models:
        raw_path = args.output_dir / f"raw_{model.replace(':','_').replace('/','_')}.json"
        completed_ids = set()
        prior = load_checkpoint_results(raw_path)
        if prior:
            all_results.extend(prior)
            completed_ids = {x["listing_id"] for x in prior}
            by_id = {c["listing_id"]: c for c in cases}
            for item in prior:
                if item["listing_id"] in by_id:
                    all_rows.extend(validate(item, by_id[item["listing_id"]]))
        progress = tqdm(
            enumerate(cases, 1),
            total=len(cases),
            desc=f"{model} listings",
            unit="listing",
            dynamic_ncols=True,
        )
        for i, case in progress:
            if case["listing_id"] in completed_ids:
                print(f"{model} [{i}/{len(cases)}] listing {case['listing_id']} already saved; skipping", flush=True)
                continue
            print(f"{model} [{i}/{len(cases)}] listing {case['listing_id']} ...", flush=True)
            result = run_one(session, model, case, args.timeout, args.max_promises,
                             args.max_tokens, args.fast_mode)
            all_results.append(result)
            append_checkpoint_result(raw_path, result)
            all_rows.extend(validate(result, case))
            print(f"  {result['elapsed_seconds']}s JSON={result['json_valid']} error={result['api_error']}", flush=True)
            progress.set_postfix(last_seconds=result["elapsed_seconds"], refresh=False)
        progress.close()
        model_results = [x for x in all_results if x["model"] == model]
        temp_path = raw_path.with_suffix(".json.tmp")
        temp_path.write_text(json.dumps(model_results, ensure_ascii=False, indent=2), encoding="utf-8")
        temp_path.replace(raw_path)
        checkpoint_path = raw_path.with_suffix(".jsonl")
        if checkpoint_path.exists():
            checkpoint_path.unlink()
    for model in args.models:
        raw_path = args.output_dir / f"raw_{model.replace(':','_').replace('/','_')}.json"
        already_loaded = any(x["model"] == model for x in all_results)
        if not already_loaded:
            prior = load_checkpoint_results(raw_path)
            if not prior:
                continue
            all_results.extend(prior)
            by_id = {c["listing_id"]: c for c in cases}
            for item in prior:
                case = by_id.get(item["listing_id"])
                if case:
                    all_rows.extend(validate(item, case))
    pd.DataFrame(all_rows).to_csv(args.output_dir / "promises.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame([{k: v for k, v in x.items() if k not in {"raw", "parsed"}} for x in all_results]).to_csv(
        args.output_dir / "calls.csv", index=False, encoding="utf-8-sig")
    summary = {}
    for model in sorted({x["model"] for x in all_results}):
        rs = [x for x in all_results if x["model"] == model]
        rows = [x for x in all_rows if x["model"] == model]
        quote_count = sum(x["evidence_quote_count"] for x in rows)
        verified_quote_count = sum(x["verified_quote_count"] for x in rows)
        repaired_quote_count = sum(x["repaired_quote_count"] for x in rows)
        raw_exact_quote_count = sum(x["raw_exact_quote_count"] for x in rows)
        evidence_rows = [x for x in rows if x["evidence_quote_count"] > 0]
        summary[model] = {
            "calls": len(rs), "json_valid_rate": sum(x["json_valid"] for x in rs) / len(rs) if rs else None,
            "schema_valid_rate": sum(x.get("schema_valid", isinstance(x.get("parsed"), dict) and isinstance(x["parsed"].get("promises"), list)) for x in rs) / len(rs) if rs else None,
            "total_seconds": round(sum(x["elapsed_seconds"] for x in rs), 3),
            "mean_seconds_per_listing": round(statistics.mean([x["elapsed_seconds"] for x in rs]), 3) if rs else None,
            "labels": dict(Counter(x["label"] for x in rows)),
            "quote_validation_rate": sum(x["quote_valid"] for x in rows) / len(rows) if rows else None,
            "quote_source_match_rate": verified_quote_count / quote_count if quote_count else None,
            "raw_exact_quote_rate": raw_exact_quote_count / quote_count if quote_count else None,
            "quote_repair_rate": repaired_quote_count / quote_count if quote_count else None,
            "id_validation_rate": sum(x["id_valid"] for x in rows) / len(rows) if rows else None,
            "citation_alignment_rate": sum(x["citation_alignment_valid"] for x in evidence_rows) / len(evidence_rows) if evidence_rows else None,
            "combined_evidence_validation_rate": sum(x["evidence_valid"] for x in rows) / len(rows) if rows else None,
            "promise_count": len(rows),
        }
    report = {"api_base": API_BASE, "requested_models": args.models, "run_models": sorted(set(x["model"] for x in all_results)),
              "available_models_at_start": available, "listings": [x["listing_id"] for x in cases],
              "max_reviews_per_listing": args.max_reviews, "max_promises_per_listing": args.max_promises,
              "max_tokens": args.max_tokens, "fast_mode": args.fast_mode, "seed": args.seed,
              "batch_mode": args.batch_mode, "batch_index": args.batch_index,
              "total_listings": total_listings,
              "retrieval": "deterministic lexical topic coverage with description overlap; same selected reviews passed to each model",
              "summary": summary}
    (args.output_dir / "summary.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print("Outputs:", args.output_dir.resolve())


if __name__ == "__main__":
    main()
