# OCLC Subject Term Cleanup — FAST Facet Extraction with LLMs

This project uses large language models (LLMs) to automatically extract [FAST](https://www.oclc.org/research/activities/fast.html) (Faceted Application of Subject Terminology) subject terms from archival metadata descriptions. It processes records from the Kerr-McGee Corporation collection (University of Oklahoma Western History Collections) and compares candidate terms across multiple models.

## Workflow

1. **Input**: An Excel file (`data/input/`) with bibliographic metadata columns including titles, descriptions, dates, and existing subjects.
2. **Extraction**: For each record, the `Description (Islandora)` field is sent to an LLM with a system prompt asking it to return structured FAST subject candidates as JSON across eight facets.
3. **Output**: The original records are augmented with columns of extracted candidates (one per model) and saved as CSV to `data/output/`.

## FAST Facets

| Facet | Description |
|---|---|
| `topical` | Subject topics |
| `geographic` | Places and locations |
| `personal_name` | Individual people |
| `corporate_name` | Organizations and companies |
| `events` | Named events |
| `uniform_title` | Uniform titles |
| `chronological` | Date ranges or specific years |
| `form_genre` | Form, genre, or physical characteristics |

## Project Structure

```
├── config/
│   └── settings.yml          # API base URL and authentication config
├── data/
│   ├── input/                # Input Excel metadata files
│   └── output/               # Enriched CSV output
├── prompts/
│   └── candidates.md         # LLM system prompt for subject extraction
├── scripts/
│   ├── extract.ipynb         # Jupyter notebook driving the extraction pipeline
│   ├── extractors.py         # Pydantic model: Candidates (typed FAST facets)
│   └── utils.py              # API client, retry logic, data loading, logfire instrumentation
├── requirements.txt
└── opencode.json
```

## Setup

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Configure `config/settings.yml`:
   - `token_auth`: API key source — a shell command (`cmd`), environment variable (`env`), or interactive prompt (`prompt`)
   - `base_url`: OpenAI-compatible API endpoint

3. Place your input Excel file in `data/input/`.

## Usage

Open and run the Jupyter notebook:

```
jupyter notebook scripts/extract.ipynb
```

The notebook:
- Loads the Excel file from `data/input/`
- Reads the system prompt from `prompts/candidates.md`
- Calls the configured LLM(s) on each record's description
- Saves the enriched dataset to `data/output/metadata.csv`

Configure which models to compare by editing the `extract.ipynb` cell that calls `process()`. Currently compares `gpt-oss` and `gemma4` against the same records.

## Dependencies

httpx, openai, pandas, pydantic, logfire, tenacity, openpyxl, PyYAML, pytest
