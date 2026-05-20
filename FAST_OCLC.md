# FAST (Faceted Application of Subject Terminology) — OCLC Metadata Standards

## 1. What is FAST?

**FAST** (Faceted Application of Subject Terminology) is a controlled subject vocabulary developed by **OCLC Research** in collaboration with the **Library of Congress** (begun in 1998). It is derived from Library of Congress Subject Headings (LCSH) but restructured into a simplified, **faceted** system that is easier to apply and more machine-friendly.

- ~1.8 million authority records across all facets
- Openly available under the **ODC-By (Open Data Commons Attribution) License**
- No API key required for access
- Expressed as **Linked Open Data** using SKOS and schema.org
- Designed for both MARC and non-MARC environments (Dublin Core, MODS, institutional repositories, etc.)

---

## 2. The Eight (or Nine) FACETS

FAST separates subject concepts into distinct, independently usable facets. This is the core of the system — rather than complex pre-coordinated strings (as in LCSH), each facet stands alone and can be combined post-coordinately.

| Facet | MARC Tag(s) | Description | Query Index (API) |
|---|---|---|---|
| **Topical** | 650 | Concepts, objects, things, processes, disciplines | `suggest50` |
| **Geographic** | 651 | Place names, jurisdictions, regions | `suggest51` |
| **Personal Name** | 600 | Names of individual people | `suggest00` |
| **Corporate Name** | 610 | Names of organizations, institutions | `suggest10` |
| **Events** | 611, 647 | Named events (wars, conferences, etc.) | `suggest11` |
| **Uniform Titles** | 630 | Titles of works that are the *subject* of the resource | `suggest30` |
| **Chronological** | 648 | Time periods, dates, date ranges | *(via SRU query)* |
| **Form/Genre** (8th facet) | 655 | What the resource *is* (form or genre), not what it's *about* | `suggest55` |
| **Meeting Names** (sometimes 9th) | 611 | Meeting/conference names | (included in Events) |

> **Key principle**: Form/Genre describes *what the resource is* (e.g., "Photographs," "Maps," "Biographies"). All other facets describe *what the resource is about*.

---

## 3. How to Derive Subject Metadata from a Description — Step-by-Step Process

### Phase A: Analyze the Description

From a natural-language description of a digital item, you must **identify candidate concepts** that map to each facet. For example, given:

> *"A 1935 black-and-white photograph of the Golden Gate Bridge under construction in San Francisco, California."*

You extract:
- **Topical**: bridges, construction, suspension bridges, photographic postcards
- **Geographic**: San Francisco (Calif.), Golden Gate Bridge
- **Chronological**: 1935, 1930-1939
- **Form/Genre**: Photographs, Black-and-white photographs

### Phase B: Look Up Authorized Terms

There are three main ways to look up and assign FAST headings:

#### Method 1: searchFAST Web Interface
URL: https://fast.oclc.org/searchfast/

- Full-featured search interface
- Browse/search by facet
- View MARC-formatted output for copy/paste
- No registration required

#### Method 2: assignFAST (Autosuggest)
URL (demo): https://fast.oclc.org/assignfast/

- Autosuggest-style lookup as you type
- Can be integrated into cataloging interfaces
- Shows authorized headings vs. "see also" references

#### Method 3: FAST API (Programmatic)
Base autosuggest URL: `http://fast.oclc.org/searchfast/fastsuggest`

**Parameters:**
| Parameter | Required | Description |
|---|---|---|
| `query` | Yes | Search text |
| `queryIndex` | Yes | Facet index (see table above) |
| `queryReturn` | Yes | Fields to return (comma-separated) |
| `rows` | Yes | Max rows (1–20) |
| `callback` | Yes | JSONP callback name |

**Query Indices:**
- `suggestall` — All facets at once
- `suggest50` — Topical
- `suggest51` — Geographic
- `suggest00` — Personal names
- `suggest10` — Corporate names
- `suggest11` — Events
- `suggest30` — Uniform titles
- `suggest55` — Form/Genre

**Example request** (topical search for "bridges"):
```
GET http://fast.oclc.org/searchfast/fastsuggest?query=bridges&queryIndex=suggest50&queryReturn=suggestall,idroot,auth,tag,type&rows=5&suggest=autosuggest&callback=myCallback
```

**Example response** (before callback wrapper):
```json
{
  "responseHeader": { "status": 0, "QTime": 100 },
  "response": {
    "numFound": 500,
    "docs": [
      {
        "idroot": "fst00838737",
        "tag": 650,
        "type": "auth",
        "auth": "Bridges"
      },
      {
        "idroot": "fst00838747",
        "tag": 650,
        "type": "auth",
        "auth": "Bridges--Design and construction"
      }
    ]
  }
}
```

**Additional undocumented sort parameter** (as of 2024): `&sort=usage+desc` returns results ordered by frequency of use in WorldCat rather than alphabetically.

#### Method 4: SRU Search API
URL: `http://fast.oclc.org/search`

Full CQL-based querying. Example:
```
GET http://fast.oclc.org/search?query=cql.any+%3D+%22san+francisco%22&httpAccept=application/xml
```

#### Method 5: Linked Data API
Read individual FAST records at:
```
GET http://id.worldcat.org/fast/{FAST_ID}/{format}
```
Formats: `marc21.xml`, `rdf.xml`, `nt`, `jsonld`, etc.

---

## 4. MARC Encoding Recommendations

When adding FAST headings to MARC records:

| Facet | MARC Field | Indicators | Subfields |
|---|---|---|---|
| Topical | `650` | `\7` | `$a [term] $2 fast $0 (OCoLC)fst[ID]` |
| Geographic | `651` | `\7` | `$a [place] $2 fast $0 (OCoLC)fst[ID]` |
| Personal Name | `600` | `1\7` | `$a [name] $2 fast $0 (OCoLC)fst[ID]` |
| Corporate Name | `610` | `2\7` | `$a [name] $2 fast $0 (OCoLC)fst[ID]` |
| Event | `647` | `\7` | `$a [event] $2 fast $0 (OCoLC)fst[ID]` |
| Uniform Title | `630` | `0\7` | `$a [title] $2 fast $0 (OCoLC)fst[ID]` |
| Chronological | `648` | `\7` | `$a [time period] $2 fast $0 (OCoLC)fst[ID]` |
| Form/Genre | `655` | `\7` | `$a [term] $2 fast $0 (OCoLC)fst[ID]` |

**Second indicator** is always `7` (source specified in $2).
**$2** is always `fast`.
**$0** contains the OCLC FAST URI: `(OCoLC)fst` + the numeric ID.

---

## 5. Practical Workflow: Description → FAST Subject Metadata

Here is a complete pipeline for processing a digital item description:

```
Step 1: Receive description text
  Example: "Oral history interview with Dr. Maria Lopez conducted in 2022
            discussing healthcare access in rural Arizona during the COVID-19 pandemic."

Step 2: Extract facet candidates
  ┌─────────────────────┬──────────────────────────────────────────────┐
  │ Facet               │ Candidate terms                              │
  ├─────────────────────┼──────────────────────────────────────────────┤
  │ Topical             │ oral history, medical care, health services  │
  │                     │ accessibility, rural health, COVID-19        │
  │ Personal Name       │ Lopez, Maria                                 │
  │ Geographic          │ Arizona                                      │
  │ Chronological       │ 2022, 2020-2023                              │
  │ Event               │ COVID-19 Pandemic (2020-2023)                │
  │ Form/Genre          │ Oral histories, Interviews, Sound recordings │
  └─────────────────────┴──────────────────────────────────────────────┘

Step 3: Query the FAST API for each candidate (by facet)
  For topical:     GET /searchfast/fastsuggest?query=rural+health&queryIndex=suggest50&...
  For geographic:  GET /searchfast/fastsuggest?query=arizona&queryIndex=suggest51&...
  For form/genre:  GET /searchfast/fastsuggest?query=oral+histories&queryIndex=suggest55&...
  For personal:    GET /searchfast/fastsuggest?query=lopez+maria&queryIndex=suggest00&...

Step 4: Select best match from results (review authorized heading, FAST ID)

Step 5: Output as subject metadata
  Using MARC:        650 \7 $a Rural health $2 fast $0 (OCoLC)fst01101651
  Using Dublin Core: <dc:subject>Rural health</dc:subject>
                     <dc:subject xsi:type="fast">http://id.worldcat.org/fast/1101651</dc:subject>
```

---

## 6. Automation Approaches (Code-Based)

Python example using the assignFAST API:
```python
import requests
from urllib.parse import quote

def suggest_fast(query, facet="suggestall", rows=5):
    """Query FAST suggest API for subject headings."""
    params = {
        "query": query,
        "queryIndex": facet,
        "queryReturn": "suggestall,idroot,auth,tag,type",
        "rows": rows,
        "suggest": "autosuggest",
        "wt": "json"
    }
    url = "http://fast.oclc.org/searchfast/fastsuggest?" + "&".join(
        f"{k}={quote(str(v))}" for k, v in params.items()
    )
    resp = requests.get(url)
    data = resp.json()
    return data["response"]["docs"]

# Example: get topical suggestions
results = suggest_fast("rural health", facet="suggest50")
for r in results:
    print(f"{r['auth']} (FAST ID: {r['idroot']}, Tag: {r['tag']})")
```

Known third-party tools:
- **[fast-reconcile](https://github.com/lawlesst/fast-reconcile)** — OpenRefine reconciliation service for FAST
- **Columbia University experiment** (code4lib 2024) — OCR extraction → TF-IDF → FAST API query → CSV output
- **OCLC FAST Converter** — Batch converts LCSH headings to FAST headings (https://fast.oclc.org/lcsh2fast/)
- **WorldCat automatic FAST generation** — For records already in WorldCat with LCSH, FAST is automatically added monthly

---

## 7. Key Principles & Best Practices

1. **One facet per heading** — Unlike LCSH, do not subdivide across facets. Each FAST heading represents exactly one facet.

2. **Geographic names list the largest jurisdiction first** (e.g., "United States—Arizona—Maricopa County"), unlike LCSH which uses indirect order.

3. **Chronological headings are flexible** — You can use any date range that accurately describes the work (e.g., "1800-1849" rather than LCSH's pre-established period subdivisions).

4. **Form/Genre is separate** — Index it as form/genre, not as subject. All other facets are indexed as subjects.

5. **Linked Data URIs** — Each FAST heading has a permanent URI at `http://id.worldcat.org/fast/[NUMBER]`. Use these for semantic web/linked data applications.

6. **No API key needed** — The FAST API is freely available for non-commercial use.

7. **Human review is still essential** — Automated suggestion is imperfect; results may require human intervention and review.

---

## 8. Key Resources

| Resource | URL |
|---|---|
| searchFAST (web search) | https://fast.oclc.org/searchfast/ |
| assignFAST (autosuggest demo) | https://fast.oclc.org/assignfast/ |
| assignFAST API docs | https://www.oclc.org/developer/api/oclc-apis/fast-api/assign-fast.en.html |
| FAST Linked Data API docs | https://www.oclc.org/developer/api/oclc-apis/fast-api/linked-data.en.html |
| FAST Converter (LCSH→FAST) | https://fast.oclc.org/lcsh2fast/ |
| FAST FAQ (PDF) | https://www.oclc.org/content/dam/oclc/fast/FAST-FAQ-Nov2019.pdf |
| FAST Quick Start Guide | https://www.oclc.org/content/dam/oclc/fast/FAST-quick-start-guide-2022.pdf |
| FAST Data Download | https://www.oclc.org/research/themes/data-science/fast/download.html |
| FAST Policy & Outreach Committee | https://www.oclc.org/en/fast/committee.html |
| Yale FAST Guide | https://web.library.yale.edu/cataloging/authorities/fast |
| FAST Principles and Application (book) | https://oclc.org/research/publications/2010/fast-principles-and-application.html |
