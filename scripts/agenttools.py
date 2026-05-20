import json
import logging
from functools import cache
from typing import Literal
from urllib.parse import quote

import httpx
import logfire
from pydantic import BaseModel, Field
from openai import pydantic_function_tool


FAST_API_URL = "https://fast.oclc.org/fastsuggest"
SUBJECT_DB = "fastapps-db/assignFAST"

logger = logging.getLogger(__name__)


@cache
def assignFast(query: str, queryIndex: str = "suggestall", rows: int = 5) -> list[dict]:
    suggestReturn = f"{queryIndex}%2Cidroot%2Cauth%2Ctag%2Ctype"
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
        with httpx.Client(timeout=10) as client:
            resp = client.get(url, headers={"User-Agent": "assignFast/1.0"})
            resp.raise_for_status()
            data = resp.json()
        docs = data["response"]["docs"]
        for d in docs:
            if isinstance(d.get("idroot"), list):
                d["idroot"] = d["idroot"][0]
        span.set_attribute("result_count", len(docs))
    logger.debug(f"Results: {docs}")
    return docs


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