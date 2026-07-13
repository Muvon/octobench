"""Objective verdict helpers: answer extraction + matchers + a programmatic
instruction-following constraint engine (IFEval/IFBench-style).

These produce the contamination-resistant `validate.sh`-equivalent verdict for QA
benchmarks: a deterministic pass/fail computed from the agent's answer and the
dataset's ground truth — no LLM judge involved.
"""
from __future__ import annotations

import json
import re
import string
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Answer extraction
# ---------------------------------------------------------------------------

# Agents are asked to write their final answer to this file in the workspace.
ANSWER_FILE = "answer.txt"


def read_answer(workspace: Path, provider_stdout: str) -> str:
    """Prefer the sentinel answer file the agent was told to write; fall back to
    the agent's final message (provider stdout)."""
    try:
        f = Path(workspace) / ANSWER_FILE
        if f.exists():
            text = f.read_text(encoding="utf-8", errors="replace").strip()
            if text:
                return text
    except Exception:
        pass
    return (provider_stdout or "").strip()


_ANSWER_TAG_RE = re.compile(r"(?:final\s*answer|answer)\s*[:\-]\s*(.+)", re.I)
_BOXED_RE = re.compile(r"\\boxed\{([^}]*)\}")


def _last_nonempty_line(text: str) -> str:
    for line in reversed((text or "").splitlines()):
        s = line.strip()
        if s:
            return s
    return ""


def extract_final(text: str) -> str:
    """Pull the most likely 'final answer' span out of a free-form response."""
    text = (text or "").strip()
    if not text:
        return ""
    boxed = _BOXED_RE.findall(text)
    if boxed:
        return boxed[-1].strip()
    m = None
    for m in _ANSWER_TAG_RE.finditer(text):
        pass  # keep the last match
    if m:
        return m.group(1).strip().strip(".")
    return _last_nonempty_line(text)


def _norm(s: str) -> str:
    s = (s or "").strip().lower()
    s = s.replace("\\$", "").replace("$", "").replace(",", "")
    s = re.sub(r"\s+", " ", s)
    return s.strip(string.punctuation + " ")


# ---------------------------------------------------------------------------
# Multiple-choice
# ---------------------------------------------------------------------------

_LETTERS = string.ascii_uppercase


def gold_letter(gold: Any, choices: List[str]) -> Optional[str]:
    """Resolve the gold answer to a choice letter (A, B, ...)."""
    if gold is None:
        return None
    g = str(gold).strip()
    # Already a letter.
    if len(g) == 1 and g.upper() in _LETTERS[: len(choices)]:
        return g.upper()
    # 0- or 1-based index.
    if g.isdigit():
        idx = int(g)
        if 0 <= idx < len(choices):
            return _LETTERS[idx]
        if 1 <= idx <= len(choices):
            return _LETTERS[idx - 1]
    # Exact answer text.
    for i, c in enumerate(choices):
        if _norm(c) == _norm(g):
            return _LETTERS[i]
    return None


def chosen_letter(response: str, choices: List[str]) -> Optional[str]:
    """Extract the letter the agent selected from a free-form response."""
    resp = (response or "").strip()
    if not resp:
        return None
    valid = set(_LETTERS[: len(choices)])
    # 1) Explicit "ANSWER: X"
    tag = extract_final(resp)
    m = re.match(r"^\(?([A-Za-z])\)?\b", tag)
    if m and m.group(1).upper() in valid:
        return m.group(1).upper()
    # 2) Patterns like "the answer is (C)"
    m = re.search(r"answer\s*(?:is|:)?\s*\(?([A-Za-z])\)?\b", resp, re.I)
    if m and m.group(1).upper() in valid:
        return m.group(1).upper()
    # 3) A lone bracketed/standalone letter anywhere late in the text.
    cands = re.findall(r"\b([A-Z])\b", resp.upper())
    cands = [c for c in cands if c in valid]
    if cands:
        return cands[-1]
    # 4) Match against choice text.
    for i, c in enumerate(choices):
        if _norm(c) and _norm(c) in _norm(resp):
            return _LETTERS[i]
    return None


def mcq_match(response: str, gold: Any, choices: List[str]) -> bool:
    gl = gold_letter(gold, choices)
    cl = chosen_letter(response, choices)
    return gl is not None and cl is not None and gl == cl


# ---------------------------------------------------------------------------
# Free-form final answer (numeric / string / math / set)
# ---------------------------------------------------------------------------


def _to_float(s: str) -> Optional[float]:
    s = _norm(s).replace("%", "").replace("\\", "")
    m = re.search(r"-?\d+(?:\.\d+)?(?:e-?\d+)?", s.replace(" ", ""))
    if not m:
        return None
    try:
        return float(m.group(0))
    except ValueError:
        return None


def final_answer_match(response: str, gold: Any, mode: str = "math", tol: float = 1e-6) -> bool:
    cand = extract_final(response)
    gold_s = str(gold)

    if mode == "letter":
        # gold is a choice letter (e.g. "D"); accept "D", "D)", "D. Weak Non-Sadism",
        # "(D)" — anything whose leading token is that letter (HLE multipleChoice).
        gl = gold_s.strip().upper()
        m = re.match(r"\s*\(?([A-Za-z])\)?[.):\s]", cand + " ")
        return bool(m) and m.group(1).upper() == gl

    if mode in ("numeric", "math"):
        gf, cf = _to_float(gold_s), _to_float(cand)
        if gf is not None and cf is not None:
            denom = max(1.0, abs(gf))
            if abs(gf - cf) <= max(tol, tol * denom):
                return True
        if mode == "numeric":
            return False
        # math: fall through to normalized string compare for symbolic answers
        return _norm(cand) == _norm(gold_s) or _norm(extract_final(gold_s)) == _norm(cand)

    if mode == "set":
        gs = {_norm(x) for x in re.split(r"[,;]", gold_s) if _norm(x)}
        cs = {_norm(x) for x in re.split(r"[,;]", cand) if _norm(x)}
        return gs == cs and len(gs) > 0

    # string
    return _norm(cand) == _norm(gold_s)


# ---------------------------------------------------------------------------
# Instruction-following constraint engine (IFEval / IFBench style)
# ---------------------------------------------------------------------------


def _word_count(text: str) -> int:
    return len(re.findall(r"\b\w[\w'-]*\b", text))


def _sentence_count(text: str) -> int:
    return len([s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()])


def _paragraph_count(text: str) -> int:
    return len([p for p in re.split(r"\n\s*\n", text.strip()) if p.strip()])


def _rel(value: int, relation: str, target: int) -> bool:
    relation = (relation or "at least").lower()
    if relation in ("at least", ">=", "minimum"):
        return value >= target
    if relation in ("at most", "<=", "less than", "maximum"):
        return value <= target
    if relation in ("exactly", "==", "equal to"):
        return value == target
    return value >= target


# Each verifier: (response_text, args) -> bool. args is a dict (IFEval kwargs).
def _v_keywords_existence(t, a):
    kws = a.get("keywords") or []
    return all(re.search(rf"\b{re.escape(k)}\b", t, re.I) for k in kws)


def _v_keywords_forbidden(t, a):
    kws = a.get("forbidden_words") or a.get("keywords") or []
    return not any(re.search(rf"\b{re.escape(k)}\b", t, re.I) for k in kws)


def _v_keyword_frequency(t, a):
    kw = a.get("keyword") or ""
    n = int(a.get("frequency", 1))
    rel = a.get("relation", "at least")
    if not kw:
        return True
    count = len(re.findall(rf"\b{re.escape(kw)}\b", t, re.I))
    return _rel(count, rel, n)


def _v_number_words(t, a):
    return _rel(_word_count(t), a.get("relation", "at least"), int(a.get("num_words", 0)))


def _v_number_sentences(t, a):
    return _rel(_sentence_count(t), a.get("relation", "at least"), int(a.get("num_sentences", 0)))


def _v_number_paragraphs(t, a):
    target = int(a.get("num_paragraphs", a.get("nth_paragraph", 0)) or 0)
    return _rel(_paragraph_count(t), a.get("relation", "exactly"), target)


def _v_number_bullets(t, a):
    n = int(a.get("num_bullets", 0))
    bullets = len(re.findall(r"^\s*[\*\-]\s+\S", t, re.M))
    return bullets == n


def _v_highlighted(t, a):
    n = int(a.get("num_highlights", 0))
    highlights = len(re.findall(r"\*[^*\n]+\*|\*\*[^*\n]+\*\*", t))
    return highlights >= n


def _v_json_format(t, a):
    s = t.strip()
    s = re.sub(r"^```(?:json)?\s*|\s*```$", "", s).strip()
    try:
        json.loads(s)
        return True
    except Exception:
        return False


def _v_title(t, a):
    return bool(re.search(r"<<[^>\n]+>>", t))


def _v_multiple_sections(t, a):
    splitter = a.get("section_spliter") or a.get("section_splitter") or "Section"
    n = int(a.get("num_sections", 0))
    count = len(re.findall(rf"{re.escape(splitter)}\s*\d+", t, re.I))
    return count >= n


def _v_placeholders(t, a):
    n = int(a.get("num_placeholders", 0))
    return len(re.findall(r"\[[^\]\n]+\]", t)) >= n


def _v_postscript(t, a):
    marker = a.get("postscript_marker", "P.S.")
    return marker.lower() in t.lower() or bool(re.search(r"\bp\.?\s*s\.?", t, re.I))


def _v_lowercase(t, a):
    letters = [c for c in t if c.isalpha()]
    return bool(letters) and all(c.islower() for c in letters)


def _v_uppercase(t, a):
    letters = [c for c in t if c.isalpha()]
    return bool(letters) and all(c.isupper() for c in letters)


def _v_capital_word_freq(t, a):
    n = int(a.get("capital_frequency", 0))
    rel = a.get("capital_relation", "at least")
    caps = len([w for w in re.findall(r"\b[A-Z][A-Z]+\b", t)])
    return _rel(caps, rel, n)


def _v_end_checker(t, a):
    phrase = (a.get("end_phrase") or "").strip().lower()
    return t.strip().lower().endswith(phrase) if phrase else True


def _v_quotation(t, a):
    s = t.strip()
    return len(s) >= 2 and s[0] == '"' and s[-1] == '"'


def _v_no_comma(t, a):
    return "," not in t


def _v_two_responses(t, a):
    return "******" in t


def _v_repeat_prompt(t, a):
    pr = (a.get("prompt_to_repeat") or "").strip()
    return t.strip().startswith(pr) if pr else True


# IFEval instruction_id -> verifier mapping (the recognized core subset).
IFEVAL_VERIFIERS = {
    "keywords:existence": _v_keywords_existence,
    "keywords:frequency": _v_keyword_frequency,
    "keywords:forbidden_words": _v_keywords_forbidden,
    "length_constraints:number_words": _v_number_words,
    "length_constraints:number_sentences": _v_number_sentences,
    "length_constraints:number_paragraphs": _v_number_paragraphs,
    "detectable_format:number_bullet_lists": _v_number_bullets,
    "detectable_format:number_highlighted_sections": _v_highlighted,
    "detectable_format:json_format": _v_json_format,
    "detectable_format:title": _v_title,
    "detectable_format:multiple_sections": _v_multiple_sections,
    "detectable_content:number_placeholders": _v_placeholders,
    "detectable_content:postscript": _v_postscript,
    "change_case:english_lowercase": _v_lowercase,
    "change_case:english_capital": _v_uppercase,
    "change_case:english_uppercase": _v_uppercase,
    "change_case:capital_word_frequency": _v_capital_word_freq,
    "startend:end_checker": _v_end_checker,
    "startend:quotation": _v_quotation,
    "punctuation:no_comma": _v_no_comma,
    "combination:two_responses": _v_two_responses,
    "combination:repeat_prompt": _v_repeat_prompt,
}

# ---------------------------------------------------------------------------
# IFBench delegation (vendored allenai/IFBench checkers, benchmarks/ifbench_vendor)
# ---------------------------------------------------------------------------


class ConstraintEngineError(RuntimeError):
    """The constraint engine itself is unusable (missing vendored deps) — abort
    the run loudly instead of silently mis-scoring."""


_IFBENCH_REGISTRY: Optional[Dict[str, Any]] = None


def _ifbench_check(cid: str, kwargs: Dict[str, Any], text: str) -> Optional[bool]:
    """Run one vendored IFBench checker; None when `cid` is not an IFBench id."""
    global _IFBENCH_REGISTRY
    if _IFBENCH_REGISTRY is None:
        try:
            from benchmarks.ifbench_vendor import INSTRUCTION_DICT
        except ImportError as e:
            raise ConstraintEngineError(
                f"constraint '{cid}' needs the vendored IFBench engine — "
                f"pip install nltk emoji syllapy 'setuptools<81' ({e})"
            ) from e
        _IFBENCH_REGISTRY = INSTRUCTION_DICT
    cls = _IFBENCH_REGISTRY.get(cid)
    if cls is None:
        return None
    checker = cls(cid)
    checker.build_description(**kwargs)
    return bool(checker.check_following(text))


# Also accept short type names in inline configs.
_SHORT_ALIASES = {
    "keywords": "keywords:existence",
    "forbidden_words": "keywords:forbidden_words",
    "word_count": "length_constraints:number_words",
    "sentence_count": "length_constraints:number_sentences",
    "paragraph_count": "length_constraints:number_paragraphs",
    "bullets": "detectable_format:number_bullet_lists",
    "json": "detectable_format:json_format",
    "title": "detectable_format:title",
    "lowercase": "change_case:english_lowercase",
    "uppercase": "change_case:english_uppercase",
    "no_comma": "punctuation:no_comma",
    "ends_with": "startend:end_checker",
    "postscript": "detectable_content:postscript",
    "placeholders": "detectable_content:number_placeholders",
    "highlighted": "detectable_format:number_highlighted_sections",
}


def verify_constraints(response: str, constraints: Any) -> Tuple[Optional[bool], Dict[str, Any]]:
    """Evaluate IFEval-style constraints against a response.

    `constraints` may be:
      - {"instruction_id_list": [...], "kwargs": [ {...}, ... ]}  (IFEval/IFBench)
      - [ {"type": "<id or short>", ...args} ]                    (inline configs)

    Returns (objective, detail). objective is None when no constraint is
    recognized (so the caller can fall back to the judge); otherwise True/False.
    """
    text = response or ""
    ids: List[str]
    kwargs: List[Dict[str, Any]]

    if isinstance(constraints, dict):
        ids = list(constraints.get("instruction_id_list") or [])
        kwargs = list(constraints.get("kwargs") or [{}] * len(ids))
    elif isinstance(constraints, list):
        ids, kwargs = [], []
        for c in constraints:
            if not isinstance(c, dict):
                continue
            cid = c.get("type") or c.get("instruction_id") or ""
            ids.append(_SHORT_ALIASES.get(cid, cid))
            kwargs.append({k: v for k, v in c.items() if k not in ("type", "instruction_id")})
    else:
        return None, {"recognized": 0, "results": [], "note": "no constraints"}

    results: List[Dict[str, Any]] = []
    recognized = 0
    all_pass = True
    for cid, kw in zip(ids, kwargs):
        cid = _SHORT_ALIASES.get(cid, cid)
        fn = IFEVAL_VERIFIERS.get(cid)
        # IFEval kwargs carry every possible key with None for the unused ones;
        # drop None so verifiers fall back to their defaults instead of int(None).
        kw = {k: v for k, v in (kw or {}).items() if v is not None}
        try:
            if fn is not None:
                ok = bool(fn(text, kw))
            else:
                ib = _ifbench_check(cid, kw, text)
                if ib is None:
                    results.append({"id": cid, "status": "skipped"})
                    continue
                ok = ib
        except ConstraintEngineError:
            raise
        except Exception as e:  # a buggy verifier must not crash the run
            recognized += 1
            results.append({"id": cid, "status": "error", "error": str(e)})
            all_pass = False
            continue
        recognized += 1
        results.append({"id": cid, "status": "pass" if ok else "fail"})
        all_pass = all_pass and ok

    if recognized == 0:
        return None, {"recognized": 0, "results": results, "note": "no recognized constraints"}
    return all_pass, {"recognized": recognized, "results": results}
