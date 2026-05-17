import json
from functools import cache
from urllib.parse import quote
from urllib.request import urlopen, Request


FAST_API_URL = "https://fast.oclc.org/fastsuggest"
SUBJECT_DB = "fastapps-db/assignFAST"


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
    req = Request(url, method="GET")
    req.add_header("User-Agent", "assignFast/1.0")
    with urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    docs = data["response"]["docs"]
    for d in docs:
        if isinstance(d.get("idroot"), list):
            d["idroot"] = d["idroot"][0]
    return docs


assignFast_tool = {
    "type": "function",
    "function": {
        "name": "assignFast",
        "description": "Query the OCLC FAST subject authority API to look up authorized FAST headings for library cataloging.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search text for the FAST heading to look up",
                },
                "queryIndex": {
                    "type": "string",
                    "enum": [
                        "suggestall",
                        "suggest50",
                        "suggest51",
                        "suggest00",
                        "suggest10",
                        "suggest11",
                        "suggest30",
                        "suggest55",
                    ],
                    "description": "FAST facet index: suggestall (all), suggest50 (Topical), suggest51 (Geographic), suggest00 (Personal Name), suggest10 (Corporate Name), suggest11 (Events), suggest30 (Uniform Title), suggest55 (Form/Genre)",
                },
                "rows": {
                    "type": "integer",
                    "description": "Maximum number of results to return (1-20)",
                    "minimum": 1,
                    "maximum": 20,
                },
            },
            "required": ["query"],
        },
    },
}