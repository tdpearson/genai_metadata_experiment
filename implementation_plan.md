# Implementation Plan: Two-Phase Pre-Resolution Pipeline

## Overview

Replace the current LLM tool-calling pattern with a three-step pipeline that separates candidate extraction, server-side API resolution, and final selection/formatting. Token usage drops ~85–90%.

```
Before:   [System Prompt + Description] → LLM decides tool calls → round-trips × N → Output
After:    [Short Cand. Prompt + Description] → LLM → Candidates
                                                ↓
                                          Python resolves via FAST API
                                                ↓
                                         [Short Sel. Prompt + Resolved Data] → LLM → Output
```

---

## Step 1: New prompt file — `prompts/candidates.md`

**Create** a new file (~35 lines). Instructs the LLM to extract candidate terms organized by facet. Returns structured JSON. No tool instructions, no MARC encoding rules, no example output.

```markdown
You are a library metadata specialist. From the description below, extract candidate FAST subject terms organized by facet.

Return ONLY a JSON object with these keys (omit empty arrays):
- topical, geographic, personal_name, corporate_name, events, uniform_title, chronological, form_genre

Each value is an array of candidate term strings. List 2-5 candidates per applicable facet.
- Be specific and relevant to the content
- For chronological: use date ranges like "1930-1939" or specific years
- Return ONLY the JSON, no other text
```

No tool definitions, no function schema — this prompt is ~90% shorter than `Extract_OCLC.md`.

---

## Step 2: Rewrite `prompts/Extract_OCLC.md` (Phase 3 prompt)

**Replace** the current 138-line prompt with a shorter version (~35 lines). Now used only for the final selection/formatting step. The LLM receives pre-resolved FAST results and just picks the best headings.

```markdown
You are a library metadata specialist. Below is a description and pre-resolved FAST API results for candidate terms. Select the best 5-8 subject headings and format as JSON.

Rules:
- Each heading is one facet. Do not combine.
- For geographic: largest jurisdiction first.
- Use the exact authorized heading and FAST URI from results.
- MARC encoding: second indicator 7, $2 fast, $0 (OCoLC)fst<ID>.

Output JSON:
{
  "item_title": "short title",
  "subject_headings": [{"heading": "", "fast_uri": "", "marc_tag": "6xx", "facet": ""}],
  "marc_encoding": ""
}
```

---

## Step 3: Add `resolve_candidates()` to `agenttools.py`

**Add** a new function that takes the candidate JSON dict from Phase 1 and resolves all terms via the FAST API server-side. No LLM involved.

**Key details:**
- Maps facet names → queryIndex (e.g., `topical` → `suggest50`)
- Calls `assignFast()` with `rows=1` for each candidate term (reduced from 5)
- Returns a minimal dict: `{term: {heading, fast_id, marc_tag}}`
- Skips `chronological` facet (no API needed, same as today)
- Uses `@cache` benefit — repeated lookups are instant

**Also**: Reduce `assignFast()` default `rows=5` → `rows=1` and trim `queryReturn` to just `auth,idroot,tag` (drop `type`).

---

## Step 4: Refactor `utils.py` — `extract()` and `extract_async()`

**Replace** the tool-calling loop with the three-phase pipeline:

```
Phase 1 — Candidate Extraction:
  LLM call with candidates.md prompt + description → returns {topical: [...], geographic: [...], ...}
  No tools, no function schema.

Phase 2 — Server-Side Resolution:
  Call resolve_candidates(candidates) → dict of {term: {heading, fast_id, marc_tag}}
  Pure Python, zero LLM tokens.

Phase 3 — Selection & Formatting:
  LLM call with Extract_OCLC.md prompt + {description, fast_results} → returns final OclcFast JSON
  No tools, no function schema.
```

**Total LLM calls per record: 2** (down from 6–11).

**Backward compatibility:** The function signatures don't change:
```python
def extract(model, system_prompt, extractor, record_content): ...
```
`system_prompt` still accepted (used as Phase 3 prompt). `candidates.md` is read internally. The notebook (`extract.ipynb`) continues to work unchanged.

---

## Step 5: Add intermediate model to `extractors.py` (optional)

**Add** a `Candidates` Pydantic model for structured parsing of Phase 1 output:

```python
class Candidates(BaseModel):
    topical: list[str] = []
    geographic: list[str] = []
    personal_name: list[str] = []
    corporate_name: list[str] = []
    events: list[str] = []
    uniform_title: list[str] = []
    chronological: list[str] = []
    form_genre: list[str] = []
```

This gives type safety and `.model_validate_json()` for Phase 1 parsing (same pattern as current `OclcFast`). Could also just use `json.loads()` if simplicity is preferred.

---

## Step 6: Rewrite tests in `test_utils.py`

**Replace** tool-call-based tests with three-phase pipeline tests:

| Test | What it covers |
|---|---|
| `test_extract_candidates_parsed` | Phase 1 returns valid Candidates JSON |
| `test_extract_full_pipeline` | All 3 phases produce correct OclcFast output |
| `test_extract_empty_fast_results` | Phase 2 returns empty dict → Phase 3 handles it |
| `test_extract_api_error_fallback` | LLM call fails → returns None |
| `test_extract_malformed_candidates` | Phase 1 returns bad JSON → handled gracefully |
| `test_extract_async_pipeline` | Same tests for async variant |

Remove `_make_tool_call()` helper. Simplify `_make_chat_response()` (no `tool_calls` param needed).

---

## Step 7: Update `assignFast()` defaults (quick win during refactor)

In `agenttools.py`:
- **Line 20**: Change `rows: int = 5` → `rows: int = 1`
- **Line 21**: Change `queryReturn` to just `"idroot,auth,tag"` (drop `type`, drop redundant `queryIndex` prefix)
- After **line 37**: Remove the `idroot` list-coercion loop (not needed with `rows=1`)

---

## Migration Path

| Order | File | Action |
|---|---|---|
| 1 | `prompts/candidates.md` | **Create** new file |
| 2 | `prompts/Extract_OCLC.md` | **Replace** with short selection prompt |
| 3 | `agenttools.py` | Add `FACET_INDEX_MAP`, `resolve_candidates()`, reduce defaults |
| 4 | `extractors.py` | Add `Candidates` model (optional) |
| 5 | `utils.py` | Refactor `extract()` and `extract_async()`, drop tool imports |
| 6 | `test_utils.py` | Rewrite tests for new pipeline |
| 7 | Run `pytest` | Verify all tests pass |
| 8 | Run notebook | Spot-check output quality on a few records |

---

## Token Impact Summary

| Metric | Before | After |
|---|---|---|
| System prompt size | ~1,000 tokens (Extract_OCLC.md) | ~250 tokens (Phase 1) + ~200 tokens (Phase 3) |
| Tool schema overhead | ~250 tokens × N round-trips | **0** |
| Tool result tokens | ~500 tokens × N round-trips | **0** |
| LLM calls per record | 6–11 | **2** |
| Total tokens per record (est.) | 3,000–8,000 | **400–900** |
| **Reduction** | — | **~85–90%** |

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Phase 1 LLM returns incomplete candidates | Prompt instructs "be generous, list 2–5 per facet" |
| FAST API returns no results for a candidate | `resolve_candidates` silently skips it; Phase 3 sees only what succeeded |
| Model doesn't support `response_format: json_object` | Detect via error/fallback to `_clean_model_response()` pattern |
| Output quality changes vs tool-calling approach | A/B test on 10 records from the existing dataset |
