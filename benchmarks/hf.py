"""Hugging Face datasets-server row fetcher.

Generalizes the row fetch in cli/swebench.py so any QA/dataset benchmark can pull
rows over HTTP (no `datasets` dependency, no auth for public datasets). Mirrors the
endpoint the SWE-bench-Live runner already uses.
"""
from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

HF_ROWS = "https://datasets-server.huggingface.co/rows"
_PAGE = 100  # datasets-server caps `length` at 100 rows per request
_RETRIES = 4  # the public endpoint occasionally drops the TLS connection mid-read


def fetch_rows(
    dataset: str,
    split: str,
    length: int = _PAGE,
    offset: int = 0,
    config: str = "default",
) -> List[Dict[str, Any]]:
    url = (
        f"{HF_ROWS}?dataset={urllib.parse.quote(dataset)}"
        f"&config={urllib.parse.quote(config)}&split={urllib.parse.quote(split)}"
        f"&offset={offset}&length={min(length, _PAGE)}"
    )
    last_err: Optional[Exception] = None
    for attempt in range(_RETRIES):
        try:
            with urllib.request.urlopen(url, timeout=90) as resp:  # noqa: S310 (trusted HF endpoint)
                data = json.load(resp)
            return [r["row"] for r in data.get("rows", [])]
        except Exception as e:  # transient TLS/EOF/5xx — back off and retry
            last_err = e
            if attempt < _RETRIES - 1:
                time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"HF fetch failed for {dataset}[{config}/{split}]: {last_err}")


def fetch_n(
    dataset: str,
    split: str,
    n: int,
    config: str = "default",
) -> List[Dict[str, Any]]:
    """Fetch up to `n` rows, paginating in pages of 100."""
    out: List[Dict[str, Any]] = []
    offset = 0
    while len(out) < n:
        page = fetch_rows(dataset, split, length=_PAGE, offset=offset, config=config)
        if not page:
            break
        out.extend(page)
        offset += len(page)
        if len(page) < _PAGE:
            break
    return out[:n]


def fetch_jsonl(
    url: str,
    n: int,
    row_filter: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Fetch up to `n` rows from a JSONL file over HTTP (e.g. a GitHub raw URL).

    Streams line-by-line and stops as soon as `n` rows match `row_filter`
    (field == value equality), so large upstream files are only partially read.
    """
    last_err: Optional[Exception] = None
    for attempt in range(_RETRIES):
        out: List[Dict[str, Any]] = []
        try:
            with urllib.request.urlopen(url, timeout=90) as resp:  # noqa: S310
                for raw in resp:
                    line = raw.strip()
                    if not line:
                        continue
                    row = json.loads(line)
                    if row_filter and any(row.get(k) != v for k, v in row_filter.items()):
                        continue
                    out.append(row)
                    if len(out) >= n:
                        return out
            return out
        except Exception as e:  # transient TLS/EOF/5xx — back off and retry
            last_err = e
            if attempt < _RETRIES - 1:
                time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"JSONL fetch failed for {url}: {last_err}")


def get_field(row: Dict[str, Any], path: Optional[str], default: Any = None) -> Any:
    """Read a (possibly dotted, list-indexable) field path from a row.

    Examples: "question", "choices.text", "metadata.0.answer".
    """
    if not path:
        return default
    cur: Any = row
    for part in str(path).split("."):
        if isinstance(cur, dict):
            cur = cur.get(part)
        elif isinstance(cur, list):
            try:
                cur = cur[int(part)]
            except (ValueError, IndexError):
                return default
        else:
            return default
        if cur is None:
            return default
    return cur
