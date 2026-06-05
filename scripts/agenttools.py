import json
import logging
import threading
from functools import cache
from typing import Literal
from urllib.parse import quote

import httpx
import logfire
from pydantic import BaseModel, Field
from openai import pydantic_function_tool
from tenacity import retry, wait_random_exponential, stop_after_attempt, retry_if_exception_type


FAST_API_URL = "https://fast.oclc.org/fastsuggest"
SUBJECT_DB = "fastapps-db/assignFAST"

FACET_INDEX_MAP = {
    "topical": "suggest50",
    "geographic": "suggest51",
    "personal_name": "suggest00",
    "corporate_name": "suggest10",
    "events": "suggest11",
    "uniform_title": "suggest30",
    "form_genre": "suggest55",
}

_TRANSIENT_EXCEPTIONS = (
    httpx.TimeoutException,
    httpx.NetworkError,
    httpx.RemoteProtocolError,
    httpx.HTTPStatusError,
    json.JSONDecodeError,
)

_api_semaphore = threading.Semaphore(4)

logger = logging.getLogger(__name__)


@cache
@retry(
    wait=wait_random_exponential(min=1, max=10),
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type(_TRANSIENT_EXCEPTIONS),
    retry_error_callback=lambda s: [],
)
def assignFast(query: str, queryIndex: str = "suggestall", rows: int = 1) -> list[dict]:
    suggestReturn = "idroot%2Cauth%2Ctag"
    query_str = (
        f"query={quote(query)}"
        f"&queryIndex={queryIndex}"
        f"&queryReturn={suggestReturn}"
        f"&suggest={SUBJECT_DB}"
        f"&wt=json"
        f"&rows={rows}"
    )
    url = f"{FAST_API_URL}?{query_str}"
    logger.debug(f"Query: {query_str}")
    with logfire.span("FAST API lookup", query=query, queryIndex=queryIndex, rows=rows) as span:
        try:
            with _api_semaphore:
                with httpx.Client(timeout=10) as client:
                    resp = client.get(url, headers={"User-Agent": "assignFast/1.0"})
                    resp.raise_for_status()
                    data = resp.json()
            docs = data["response"]["docs"]
            span.set_attribute("result_count", len(docs))
            logger.debug(f"Results: {docs}")
            return docs
        except _TRANSIENT_EXCEPTIONS:
            raise
        except (KeyError, TypeError) as e:
            logger.error(f"FAST API unexpected response structure for query={query!r}: {e}")
            span.set_attribute("error", str(e))
    return []


def resolve_candidates(candidates: dict) -> dict[str, dict]:
    results = {}
    for facet, terms in candidates.items():
        if facet == "chronological" or not terms:
            continue
        query_index = FACET_INDEX_MAP.get(facet)
        if not query_index:
            continue
        for term in terms:
            docs = assignFast(term, queryIndex=query_index, rows=1)
            if docs:
                d = docs[0]
                results[term] = {
                    "heading": d.get("auth", term),
                    "fast_id": d.get("idroot", ""),
                    "marc_tag": str(d.get("tag", "")),
                }
    return results


class AssignFastParams(BaseModel):
    query: str = Field(description="Search text for the FAST heading to look up")
    queryIndex: Literal[
        "suggestall",
        "suggest50",
        "suggest51",
        "suggest00",
        "suggest10",
        "suggest11",
        "suggest30",
        "suggest55",
    ] = Field(
        default="suggestall",
        description="FAST facet index: suggestall (all), suggest50 (Topical), suggest51 (Geographic), suggest00 (Personal Name), suggest10 (Corporate Name), suggest11 (Events), suggest30 (Uniform Title), suggest55 (Form/Genre)",
    )
    rows: int = Field(
        default=5,
        description="Maximum number of results to return (1-20)",
        ge=1,
        le=20,
    )


assignFast_tool = pydantic_function_tool(
    AssignFastParams,
    name="assignFast",
    description="Query the OCLC FAST subject authority API to look up authorized FAST headings for library cataloging.",
)