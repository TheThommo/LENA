"""
Mechanical assertion checks for the PULSE evaluation harness.
These are string/structure predicates — never LLM judgement.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class AssertionResult:
    name: str
    passed: bool
    detail: str
    defect_id: str = ""


@dataclass
class BriefSections:
    full: str
    key_findings: str = ""
    bottom_line: str = ""
    other: str = ""

    @classmethod
    def parse(cls, brief: str) -> "BriefSections":
        text = brief or ""
        # Split on markdown ## headers
        parts = re.split(r"(?m)^##\s+", text)
        key = ""
        bottom = ""
        other_bits: list[str] = []
        if parts:
            # preamble before first ##
            other_bits.append(parts[0])
        for block in parts[1:]:
            lines = block.splitlines()
            title = (lines[0] if lines else "").strip().lower()
            body = "\n".join(lines[1:]) if len(lines) > 1 else ""
            if "key finding" in title:
                key = body
            elif "bottom line" in title:
                bottom = body
            else:
                other_bits.append(body)
        return cls(full=text, key_findings=key, bottom_line=bottom, other="\n".join(other_bits))

    def scope_text(self, scope: str) -> str:
        scope = (scope or "all").lower()
        if scope in ("key_findings", "key findings", "findings"):
            return self.key_findings or self.full
        if scope in ("bottom_line", "bottom line"):
            return self.bottom_line or self.full
        if scope == "all":
            return self.full
        return self.full


def _contains_any(text: str, patterns: list[str]) -> Optional[str]:
    lower = text.lower()
    for p in patterns:
        if p.lower() in lower:
            return p
        # allow flexible whitespace / punctuation in regex-ish patterns
        try:
            if re.search(p, text, flags=re.IGNORECASE):
                return p
        except re.error:
            continue
    return None


def qualifier_preserved(
    brief: str,
    term: str,
    variants: list[str],
    scope: str = "all",
    defect_id: str = "D1",
) -> AssertionResult:
    """
    If any variant of the concept appears in scope, the precise qualifier term
    (or an accepted precise form) must also appear. Broadened-only language fails.
    """
    sections = BriefSections.parse(brief)
    text = sections.scope_text(scope)
    precise_forms = [term] + [v for v in variants if v.startswith("=")]
    precise_forms = [p[1:] if p.startswith("=") else p for p in precise_forms]
    # variants without '=' are broadened/forbidden stand-ins when used alone
    broad = [v for v in variants if not v.startswith("=")]

    has_precise = _contains_any(text, precise_forms) is not None
    has_broad = _contains_any(text, broad) is not None

    if has_broad and not has_precise:
        return AssertionResult(
            name="qualifier_preserved",
            passed=False,
            detail=(
                f"scope={scope}: found broadened form(s) without precise term "
                f"{term!r}. broad={broad}"
            ),
            defect_id=defect_id,
        )
    if has_precise or not has_broad:
        return AssertionResult(
            name="qualifier_preserved",
            passed=True,
            detail=f"scope={scope}: precise qualifier intact or concept absent",
            defect_id=defect_id,
        )
    return AssertionResult(
        name="qualifier_preserved",
        passed=False,
        detail=f"scope={scope}: qualifier {term!r} not preserved",
        defect_id=defect_id,
    )


def forbidden_unqualified(
    brief: str,
    pattern: str,
    scope: str,
    reason: str,
    defect_id: str = "D1",
) -> AssertionResult:
    sections = BriefSections.parse(brief)
    text = sections.scope_text(scope)
    hit = _contains_any(text, [pattern])
    if hit:
        return AssertionResult(
            name="forbidden_unqualified",
            passed=False,
            detail=f"scope={scope}: forbidden {pattern!r} — {reason}",
            defect_id=defect_id,
        )
    return AssertionResult(
        name="forbidden_unqualified",
        passed=True,
        detail=f"scope={scope}: pattern absent",
        defect_id=defect_id,
    )


def internal_consistency(brief: str, defect_id: str = "D2") -> AssertionResult:
    """
    Detect Key Findings vs Bottom Line genotype-scope contradiction:
    KF restricts to homozygotes/e4/4 while BL broadens to all ApoE4 carriers.
    """
    sections = BriefSections.parse(brief)
    kf = sections.key_findings.lower()
    bl = sections.bottom_line.lower()
    if not kf or not bl:
        # If sections missing, treat as fail for consistency harness cases
        if "## key findings" in sections.full.lower() and "## bottom line" in sections.full.lower():
            return AssertionResult(
                name="internal_consistency",
                passed=False,
                detail="sections present but empty after parse",
                defect_id=defect_id,
            )
        return AssertionResult(
            name="internal_consistency",
            passed=True,
            detail="insufficient section structure to contradict",
            defect_id=defect_id,
        )

    precise_kf = bool(
        re.search(r"e4\s*/\s*e?4|ε4\s*/\s*ε4|homozygot", kf, re.I)
    )
    broad_bl = bool(
        re.search(r"apoe4\s+carriers?|apoe\s*e4\s+carriers?|apoe\s*ε4\s+carriers?", bl, re.I)
    ) and not bool(re.search(r"homozygot|e4\s*/\s*e?4|ε4\s*/\s*ε4", bl, re.I))

    if precise_kf and broad_bl:
        return AssertionResult(
            name="internal_consistency",
            passed=False,
            detail="Key Findings restrict to e4/4/homozygotes but Bottom Line broadens to all ApoE4 carriers",
            defect_id=defect_id,
        )
    return AssertionResult(
        name="internal_consistency",
        passed=True,
        detail="no KF/BL genotype-scope contradiction detected",
        defect_id=defect_id,
    )


def claim_provenance_complete(
    claims: list[dict[str, Any]],
    defect_id: str = "D11",
) -> AssertionResult:
    if not claims:
        return AssertionResult(
            name="claim_provenance_complete",
            passed=False,
            detail="no claims provided",
            defect_id=defect_id,
        )
    missing = []
    for i, c in enumerate(claims):
        if not c.get("claim_id"):
            missing.append(f"[{i}] claim_id")
        if not c.get("source_ids"):
            missing.append(f"[{i}] source_ids")
        span = c.get("span") or c.get("supporting_span")
        if not span:
            missing.append(f"[{i}] span")
    if missing:
        return AssertionResult(
            name="claim_provenance_complete",
            passed=False,
            detail=f"missing provenance fields: {', '.join(missing[:12])}",
            defect_id=defect_id,
        )
    return AssertionResult(
        name="claim_provenance_complete",
        passed=True,
        detail=f"{len(claims)} claims fully provenanced",
        defect_id=defect_id,
    )


# Published status thresholds — must stay in sync with pulse_engine.
from app.core.pulse_engine import CONFIDENCE_STATUS_THRESHOLDS as _PULSE_THRESHOLDS

CONFIDENCE_STATUS_THRESHOLDS = tuple(
    (float(t), s.value if hasattr(s, "value") else str(s))
    for t, s in _PULSE_THRESHOLDS
)


def status_for_confidence(confidence: float) -> str:
    for threshold, label in CONFIDENCE_STATUS_THRESHOLDS:
        if confidence >= threshold:
            return label
    return "insufficient_validation"


def confidence_status_coherent(
    confidence: float,
    status: str,
    defect_id: str = "D3",
) -> AssertionResult:
    expected = status_for_confidence(float(confidence or 0.0))
    # Normalize aliases
    status_n = (status or "").strip().lower()
    if status_n == "insufficient":
        status_n = "insufficient_validation"
    if status_n != expected:
        return AssertionResult(
            name="confidence_status_coherent",
            passed=False,
            detail=f"status={status_n!r} incoherent with confidence={confidence:.2f} (expected {expected!r})",
            defect_id=defect_id,
        )
    return AssertionResult(
        name="confidence_status_coherent",
        passed=True,
        detail=f"status={status_n} matches confidence={confidence:.2f}",
        defect_id=defect_id,
    )


def divergence_absent(
    diverging_sources: list[str],
    source: str,
    reason: str,
    defect_id: str = "D4",
) -> AssertionResult:
    names = {s.lower() for s in diverging_sources}
    if source.lower() in names:
        return AssertionResult(
            name="divergence_absent",
            passed=False,
            detail=f"{source} incorrectly flagged as divergent — {reason}",
            defect_id=defect_id,
        )
    return AssertionResult(
        name="divergence_absent",
        passed=True,
        detail=f"{source} not flagged as divergent",
        defect_id=defect_id,
    )


def divergence_present(
    edge_cases_or_flags: list[dict[str, Any]] | list[str],
    topic: str,
    defect_id: str = "D5",
) -> AssertionResult:
    """
    Require that a contradiction/supersession on `topic` was surfaced.
    Accepts either reason strings or edge-case dicts with reason/topic/claim fields.
    """
    blob_parts: list[str] = []
    for item in edge_cases_or_flags:
        if isinstance(item, str):
            blob_parts.append(item)
        elif isinstance(item, dict):
            blob_parts.append(
                " ".join(
                    str(item.get(k, ""))
                    for k in (
                        "reason",
                        "topic",
                        "classification",
                        "divergence_type",
                        "summary",
                        "claim",
                    )
                )
            )
            for c in item.get("claims") or []:
                if isinstance(c, dict):
                    blob_parts.append(str(c.get("span") or c.get("text") or ""))
                else:
                    blob_parts.append(str(c))
    blob = " ".join(blob_parts).lower()
    if topic.lower() not in blob and not re.search(re.escape(topic), blob, re.I):
        return AssertionResult(
            name="divergence_present",
            passed=False,
            detail=f"expected divergence on topic {topic!r} not surfaced",
            defect_id=defect_id,
        )
    return AssertionResult(
        name="divergence_present",
        passed=True,
        detail=f"divergence on {topic!r} present",
        defect_id=defect_id,
    )


def source_class_present(
    source_names: list[str],
    source_class: str,
    defect_id: str = "D8",
) -> AssertionResult:
    class_map = {
        "regulatory": {"dailymed", "openfda", "ods_dsld"},
        "trial_registry": {"clinical_trials"},
        "guideline": {"who_iris", "cdc"},
        "literature": {
            "pubmed", "cochrane", "openalex", "semantic_scholar", "europe_pmc",
        },
    }
    allowed = class_map.get(source_class.lower())
    if not allowed:
        return AssertionResult(
            name="source_class_present",
            passed=False,
            detail=f"unknown source class {source_class!r}",
            defect_id=defect_id,
        )
    present = {s.lower() for s in source_names}
    hit = present & allowed
    if not hit:
        return AssertionResult(
            name="source_class_present",
            passed=False,
            detail=f"no {source_class} sources in ranked/returned set {sorted(present)}",
            defect_id=defect_id,
        )
    return AssertionResult(
        name="source_class_present",
        passed=True,
        detail=f"{source_class} present via {sorted(hit)}",
        defect_id=defect_id,
    )


def preferred_source_class_leads(
    ranked_source_names: list[str],
    source_class: str,
    defect_id: str = "E8",
) -> AssertionResult:
    """
    E8: the top-ranked result must come from the planned source class
    (label / trial registry / guideline), not background literature.
    """
    class_map = {
        "regulatory": {"dailymed", "openfda", "ods_dsld"},
        "trial_registry": {"clinical_trials"},
        "guideline": {"who_iris", "cdc"},
        "literature": {
            "pubmed", "cochrane", "openalex", "semantic_scholar", "europe_pmc",
        },
    }
    allowed = class_map.get(source_class.lower())
    if not allowed:
        return AssertionResult(
            name="preferred_source_class_leads",
            passed=False,
            detail=f"unknown source class {source_class!r}",
            defect_id=defect_id,
        )
    if not ranked_source_names:
        return AssertionResult(
            name="preferred_source_class_leads",
            passed=False,
            detail="no ranked sources to evaluate lead class",
            defect_id=defect_id,
        )
    lead = (ranked_source_names[0] or "").lower()
    if lead not in allowed:
        return AssertionResult(
            name="preferred_source_class_leads",
            passed=False,
            detail=(
                f"lead source {lead!r} is not in planned class {source_class!r}; "
                f"ranked={list(ranked_source_names)[:5]}"
            ),
            defect_id=defect_id,
        )
    return AssertionResult(
        name="preferred_source_class_leads",
        passed=True,
        detail=f"lead source {lead!r} matches class {source_class!r}",
        defect_id=defect_id,
    )


def themes_are_clusters(
    themes: list[str],
    defect_id: str = "D7",
) -> AssertionResult:
    """
    Themes must be real multi-word phrase clusters (or empty/omitted).

    Fail modes (E7):
    - alphabetised single-token keyword lists
    - space-joined alphabetised token bags ("ace adults agents arbs")
    """
    if not themes:
        return AssertionResult(
            name="themes_are_clusters",
            passed=True,
            detail="themes omitted (acceptable)",
            defect_id=defect_id,
        )

    def _alpha_join(phrase: str) -> bool:
        # ≥3 tokens: real bigrams are often alphabetical by chance
        words = [w for w in re.findall(r"[a-z0-9\-]+", (phrase or "").lower()) if w]
        return len(words) >= 3 and words == sorted(words)

    single_tokens = [
        t
        for t in themes
        if isinstance(t, str) and " " not in t.strip() and "-" not in t
    ]
    # Fail if majority are raw single tokens (the production failure mode)
    if len(themes) >= 4 and len(single_tokens) / len(themes) >= 0.75:
        lowered = [t.lower() for t in themes]
        if lowered == sorted(lowered) and all(len(t.split()) == 1 for t in themes):
            return AssertionResult(
                name="themes_are_clusters",
                passed=False,
                detail=f"themes look like alphabetised raw tokens: {themes[:8]}",
                defect_id=defect_id,
            )
        return AssertionResult(
            name="themes_are_clusters",
            passed=False,
            detail=f"themes are predominantly raw tokens: {themes[:8]}",
            defect_id=defect_id,
        )

    alpha_joins = [t for t in themes if isinstance(t, str) and _alpha_join(t)]
    if len(themes) >= 2 and len(alpha_joins) / len(themes) >= 0.5:
        return AssertionResult(
            name="themes_are_clusters",
            passed=False,
            detail=f"themes look like alphabetised token-joins: {themes[:8]}",
            defect_id=defect_id,
        )

    return AssertionResult(
        name="themes_are_clusters",
        passed=True,
        detail=f"{len(themes)} theme cluster(s) acceptable",
        defect_id=defect_id,
    )


def source_dates_present_in_narrative(
    brief: str,
    min_dates: int = 1,
    defect_id: str = "D9",
) -> AssertionResult:
    # Years 19xx/20xx in narrative
    years = re.findall(r"\b(?:19|20)\d{2}\b", brief or "")
    if len(years) < min_dates:
        return AssertionResult(
            name="source_dates_present_in_narrative",
            passed=False,
            detail=f"found {len(years)} year mentions, need >= {min_dates}",
            defect_id=defect_id,
        )
    return AssertionResult(
        name="source_dates_present_in_narrative",
        passed=True,
        detail=f"found {len(years)} year mention(s)",
        defect_id=defect_id,
    )


def approvals_not_called_guidelines(
    brief: str,
    defect_id: str = "D10",
) -> AssertionResult:
    """
    Fail if marketing authorisation / FDA approval is labelled as a 'guideline'
    in the same clause (advisory vs legal force).
    Distinguishing language (advisory / distinct / separate) is allowed.
    Interrogative contrasts ("approval or a guideline?") are not conflation.
    """
    text = brief or ""
    for m in re.finditer(
        r"([^.?\n]{0,90}\bguidelines?\b[^.?\n]{0,90})",
        text,
        re.I,
    ):
        window = m.group(1)
        if not re.search(
            r"(?:FDA|EMA|CHMP|marketing authori[sz]ation|approv(?:al|ed))",
            window,
            re.I,
        ):
            continue
        if re.search(
            r"(?:advisor(?:y|ily)|distinct|different from|not (?:themselves|the same)|"
            r"separat(?:e|ely)|legal(?:ly)? binding|do not (?:themselves )?confer|"
            r"approv(?:al|ed)\s+or\s+(?:an?\s+)?guidelines?|"
            r"guidelines?\s+or\s+(?:an?\s+)?approv|"
            r"approv(?:al|ed)\s+versus\s+guidelines?|"
            r"guidelines?\s+versus\s+approv|"
            r"is that an?\s+approv)",
            window,
            re.I,
        ):
            continue
        return AssertionResult(
            name="approvals_not_called_guidelines",
            passed=False,
            detail=f"approvals conflated with guidelines: …{window.strip()}…",
            defect_id=defect_id,
        )
    return AssertionResult(
        name="approvals_not_called_guidelines",
        passed=True,
        detail="no approval/guideline conflation detected",
        defect_id=defect_id,
    )


def top_source_not_irrelevant(
    ranked_sources: list[str],
    forbidden_first: list[str],
    defect_id: str = "D12",
) -> AssertionResult:
    if not ranked_sources:
        return AssertionResult(
            name="top_source_not_irrelevant",
            passed=False,
            detail="empty ranked source list",
            defect_id=defect_id,
        )
    top = ranked_sources[0]
    # Allow either source name or title substring match against forbidden list
    top_l = top.lower()
    for f in forbidden_first:
        if f.lower() in top_l or top_l in f.lower():
            return AssertionResult(
                name="top_source_not_irrelevant",
                passed=False,
                detail=f"irrelevant result ranked first: {top!r} matches forbidden {f!r}",
                defect_id=defect_id,
            )
    return AssertionResult(
        name="top_source_not_irrelevant",
        passed=True,
        detail=f"top ranked acceptable: {top!r}",
        defect_id=defect_id,
    )


def status_is(
    status: str,
    expected: str,
    defect_id: str = "D3",
) -> AssertionResult:
    got = (status or "").lower()
    exp = expected.lower()
    if got != exp:
        return AssertionResult(
            name="status_is",
            passed=False,
            detail=f"status={got!r} expected {exp!r}",
            defect_id=defect_id,
        )
    return AssertionResult(
        name="status_is",
        passed=True,
        detail=f"status={got}",
        defect_id=defect_id,
    )


def _norm_title(title: str) -> str:
    t = re.sub(r"[^a-z0-9]+", " ", (title or "").lower()).strip()
    return re.sub(r"\s+", " ", t)


def _work_key(item: dict[str, Any] | Any) -> str:
    if isinstance(item, dict):
        doi = (item.get("doi") or "").strip().lower()
        pmid = (item.get("pmid") or "").strip().lower()
        title = _norm_title(item.get("title") or "")
    else:
        doi = (getattr(item, "doi", None) or "").strip().lower()
        pmid = (getattr(item, "pmid", None) or "").strip().lower()
        title = _norm_title(getattr(item, "title", "") or "")
    if doi:
        return f"doi:{doi}"
    if pmid:
        return f"pmid:{pmid}"
    if title:
        return f"title:{title}"
    return ""


def dedup_correct(
    papers: list[Any],
    defect_id: str = "E1",
) -> AssertionResult:
    """
    No DOI/PMID/normalized-title may appear on more than one counted paper
    under different database source_names without being treated as one work.
    Fail when the same work key is present under >=2 source_names in the corpus.
    """
    by_key: dict[str, set[str]] = {}
    for p in papers or []:
        key = _work_key(p)
        if not key:
            continue
        src = ""
        if isinstance(p, dict):
            src = (p.get("source_name") or p.get("source") or "").lower()
        else:
            src = (getattr(p, "source_name", "") or "").lower()
        by_key.setdefault(key, set()).add(src)
    dupes = {k: sorted(v) for k, v in by_key.items() if len(v) >= 2}
    if dupes:
        sample = list(dupes.items())[:3]
        return AssertionResult(
            name="dedup_correct",
            passed=False,
            detail=f"same work under multiple databases (not deduped): {sample}",
            defect_id=defect_id,
        )
    return AssertionResult(
        name="dedup_correct",
        passed=True,
        detail=f"{len(by_key)} distinct work keys; no cross-DB duplicates",
        defect_id=defect_id,
    )


def distinct_source_count_accurate(
    pulse: Any,
    papers: list[Any],
    defect_id: str = "E1",
) -> AssertionResult:
    """
    Cross-validation / corroboration must not treat duplicate works as independent.
    If the same work appears in >=2 DBs and total_cross_validations credits that
    pair, fail. Also fail when narrative claims N sources but distinct works < N
    for the duplicated set.
    """
    by_key: dict[str, list[Any]] = {}
    for p in papers or []:
        key = _work_key(p)
        if key:
            by_key.setdefault(key, []).append(p)
    multi = {k: v for k, v in by_key.items() if len(v) >= 2}
    if not multi:
        return AssertionResult(
            name="distinct_source_count_accurate",
            passed=True,
            detail="no multi-DB duplicate works in corpus",
            defect_id=defect_id,
        )

    # If pulse recorded cross-validations between same-title different sources, fail
    xv = list(getattr(pulse, "cross_validations", None) or [])
    bad = []
    for x in xv:
        ta = _norm_title(getattr(x, "paper_a_title", "") or "")
        tb = _norm_title(getattr(x, "paper_b_title", "") or "")
        if ta and ta == tb and getattr(x, "paper_a_source", None) != getattr(x, "paper_b_source", None):
            bad.append((ta[:60], getattr(x, "paper_a_source", ""), getattr(x, "paper_b_source", "")))
    raw_count = len(papers or [])
    distinct = len(by_key)
    if bad or (raw_count > distinct and getattr(pulse, "total_cross_validations", 0) > 0):
        return AssertionResult(
            name="distinct_source_count_accurate",
            passed=False,
            detail=(
                f"distinct_works={distinct} raw_papers={raw_count}; "
                f"duplicate-title cross-validations={bad[:3]}; "
                f"total_cross_validations={getattr(pulse, 'total_cross_validations', 0)}"
            ),
            defect_id=defect_id,
        )
    return AssertionResult(
        name="distinct_source_count_accurate",
        passed=True,
        detail=f"distinct_works={distinct} raw_papers={raw_count}; no dupe xv pairs",
        defect_id=defect_id,
    )


def relevance_lead(
    brief: str,
    lead_must_include: Optional[list[str]] = None,
    lead_must_not_include: Optional[list[str]] = None,
    lead_must_include_all_groups: Optional[list[list[str]]] = None,
    defect_id: str = "E2",
) -> AssertionResult:
    """
    First substantive paragraph/sentence must match a query sub-question cue
    and must not lead with forbidden off-topic cues.

    lead_must_include: any-of tokens
    lead_must_include_all_groups: each inner list is an any-of group; ALL groups
    must match (e.g. US territory AND EU territory for a comparative query).
    """
    text = (brief or "").strip()
    if not text:
        return AssertionResult(
            name="relevance_lead",
            passed=False,
            detail="empty brief",
            defect_id=defect_id,
        )
    # Skip uncertainty notices
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    while lines and lines[0].lower().startswith("**uncertainty"):
        lines = lines[1:]
    lead = lines[0] if lines else ""
    # If first line is a header, take next
    if lead.startswith("#"):
        lead = lines[1] if len(lines) > 1 else lead
    lead_l = lead.lower()
    # Also inspect the first ~400 chars for early off-topic prevalence dumps
    head = text[:400].lower()
    for bad in lead_must_not_include or []:
        if bad.lower() in lead_l or bad.lower() in head:
            return AssertionResult(
                name="relevance_lead",
                passed=False,
                detail=f"lead/head contains forbidden off-topic {bad!r}: {lead[:180]!r}",
                defect_id=defect_id,
            )
    if lead_must_include_all_groups:
        missing_groups = []
        for group in lead_must_include_all_groups:
            if not any(tok.lower() in lead_l for tok in group):
                missing_groups.append(group)
        if missing_groups:
            return AssertionResult(
                name="relevance_lead",
                passed=False,
                detail=(
                    f"lead missing required cue groups {missing_groups!r}: {lead[:180]!r}"
                ),
                defect_id=defect_id,
            )
    if lead_must_include:
        if not any(tok.lower() in lead_l for tok in lead_must_include):
            return AssertionResult(
                name="relevance_lead",
                passed=False,
                detail=(
                    f"lead missing sub-question cues {lead_must_include!r}: {lead[:180]!r}"
                ),
                defect_id=defect_id,
            )
    return AssertionResult(
        name="relevance_lead",
        passed=True,
        detail=f"lead ok: {lead[:160]!r}",
        defect_id=defect_id,
    )


def no_verbatim_dump(
    brief: str,
    claims: list[dict[str, Any]],
    min_words: int = 12,
    defect_id: str = "E3",
) -> AssertionResult:
    """
    Fail if >= min_words contiguous words from a single claim span appear in the brief
    as a near-verbatim dump (composition must synthesise, not concatenate).
    """
    brief_l = re.sub(r"\s+", " ", (brief or "").lower()).strip()
    if not brief_l:
        return AssertionResult(
            name="no_verbatim_dump",
            passed=False,
            detail="empty brief",
            defect_id=defect_id,
        )
    for c in claims or []:
        span = (c.get("span") or c.get("text") or "").strip()
        if not span:
            continue
        words = re.findall(r"[a-z0-9ε]+", span.lower())
        if len(words) < min_words:
            continue
        window = " ".join(words[:min_words])
        # also try mid-span window
        windows = [window]
        if len(words) >= min_words + 4:
            windows.append(" ".join(words[2 : 2 + min_words]))
        for w in windows:
            if w and w in brief_l:
                return AssertionResult(
                    name="no_verbatim_dump",
                    passed=False,
                    detail=f">={min_words} contiguous claim words dumped: {w!r}",
                    defect_id=defect_id,
                )
    return AssertionResult(
        name="no_verbatim_dump",
        passed=True,
        detail=f"no >={min_words}-word verbatim claim dump detected",
        defect_id=defect_id,
    )


def divergence_wellformed(
    divergence_flags: list[dict[str, Any]],
    defect_id: str = "E5",
) -> AssertionResult:
    """
    Any surfaced divergence must name a real shared proposition (multi-word topic),
    not a token fragment, and must be CONTRADICTION or TEMPORAL_SUPERSESSION.
    """
    if not divergence_flags:
        return AssertionResult(
            name="divergence_wellformed",
            passed=True,
            detail="no divergences surfaced",
            defect_id=defect_id,
        )
    bad = []
    for d in divergence_flags:
        klass = (d.get("classification") or d.get("divergence_type") or "").upper()
        topic = (d.get("topic") or "").strip()
        tokens = topic.split()
        if klass not in ("CONTRADICTION", "TEMPORAL_SUPERSESSION"):
            # Absence / keyword edges should not appear as divergences
            bad.append(f"non-conflict class={klass!r} topic={topic!r}")
            continue
        if len(tokens) < 2 or (len(tokens) <= 3 and all(len(t) <= 4 for t in tokens)):
            bad.append(f"token-fragment topic={topic!r}")
    if bad:
        return AssertionResult(
            name="divergence_wellformed",
            passed=False,
            detail="; ".join(bad[:4]),
            defect_id=defect_id,
        )
    return AssertionResult(
        name="divergence_wellformed",
        passed=True,
        detail=f"{len(divergence_flags)} divergence(s) well-formed",
        defect_id=defect_id,
    )


def key_not_stale(
    valid_as_of: str = "",
    review_by: str = "",
    defect_id: str = "STALE",
) -> AssertionResult:
    """Fail case as STALE when review_by is past (not a pipeline defect)."""
    from datetime import date

    if not review_by:
        return AssertionResult(
            name="key_not_stale",
            passed=True,
            detail=f"no review_by (valid_as_of={valid_as_of or 'n/a'})",
            defect_id=defect_id,
        )
    try:
        due = date.fromisoformat(review_by[:10])
    except ValueError:
        return AssertionResult(
            name="key_not_stale",
            passed=False,
            detail=f"invalid review_by={review_by!r}",
            defect_id=defect_id,
        )
    if date.today() > due:
        return AssertionResult(
            name="key_not_stale",
            passed=False,
            detail=f"STALE key: review_by={review_by} valid_as_of={valid_as_of}",
            defect_id=defect_id,
        )
    return AssertionResult(
        name="key_not_stale",
        passed=True,
        detail=f"key fresh through {review_by}",
        defect_id=defect_id,
    )


ASSERTION_DISPATCH = {
    "qualifier_preserved": lambda args, ctx: qualifier_preserved(ctx["brief"], **args),
    "forbidden_unqualified": lambda args, ctx: forbidden_unqualified(ctx["brief"], **args),
    "internal_consistency": lambda args, ctx: internal_consistency(ctx["brief"], **args),
    "claim_provenance_complete": lambda args, ctx: claim_provenance_complete(ctx.get("claims") or [], **args),
    "confidence_status_coherent": lambda args, ctx: confidence_status_coherent(
        ctx["confidence"], ctx["status"], **args
    ),
    "divergence_absent": lambda args, ctx: divergence_absent(ctx.get("diverging_sources") or [], **args),
    "divergence_present": lambda args, ctx: divergence_present(ctx.get("divergence_flags") or [], **args),
    "source_class_present": lambda args, ctx: source_class_present(ctx.get("source_names") or [], **args),
    "preferred_source_class_leads": lambda args, ctx: preferred_source_class_leads(
        ctx.get("ranked_source_names") or [], **args
    ),
    "themes_are_clusters": lambda args, ctx: themes_are_clusters(ctx.get("themes") or [], **args),
    "source_dates_present_in_narrative": lambda args, ctx: source_dates_present_in_narrative(ctx["brief"], **args),
    "approvals_not_called_guidelines": lambda args, ctx: approvals_not_called_guidelines(ctx["brief"], **args),
    "top_source_not_irrelevant": lambda args, ctx: top_source_not_irrelevant(ctx.get("ranked_titles") or [], **args),
    "status_is": lambda args, ctx: status_is(ctx["status"], **args),
    "dedup_correct": lambda args, ctx: dedup_correct(ctx.get("papers") or [], **args),
    "distinct_source_count_accurate": lambda args, ctx: distinct_source_count_accurate(
        ctx.get("pulse"), ctx.get("papers") or [], **args
    ),
    "relevance_lead": lambda args, ctx: relevance_lead(ctx["brief"], **args),
    "no_verbatim_dump": lambda args, ctx: no_verbatim_dump(ctx["brief"], ctx.get("claims") or [], **args),
    "divergence_wellformed": lambda args, ctx: divergence_wellformed(
        ctx.get("divergence_flags") or [], **args
    ),
    "key_not_stale": lambda args, ctx: key_not_stale(**args),
}


def run_assertion(spec: dict[str, Any], ctx: dict[str, Any]) -> AssertionResult:
    atype = spec["type"]
    args = {k: v for k, v in spec.items() if k not in ("type",)}
    fn = ASSERTION_DISPATCH.get(atype)
    if not fn:
        return AssertionResult(name=atype, passed=False, detail=f"unknown assertion type {atype}")
    return fn(args, ctx)
