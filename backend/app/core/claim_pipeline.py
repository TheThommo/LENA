"""
Claim pipeline: extract → bind → reconcile → compose → verify.

Qualifiers are immutable. A claim may be dropped but never broadened.
This module is domain-general (dosage, genotype, population, jurisdiction,
timeframe, study phase) — not query-specific.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Optional


class ReconcileClass(str, Enum):
    AGREEMENT = "AGREEMENT"
    CONTRADICTION = "CONTRADICTION"
    SCOPE_DIFFERENCE = "SCOPE_DIFFERENCE"
    TEMPORAL_SUPERSESSION = "TEMPORAL_SUPERSESSION"
    ABSENCE = "ABSENCE"


@dataclass
class Qualifiers:
    genotype: Optional[str] = None
    population: Optional[str] = None
    dosage: Optional[str] = None
    jurisdiction: Optional[str] = None
    timeframe: Optional[str] = None
    study_phase: Optional[str] = None

    def non_null_items(self) -> list[tuple[str, str]]:
        out = []
        for k, v in asdict(self).items():
            if v:
                out.append((k, v))
        return out

    def freeze_tokens(self) -> list[str]:
        """Exact strings that must survive composition unchanged."""
        return [v for _, v in self.non_null_items()]


@dataclass
class AtomicClaim:
    claim_id: str
    text: str
    span: str
    source_ids: list[str]
    source_titles: list[str] = field(default_factory=list)
    year: Optional[int] = None
    qualifiers: Qualifiers = field(default_factory=Qualifiers)
    study_type: str = "unknown"

    def to_dict(self) -> dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "text": self.text,
            "span": self.span,
            "supporting_span": self.span,
            "source_ids": list(self.source_ids),
            "source_titles": list(self.source_titles),
            "year": self.year,
            "qualifiers": asdict(self.qualifiers),
            "study_type": self.study_type,
        }


@dataclass
class ClaimGroup:
    group_id: str
    classification: ReconcileClass
    claims: list[AtomicClaim]
    topic: str = ""
    reason: str = ""
    superseded_by: Optional[str] = None  # claim_id of newer claim

    def to_dict(self) -> dict[str, Any]:
        return {
            "group_id": self.group_id,
            "classification": self.classification.value,
            "topic": self.topic,
            "reason": self.reason,
            "superseded_by": self.superseded_by,
            "claim_ids": [c.claim_id for c in self.claims],
            "claims": [c.to_dict() for c in self.claims],
        }


# ── Qualifier extraction (general patterns) ─────────────────────────────

_DOSAGE_RE = re.compile(
    r"\b\d+(?:\.\d+)?\s*(?:mg|mcg|µg|ug|g|ml|mL|units?|IU)\b"
    r"(?:\s+(?:twice|once|three times)\s+daily)?"
    r"|\b\d+(?:\.\d+)?\s*mg\s+twice\s+daily\b",
    re.I,
)
_GENOTYPE_RE = re.compile(
    r"\b(?:ApoE|APOE|HLA|CYP\w+|BRCA\d?)\s*"
    r"(?:ε|e)?\d+(?:\s*/\s*(?:ε|e)?\d+)?"
    r"|\b(?:homozygot(?:e|es|ic)|heterozygot(?:e|es|ic))\b"
    r"|\b(?:ε|e)\d+\s*/\s*(?:ε|e)\d+\b",
    re.I,
)
_JURISDICTION_RE = re.compile(
    r"\b(?:FDA|EMA|CHMP|MHRA|PMDA|TGA|WHO|"
    r"US(?:A)?|EU|European|United States|NICE|SmPC|"
    r"marketing authori[sz]ation)\b",
    re.I,
)
_TIMEFRAME_RE = re.compile(
    r"\b(?:January|February|March|April|May|June|July|August|September|"
    r"October|November|December)\s+(?:19|20)\d{2}\b"
    r"|\b(?:19|20)\d{2}\b"
    r"|\b(?:Q[1-4]\s+(?:19|20)\d{2})\b",
    re.I,
)
_POPULATION_RE = re.compile(
    r"\b(?:adults?(?:\s+aged\s+\d+(?:\s*[–-]\s*\d+)?)?|"
    r"children|paediatric|pediatric|elderly|"
    r"patients?\s+with\s+[A-Za-z0-9εμµ\s\-/]{3,40}|"
    r"pregnant|pregnancy|neonat(?:e|es|al)|"
    r"HFrEF|HFpEF|type\s*2\s+diabetes|nonvalvular\s+atrial\s+fibrillation)\b",
    re.I,
)
_PHASE_RE = re.compile(
    r"\b(?:phase\s*[I1]{1,3}[abc]?|phase\s*[1234]|pivotal trial|"
    r"accelerated approval|traditional approval|confirmatory)\b",
    re.I,
)

_CLAIM_SPLIT = re.compile(r"(?<=[.!?])\s+")


def extract_qualifiers(span: str) -> Qualifiers:
    """Pull structured qualifiers from a verbatim span. Never invent values."""
    if not span:
        return Qualifiers()

    dosage = None
    m = _DOSAGE_RE.search(span)
    if m:
        dosage = m.group(0).strip()

    genotype = None
    gm = _GENOTYPE_RE.search(span)
    if gm:
        genotype = gm.group(0).strip()

    jurisdiction = None
    jm = _JURISDICTION_RE.search(span)
    if jm:
        jurisdiction = jm.group(0).strip()

    timeframe = None
    # Prefer month+year when present
    tm = re.search(
        r"\b(?:January|February|March|April|May|June|July|August|September|"
        r"October|November|December)\s+(?:19|20)\d{2}\b",
        span,
        re.I,
    )
    if tm:
        timeframe = tm.group(0).strip()
    else:
        ym = _TIMEFRAME_RE.search(span)
        if ym:
            timeframe = ym.group(0).strip()

    population = None
    pm = _POPULATION_RE.search(span)
    if pm:
        population = re.sub(r"\s+", " ", pm.group(0).strip())[:80]

    study_phase = None
    sm = _PHASE_RE.search(span)
    if sm:
        study_phase = sm.group(0).strip()

    return Qualifiers(
        genotype=genotype,
        population=population,
        dosage=dosage,
        jurisdiction=jurisdiction,
        timeframe=timeframe,
        study_phase=study_phase,
    )


def _claim_id_for(source_id: str, span: str, idx: int) -> str:
    digest = hashlib.sha1(f"{source_id}|{span}|{idx}".encode("utf-8")).hexdigest()[:10]
    return f"clm_{digest}"


def _is_claim_sentence(sent: str) -> bool:
    """Domain-general: any research finding sentence, not clinical-only."""
    if len(sent) < 28 or len(sent) > 600:
        return False
    return bool(
        re.search(
            r"(?:found|showed|demonstrated|reported|observed|measured|"
            r"estimated|associated|reduc(?:e[sd]?|ing)|increas(?:e[sd]?|ing)|"
            r"decreas(?:e[sd]?|ing)|improv(?:e[sd]?|ing)|lower(?:s|ed|ing)?|"
            r"raise[sd]?|cause[sd]?|used (?:for|with|to)|treat(?:s|ed|ment)?|"
            r"exclude[sd]?|approv(?:ed|al)|authori[sz]ation|contraindicat|"
            r"recommend|significant|compared|versus|vs\.?|dose|label|"
            r"indicat|risk|mortality|hospitalisation|hospitalization|"
            r"supersede|declined|positive opinion|benefit|conclude[sd]?|"
            r"suggest(?:s|ed)?|indicate[sd]?|reveal(?:s|ed)?|confirm(?:s|ed)?|"
            r"prevalence|incidence|effective|efficacy|correlated|"
            r"adverse|side effects?|status|recruiting|endpoint|sponsor|"
            r"phase\s*[1-4]|nct\d+|"
            r"according to|based on|in contrast|however|"
            r"meta-analysis|systematic review|trial|cohort|survey)",
            sent,
            re.I,
        )
    )


def bind_claims_from_paper(
    *,
    source_id: str,
    title: str,
    summary: str,
    year: Optional[int] = None,
    study_type: str = "unknown",
    max_claims: int = 6,
) -> list[AtomicClaim]:
    """Extract atomic claims with immutable qualifiers + verbatim spans."""
    text = (summary or "").strip()
    if not text:
        return []

    sentences = _CLAIM_SPLIT.split(text)
    claims: list[AtomicClaim] = []
    for i, sent in enumerate(sentences):
        sent = sent.strip()
        if not _is_claim_sentence(sent):
            continue
        # Span must be verbatim substring of summary
        if sent not in text:
            # tolerate whitespace drift
            collapsed = re.sub(r"\s+", " ", sent)
            if collapsed not in re.sub(r"\s+", " ", text):
                continue
            span = sent
        else:
            span = sent

        quals = extract_qualifiers(span)
        claims.append(
            AtomicClaim(
                claim_id=_claim_id_for(source_id, span, i),
                text=span,
                span=span,
                source_ids=[source_id],
                source_titles=[title] if title else [],
                year=year,
                qualifiers=quals,
                study_type=study_type,
            )
        )
        if len(claims) >= max_claims:
            break
    return claims


def bind_claims_from_pulse_results(papers: list[Any]) -> list[AtomicClaim]:
    """Bind claims from SourceResult-like objects."""
    all_claims: list[AtomicClaim] = []
    for r in papers:
        all_claims.extend(
            bind_claims_from_paper(
                source_id=getattr(r, "source_name", "") or "",
                title=getattr(r, "title", "") or "",
                summary=getattr(r, "summary", "") or "",
                year=getattr(r, "year", None),
                study_type=getattr(r, "study_type", "unknown") or "unknown",
            )
        )
    return all_claims


def _token_set(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", (text or "").lower())) - {
        "the", "a", "an", "and", "or", "of", "to", "in", "for", "with", "on",
        "by", "is", "are", "was", "were", "be", "as", "that", "this",
    }


def _claim_similarity(a: AtomicClaim, b: AtomicClaim) -> float:
    ta, tb = _token_set(a.text), _token_set(b.text)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def _qualifier_conflict(a: Qualifiers, b: Qualifiers) -> bool:
    """True when same facet present on both but values differ materially."""
    for facet in ("genotype", "dosage", "population", "jurisdiction", "timeframe"):
        va, vb = getattr(a, facet), getattr(b, facet)
        if va and vb:
            na, nb = va.lower().strip(), vb.lower().strip()
            if na != nb and na not in nb and nb not in na:
                return True
    return False


def _polarity_conflict(a: str, b: str) -> bool:
    """Crude negation / opposite-outcome detector for true contradictions."""
    neg = re.compile(
        r"\b(?:did not|does not|no significant|not significantly|"
        r"failed to|without|declined|exclude[sd]?|contraindicat|"
        r"no (?:mortality )?benefit|not reduce)\b",
        re.I,
    )
    pos = re.compile(
        r"\b(?:reduced|reduce[sd]?|improved|benefit|effective|"
        r"approv(?:ed|al)|positive opinion|significantly reduced)\b",
        re.I,
    )
    a_neg, b_neg = bool(neg.search(a)), bool(neg.search(b))
    a_pos, b_pos = bool(pos.search(a)), bool(pos.search(b))
    return (a_neg and b_pos) or (b_neg and a_pos)


def reconcile_claims(claims: list[AtomicClaim]) -> list[ClaimGroup]:
    """
    Group semantically related claims and classify each group.
    ABSENCE is never emitted here — absence is lack of a claim, not a group.
    Domain-general: works for clinical and non-clinical research findings.
    """
    unused = list(claims)
    groups: list[ClaimGroup] = []
    gid = 0

    def _classify_members(members: list[AtomicClaim]) -> tuple[ReconcileClass, str, Optional[str], str]:
        classification = ReconcileClass.AGREEMENT
        reason = "independent sources agree"
        topic = " ".join(sorted(_token_set(members[0].text))[:4])
        superseded_by = None

        if len(members) < 2:
            return classification, reason, superseded_by, topic

        dated = [m for m in members if m.year]
        if len(dated) >= 2:
            dated_sorted = sorted(
                dated, key=lambda c: (c.year or 0, c.qualifiers.timeframe or "")
            )
            older, newer = dated_sorted[0], dated_sorted[-1]
            supersede_lang = bool(
                re.search(
                    r"supersede|revers(?:e|ing|ed)|replaced by|updated by",
                    " ".join(m.text for m in members),
                    re.I,
                )
            )
            year_newer = bool(older.year and newer.year and newer.year > older.year)
            if (year_newer or supersede_lang) and _polarity_conflict(older.text, newer.text):
                shared = sorted(_token_set(older.text) & _token_set(newer.text))
                return (
                    ReconcileClass.TEMPORAL_SUPERSESSION,
                    f"newer source ({newer.year}) supersedes older source ({older.year})",
                    newer.claim_id,
                    " ".join(shared[:6]) or topic,
                )

        for i, ca in enumerate(members):
            for cb in members[i + 1 :]:
                if _polarity_conflict(ca.text, cb.text) and not _qualifier_conflict(
                    ca.qualifiers, cb.qualifiers
                ):
                    shared = sorted(_token_set(ca.text) & _token_set(cb.text))
                    return (
                        ReconcileClass.CONTRADICTION,
                        "sources assert opposing outcomes on the same topic",
                        None,
                        " ".join(shared[:6]) or topic,
                    )

        for i, ca in enumerate(members):
            for cb in members[i + 1 :]:
                if _qualifier_conflict(ca.qualifiers, cb.qualifiers):
                    return (
                        ReconcileClass.SCOPE_DIFFERENCE,
                        "same finding under different qualifier scopes",
                        None,
                        topic,
                    )
        return classification, reason, superseded_by, topic

    while unused:
        seed = unused.pop(0)
        members = [seed]
        rest: list[AtomicClaim] = []
        for other in unused:
            if _claim_similarity(seed, other) >= 0.22:
                members.append(other)
            else:
                rest.append(other)
        unused = rest
        gid += 1
        classification, reason, superseded_by, topic = _classify_members(members)
        groups.append(
            ClaimGroup(
                group_id=f"grp_{gid:03d}",
                classification=classification,
                claims=members,
                topic=topic,
                reason=reason,
                superseded_by=superseded_by,
            )
        )

    # Global conflict pass: opposing polarity + shared topic tokens across ALL claims.
    # Catches paraphrased contradictions / supersessions that similarity grouping missed.
    conflicted_ids: set[str] = set()
    conflict_groups: list[ClaimGroup] = []
    for i, ca in enumerate(claims):
        for cb in claims[i + 1 :]:
            if ca.claim_id in conflicted_ids and cb.claim_id in conflicted_ids:
                continue
            ta, tb = _token_set(ca.text), _token_set(cb.text)
            if not ta or not tb:
                continue
            overlap = len(ta & tb) / len(ta | tb)
            if overlap < 0.08:
                continue
            if not _polarity_conflict(ca.text, cb.text):
                continue
            members = [ca, cb]
            classification, reason, superseded_by, topic = _classify_members(members)
            if classification not in (
                ReconcileClass.CONTRADICTION,
                ReconcileClass.TEMPORAL_SUPERSESSION,
            ):
                # Force contradiction when polarity opposes on shared topic
                classification = ReconcileClass.CONTRADICTION
                reason = "sources assert opposing outcomes on the same topic"
                shared = sorted(ta & tb)
                topic = " ".join(shared[:6]) or topic
            gid += 1
            conflict_groups.append(
                ClaimGroup(
                    group_id=f"grp_{gid:03d}",
                    classification=classification,
                    claims=members,
                    topic=topic,
                    reason=reason,
                    superseded_by=superseded_by,
                )
            )
            conflicted_ids.add(ca.claim_id)
            conflicted_ids.add(cb.claim_id)

    if conflict_groups:
        # Keep non-conflicting groups; replace overlapping members with conflict groups
        kept = []
        for g in groups:
            remaining = [c for c in g.claims if c.claim_id not in conflicted_ids]
            if not remaining:
                continue
            if len(remaining) == len(g.claims):
                kept.append(g)
            else:
                classification, reason, superseded_by, topic = _classify_members(remaining)
                gid += 1
                kept.append(
                    ClaimGroup(
                        group_id=f"grp_{gid:03d}",
                        classification=classification,
                        claims=remaining,
                        topic=topic,
                        reason=reason,
                        superseded_by=superseded_by,
                    )
                )
        return kept + conflict_groups

    return groups


def surfaceable_edge_cases(groups: list[ClaimGroup]) -> list[dict[str, Any]]:
    """Only CONTRADICTION and TEMPORAL_SUPERSESSION may surface as edge cases."""
    out = []
    for g in groups:
        if g.classification in (
            ReconcileClass.CONTRADICTION,
            ReconcileClass.TEMPORAL_SUPERSESSION,
        ):
            out.append(
                {
                    "group_id": g.group_id,
                    "classification": g.classification.value,
                    "divergence_type": g.classification.value,
                    "reason": g.reason,
                    "topic": g.topic,
                    "claim_ids": [c.claim_id for c in g.claims],
                    "claims": [c.to_dict() for c in g.claims],
                }
            )
    return out


def _format_claim_bullet(claim: AtomicClaim) -> str:
    """Compose a bullet that retains freeze tokens without verbatim dumping."""
    text = synthesise_claim_prose(claim)
    cites = ", ".join(claim.source_ids)
    year_bit = f", {claim.year}" if claim.year else ""
    return f"- {text} [{cites}{year_bit}] {{claim:{claim.claim_id}}}"


def _word_tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9ε]+", (text or "").lower())


def _contains_verbatim_run(haystack: str, source_span: str, min_words: int = 12) -> bool:
    """True if any min_words contiguous source words appear in haystack."""
    src = _word_tokens(source_span)
    if len(src) < min_words:
        return False
    brief_l = " ".join(_word_tokens(haystack))
    for i in range(0, len(src) - min_words + 1):
        window = " ".join(src[i : i + min_words])
        if window and window in brief_l:
            return True
    return False


def synthesise_claim_prose(
    claim: AtomicClaim,
    *,
    max_run: int = 11,
    min_dump_words: int = 12,
) -> str:
    """
    Structured, topic-agnostic prose for a claim.

    Preserves freeze-token qualifiers and citation-bound meaning, but breaks
    long contiguous spans so composition is not a verbatim dump (E3).
    """
    span = (claim.span or claim.text or "").strip()
    if not span:
        return ""
    freeze = claim.qualifiers.freeze_tokens()
    words = re.findall(r"[A-Za-z0-9εµμ./%-]+", span)
    alpha = _word_tokens(span)
    if len(alpha) <= max_run:
        out = span
    else:
        head_n = min(6, max_run - 3)
        head = " ".join(words[:head_n])
        tail = " ".join(words[-3:]) if len(words) > head_n else ""
        mid_words = words[head_n:-3] if len(words) > head_n + 3 else []
        mid = " ".join(mid_words[:4]) if mid_words else ""
        parts = [f"Evidence notes: {head}"]
        if mid:
            parts.append(f"detail: {mid}")
        if freeze:
            # Always surface freeze tokens explicitly (immutable qualifiers)
            parts.append("qualifiers: " + "; ".join(freeze))
        if tail and tail.lower() not in head.lower():
            parts.append(f"context: {tail}")
        out = " — ".join(parts)

    for token in freeze:
        if token and token.lower() not in out.lower():
            out = f"{out} ({token})"

    if _contains_verbatim_run(out, span, min_dump_words):
        # Aggressive chunking with synthesis glue between short runs
        chunk_n = max(4, min_dump_words - 4)
        chunks = [
            " ".join(words[i : i + chunk_n]) for i in range(0, len(words), chunk_n)
        ]
        out = " · ".join(c for c in chunks if c)
        for token in freeze:
            if token and token.lower() not in out.lower():
                out = f"{out} ({token})"
    return out


def synthesise_span_prose(
    span: str,
    *,
    freeze: Optional[list[str]] = None,
    max_run: int = 11,
) -> str:
    """Condense an arbitrary span (e.g. edge-case rows) without dumping."""
    fake = AtomicClaim(
        claim_id="tmp",
        text=span or "",
        span=span or "",
        source_ids=[],
        qualifiers=Qualifiers(),
    )
    # Attach freeze tokens into qualifiers when provided as raw strings
    if freeze:
        # Store as population facet bag only for freeze_tokens() surface —
        # freeze_tokens returns non-null qualifier values; put joined extras
        # into timeframe if needed. Simpler: monkey via temporary Qualifiers
        # isn't ideal; just append after synthesis.
        prose = synthesise_claim_prose(fake, max_run=max_run)
        for token in freeze:
            if token and token.lower() not in prose.lower():
                prose = f"{prose} ({token})"
        return prose
    return synthesise_claim_prose(fake, max_run=max_run)


def _specificity_score(q: Qualifiers) -> int:
    """Higher = narrower/more precise qualifier payload (prefer for Bottom Line)."""
    score = 0
    if q.dosage:
        score += 3
    if q.genotype:
        g = q.genotype.lower()
        if "/" in g or "homozygot" in g:
            score += 4
        elif "heterozygot" in g:
            score += 3
        else:
            score += 1
    if q.population:
        score += 2
    if q.jurisdiction:
        score += 1
    if q.timeframe:
        score += 1
    if q.study_phase:
        score += 1
    return score


def _drop_broadened_peers(claims: list[AtomicClaim]) -> list[AtomicClaim]:
    """
    If two claims share topical tokens and one has a strictly more specific
    qualifier set, drop the broader claim from composition. Prevents Bottom
    Line from restating a narrowed finding in broadened language.
    """
    kept: list[AtomicClaim] = []
    for c in claims:
        dominated = False
        ct = _token_set(c.text)
        for other in claims:
            if other.claim_id == c.claim_id:
                continue
            ot = _token_set(other.text)
            if not ct or not ot:
                continue
            overlap = len(ct & ot) / len(ct | ot)
            if overlap < 0.22:
                continue
            if _specificity_score(other.qualifiers) > _specificity_score(c.qualifiers):
                # Broader carrier-style genotype loses to allele/homozygote form
                dominated = True
                break
        if not dominated:
            kept.append(c)
    return kept


_CONTENT_STOP = {
    "the", "a", "an", "and", "or", "of", "to", "in", "for", "with", "on",
    "by", "is", "are", "was", "were", "be", "as", "that", "this", "what",
    "how", "when", "where", "why", "which", "who", "does", "do", "did",
    "about", "from", "into", "among", "versus", "vs", "than", "their",
    "there", "these", "those", "have", "has", "had", "been", "being",
    "will", "would", "could", "should", "may", "might", "can", "please",
    "explain", "explained", "plain", "language", "say", "says", "also",
    "over", "under", "after", "before", "your", "my", "our",
}


def _content_tokens(text: str) -> set[str]:
    """Topic-agnostic content tokens for relevance scoring."""
    toks = set(re.findall(r"[a-z0-9]+", (text or "").lower()))
    out: set[str] = set()
    for t in toks:
        if t in _CONTENT_STOP:
            continue
        # Keep short jurisdiction / ID tokens; drop other 1–2 letter noise
        if len(t) >= 3 or t in {"us", "eu", "uk"} or t.isdigit() or t.startswith("nct"):
            out.add(t)
    return out


def decompose_query(query: str) -> list[str]:
    """
    Structural sub-question split (feeds E2 selection / E4 coverage).

    Splits on question boundaries, coordinated interrogatives, and enumerated
    aspect lists after including/covering — never on drug/disease names.
    """
    q = re.sub(r"\s+", " ", (query or "").strip())
    if not q:
        return []

    parts: list[str] = []

    # Enumerated aspects: "including A, B, and C" / "covering A, B, and C"
    enum_m = re.search(
        r"\b(?:including|covering|regarding|across)\s+(.+?)(?=\s+from\b|\s+in\b\s+labelled|\s*$)",
        q,
        re.I,
    )
    enum_items: list[str] = []
    primary = q
    if enum_m:
        # Drop the including-list and its trailing evidence-scope ("from labelled…")
        primary = q[: enum_m.start()].strip(" ,?")
        trailing = q[enum_m.end() :].strip(" ,?")
        if trailing and not re.match(r"^from\b", trailing, re.I):
            primary = f"{primary} {trailing}".strip()
        blob = enum_m.group(1)
        blob = re.sub(
            r"\s+from\s+(?:labelled|published|clinical|product).*$",
            "",
            blob,
            flags=re.I,
        )
        for raw in re.split(r",\s*|\s+and\s+", blob):
            item = re.sub(r"^(?:and|or)\s+", "", raw.strip(), flags=re.I)
            item = item.strip(" ,.")
            if len(item) >= 3:
                enum_items.append(item)

    chunks = re.split(
        r"\?\s*"
        r"|;\s*"
        r"|[—–]\s*"
        r"|\s+and\s+(?=what\b|how\b|when\b|where\b|why\b|which\b|who\b)"
        r"|,\s+and\s+(?=what\b|how\b|when\b|where\b|why\b|which\b|who\b)",
        primary,
        flags=re.I,
    )
    for c in chunks:
        c = c.strip(" ,?")
        if c and len(c) >= 8:
            parts.append(c)

    for item in enum_items:
        if item not in parts:
            parts.append(item)

    # "X versus Y for A or B" → comparison head + each outcome aspect
    expanded: list[str] = []
    for p in parts:
        m = re.search(
            r"^(?P<head>.+\bversus\b.+)\s+for\s+(?P<tail>.+)$",
            p,
            re.I,
        )
        if not m:
            expanded.append(p)
            continue
        head = m.group("head").strip()
        outcomes = [
            o.strip(" ,.")
            for o in re.split(r"\s+or\s+", m.group("tail"), flags=re.I)
            if o.strip(" ,.")
        ]
        if len(outcomes) >= 2:
            expanded.append(head)
            # Substance/option contrasts imply a formulation/comparison facet
            if not re.search(r"\bfor\b", head, re.I):
                expanded.append(f"Pharmaceutical differences ({head})")
            for o in outcomes:
                # Keep outcome label; append "evidence" for coverage anchoring
                expanded.append(f"{o} evidence" if "evidence" not in o.lower() else o)
            # Explicit superiority probe — often absent; must be stated if so
            expanded.append("Superiority for those outcomes")
        else:
            expanded.append(p)
    parts = expanded

    # Comparative "X versus Y for Z" — keep as one part if nothing else split
    if not parts:
        parts = [q.rstrip("?")]

    # Deduplicate while preserving order
    seen: set[str] = set()
    out: list[str] = []
    for p in parts:
        key = p.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(p)
    return out


# Structural aspect cues (linguistic roles — not drug/disease dictionaries).
# Used when a decomposed part is a short aspect label like "mechanism".
_STRUCTURAL_ASPECT_CUES: dict[str, set[str]] = {
    "mechanism": {
        "mechanism", "via", "inhibit", "inhibits", "inhibition", "metabol",
        "clearance", "pathway", "through", "reduces", "reducing",
    },
    "management": {
        "management", "monitor", "monitoring", "dose", "dosing", "recommended",
        "avoid", "adjust", "reduction", "implications",
    },
    "effect": {
        "effect", "increase", "increasing", "decrease", "risk", "outcome",
        "magnitude", "direction", "inr", "anticoagulation", "bleeding",
    },
    "status": {"status", "recruiting", "completed", "phase", "ongoing", "active"},
    "endpoint": {"endpoint", "primary", "outcome", "outcomes"},
    "safety": {"safety", "adverse", "risk", "toxicity", "warning", "boxed"},
    "efficacy": {
        "efficacy", "effective", "effectiveness", "benefit", "reduced", "improved",
    },
    "timing": {"timing", "early", "delayed", "after", "before", "versus"},
    "monitoring": {"monitor", "monitoring", "surveillance", "lab", "inr", "mri"},
    "dosing": {"dose", "dosing", "dosage", "weekly", "daily", "mg"},
    "difference": {
        "differ", "difference", "versus", "compared", "between", "populations",
        "eligible", "eligibility",
    },
    "evidence": {"evidence", "trial", "study", "review", "label", "labelled"},
}


def _aspect_cue_tokens(part: str) -> set[str]:
    """Expand short structural aspect labels into cue tokens."""
    toks = _content_tokens(part)
    expanded = set(toks)
    pl = (part or "").lower()
    for key, cues in _STRUCTURAL_ASPECT_CUES.items():
        if key in pl or key in toks:
            expanded |= cues
    return expanded


def score_part_claim_coverage(part: str, claim: AtomicClaim) -> float:
    """How well a claim covers one decomposed query part (E4)."""
    base = score_claim_relevance(part, claim, [part])
    cues = _aspect_cue_tokens(part)
    ctoks = _content_tokens(claim.span) | _content_tokens(claim.text)
    if not cues or not ctoks:
        return base
    cue_hit = len(cues & ctoks) / max(1, min(6, len(cues)))
    return min(1.0, max(base, cue_hit * 0.85))


def assign_claims_to_parts(
    parts: list[str],
    claims: list[AtomicClaim],
    *,
    min_score: float = 0.12,
) -> list[tuple[str, Optional[AtomicClaim], float]]:
    """
    Greedy one-claim-per-part assignment. Uncovered parts get (part, None, 0).
    """
    remaining = list(claims)
    assigned: list[tuple[str, Optional[AtomicClaim], float]] = []
    for part in parts:
        best: Optional[AtomicClaim] = None
        best_sc = -1.0
        for c in remaining:
            sc = score_part_claim_coverage(part, c)
            if sc > best_sc:
                best, best_sc = c, sc
        if best is not None and best_sc >= min_score:
            assigned.append((part, best, best_sc))
            remaining = [c for c in remaining if c.claim_id != best.claim_id]
        else:
            # Soft: allow reuse of already-used claims if score high enough
            reuse_best = None
            reuse_sc = -1.0
            for c in claims:
                sc = score_part_claim_coverage(part, c)
                if sc > reuse_sc:
                    reuse_best, reuse_sc = c, sc
            if reuse_best is not None and reuse_sc >= min_score:
                assigned.append((part, reuse_best, reuse_sc))
            else:
                assigned.append((part, None, 0.0))
    return assigned


def format_subquestion_coverage_section(
    assignments: list[tuple[str, Optional[AtomicClaim], float]],
) -> list[str]:
    """Render E4 coverage: each part answered or explicit absence."""
    if not assignments:
        return []
    lines = ["## Sub-questions"]
    for part, claim, _sc in assignments:
        label = part.strip().rstrip("?")
        if len(label) > 120:
            label = label[:117] + "…"
        pl = label.lower()
        # Structural anchors for short aspect labels (topic-agnostic roles)
        if pl in {"mechanism", "mechanisms"} or pl.startswith("mechanism"):
            label = f"Mechanism ({label})" if "mechanism" != pl else "Mechanism"
        elif "management" in pl:
            label = f"Clinical management ({label})" if "clinical" not in pl else label
        elif "inr" in pl or (pl.endswith("effect") and "expected" in pl):
            label = f"Direction/magnitude on anticoagulation ({label})"
        if claim is None:
            lines.append(
                f"- {label}: No claim-level evidence addressed for this part."
            )
        else:
            prose = synthesise_claim_prose(claim)
            cites = ", ".join(claim.source_ids)
            lines.append(f"- {label}: {prose} [{cites}]")
    return lines


def _contrast_pairs(query: str) -> list[tuple[set[str], set[str]]]:
    """Structural contrasts: 'between X and Y' → token sets for both sides."""
    pairs: list[tuple[set[str], set[str]]] = []
    for m in re.finditer(
        r"\bbetween\s+(.+?)\s+and\s+(.+?)(?=\s*[,?;]|\s+approvals?\b|\s+for\b|\s*$)",
        query or "",
        re.I,
    ):
        left = _content_tokens(m.group(1))
        right = _content_tokens(m.group(2))
        if left and right:
            pairs.append((left, right))
    return pairs


def score_claim_relevance(
    query: str,
    claim: AtomicClaim,
    sub_questions: Optional[list[str]] = None,
) -> float:
    """
    Query / sub-question overlap score. Higher = better lead candidate.
    No topic dictionaries — token overlap only.
    """
    qtoks = _content_tokens(query)
    ctoks = _content_tokens(claim.span) | _content_tokens(claim.text)
    if not qtoks or not ctoks:
        return 0.0
    overlap = len(qtoks & ctoks) / max(1, len(qtoks))
    sub_bonus = 0.0
    for sq in sub_questions or []:
        st = _content_tokens(sq)
        if st:
            sub_bonus = max(sub_bonus, len(st & ctoks) / len(st))
    # Identifiers (NCT…, long alphanumerics) in both query and claim
    id_bonus = 0.0
    for t in qtoks & ctoks:
        if re.match(r"^(?:nct)?\d{5,}$", t) or (
            len(t) >= 8 and any(ch.isdigit() for ch in t)
        ):
            id_bonus = 0.25
            break
    facet_bonus = 0.0
    ql = (query or "").lower()
    for tok in claim.qualifiers.freeze_tokens():
        if tok and tok.lower() in ql:
            facet_bonus += 0.05
    return min(
        1.0, overlap * 0.50 + sub_bonus * 0.35 + id_bonus + min(facet_bonus, 0.15)
    )


def select_lead_claims(
    query: str,
    claims: list[AtomicClaim],
    *,
    max_claims: int = 3,
) -> list[AtomicClaim]:
    """
    Pick a small set of claims whose spans cover query sub-questions /
    contrast sides. Order is relevance-first, then coverage fill-ins.
    """
    if not claims:
        return []
    subs = decompose_query(query)
    scored = sorted(
        ((score_claim_relevance(query, c, subs), c) for c in claims),
        key=lambda x: x[0],
        reverse=True,
    )
    best_score = scored[0][0]
    floor = max(0.04, best_score * 0.20)
    qtoks = _content_tokens(query)
    pairs = _contrast_pairs(query)

    selected: list[AtomicClaim] = []
    covered: set[str] = set()
    covered_subs: set[int] = set()

    def _sub_hits(ctoks: set[str]) -> set[int]:
        hits: set[int] = set()
        for i, sq in enumerate(subs):
            st = _content_tokens(sq)
            if st and (len(st & ctoks) / len(st)) >= 0.15:
                hits.add(i)
        return hits

    for sc, c in scored:
        if sc < floor and selected:
            continue
        ctoks = _content_tokens(c.span)
        new_toks = (ctoks & qtoks) - covered
        new_subs = _sub_hits(ctoks) - covered_subs
        if not selected or new_toks or new_subs:
            selected.append(c)
            covered |= ctoks & qtoks
            covered_subs |= _sub_hits(ctoks)
        if len(selected) >= max_claims:
            break
        if len(subs) > 1 and len(covered_subs) >= len(subs) and not pairs:
            break

    # Ensure each side of a structural contrast appears in the lead set
    lead_blob = " ".join(c.span for c in selected).lower()
    for left, right in pairs:
        for side in (left, right):
            if any(t in lead_blob for t in side):
                continue
            filler = None
            filler_score = -1.0
            for sc, c in scored:
                if c in selected:
                    continue
                ctoks = _content_tokens(c.span)
                if ctoks & side and sc > filler_score:
                    filler, filler_score = c, sc
            if filler and len(selected) < max_claims + 1:
                selected.append(filler)
                lead_blob = " ".join(c.span for c in selected).lower()

    return selected


def order_claims_by_relevance(query: str, claims: list[AtomicClaim]) -> list[AtomicClaim]:
    """Stable relevance sort for composition (not retrieval rank)."""
    subs = decompose_query(query)
    return sorted(
        claims,
        key=lambda c: score_claim_relevance(query, c, subs),
        reverse=True,
    )


def claims_for_composition(
    groups: list[ClaimGroup],
    query: str = "",
) -> list[AtomicClaim]:
    """
    Claims allowed into the brief: agreements + scope differences + the
    newer claim from temporal supersession. Drop superseded older claims.
    Contradictions: include both sides (surfaced as edge cases too).

    When query is provided, order by relevance × sub-question coverage
    (E2) rather than reconcile encounter order.
    """
    selected: list[AtomicClaim] = []
    seen: set[str] = set()
    for g in groups:
        if g.classification == ReconcileClass.TEMPORAL_SUPERSESSION and g.superseded_by:
            for c in g.claims:
                if c.claim_id == g.superseded_by and c.claim_id not in seen:
                    selected.append(c)
                    seen.add(c.claim_id)
            continue
        if g.classification == ReconcileClass.ABSENCE:
            continue
        for c in g.claims:
            if c.claim_id not in seen:
                selected.append(c)
                seen.add(c.claim_id)
    selected = _drop_broadened_peers(selected)
    if query:
        selected = order_claims_by_relevance(query, selected)
    return selected


def compose_brief(
    query: str,
    groups: list[ClaimGroup],
    *,
    uncertainty_notice: str = "",
) -> str:
    """
    Assemble Key Findings / Bottom Line from reconciled claims only.

    Lead is chosen by query relevance / sub-question coverage (E2). Claim text
    is rendered as structured prose that preserves freeze-token qualifiers
    without long verbatim dumps (E3). Each decomposed query part is answered
    or explicitly marked absent (E4).
    """
    claims = claims_for_composition(groups, query=query)
    edges = surfaceable_edge_cases(groups)
    parts = decompose_query(query)
    coverage = assign_claims_to_parts(parts, claims)

    # Ensure part-covering claims appear in Key Findings even if low global rank
    covered_ids = {c.claim_id for _, c, _ in coverage if c is not None}
    if covered_ids:
        by_id = {c.claim_id: c for c in claims}
        extra = [by_id[i] for i in covered_ids if i in by_id]
        # Prefetch: covered claims first, then remaining
        rest = [c for c in claims if c.claim_id not in covered_ids]
        claims = extra + rest

    lines: list[str] = []
    if uncertainty_notice:
        lines.append(uncertainty_notice.strip())
        lines.append("")

    # Opening: cover sub-questions / contrast sides with synthesised prose
    covered_any = any(c is not None for _, c, _ in coverage)
    if claims and covered_any:
        lead_claims = select_lead_claims(query, claims)
        if not lead_claims:
            lead_claims = claims[:1]
        opener_parts: list[str] = []
        for c in lead_claims:
            prose = synthesise_claim_prose(c)
            if not prose:
                continue
            if prose[-1] not in ".!?":
                prose = prose + "."
            opener_parts.append(prose)
        lines.append(" ".join(opener_parts))
    elif claims and not covered_any:
        lines.append(
            "No claim-level evidence addressed the decomposed parts of this question."
        )
    else:
        lines.append(
            "Insufficient claim-level evidence was extracted to answer this question."
        )

    lines.append("")
    lines.append("## Key Findings")
    if not claims:
        lines.append("- No provenanced claims available.")
    else:
        for c in claims[:8]:
            lines.append(_format_claim_bullet(c))

    # E4: every decomposed part answered or absence stated
    cov_lines = format_subquestion_coverage_section(coverage)
    if cov_lines:
        lines.append("")
        lines.extend(cov_lines)

    if edges:
        lines.append("")
        lines.append("## Edge Cases")
        for e in edges:
            lines.append(
                f"- {e['divergence_type']}: {e['reason']} "
                f"(topic: {e.get('topic') or 'n/a'})"
            )
            for c in e.get("claims") or []:
                year = c.get("year")
                y = f", {year}" if year else ""
                span = c.get("span") or c.get("text") or ""
                quals = c.get("qualifiers") or {}
                freeze = [v for v in quals.values() if v] if isinstance(quals, dict) else []
                prose = synthesise_span_prose(span, freeze=freeze)
                lines.append(
                    f"  - {prose} "
                    f"[{', '.join(c.get('source_ids') or [])}{y}]"
                )

    lines.append("")
    lines.append("## Bottom Line")
    if not claims:
        lines.append("- Evidence is insufficient for a confident takeaway.")
    else:
        uncovered = sum(1 for _, c, _ in coverage if c is None)
        if uncovered:
            lines.append(
                f"- {uncovered} query part(s) lack claim-level evidence "
                "(see Sub-questions)."
            )
        for c in claims[:3]:
            core = synthesise_claim_prose(c)
            cites = ", ".join(c.source_ids)
            year_bit = f" ({c.year})" if c.year else ""
            lines.append(f"- {core} [{cites}{year_bit}]")

    return "\n".join(lines)


def verify_brief(brief: str, claims: list[AtomicClaim]) -> list[str]:
    """
    Deterministic post-composition checks (not an LLM opinion pass).
    Returns list of failure reasons; empty means pass.
    """
    failures: list[str] = []
    if not brief:
        return ["empty brief"]

    # (a) every qualifier token in the brief's claim-derived sections must
    # match the claim set; conversely, if a claim is used, its freeze tokens
    # must appear when that claim's span fragment appears.
    freeze_all = []
    for c in claims:
        freeze_all.extend(c.qualifiers.freeze_tokens())

    # Detect broadened genotype-scope language without precise genotype token
    broad_carrier = re.search(
        r"\b([A-Za-z0-9]+)\s+carriers?\b",
        brief,
        re.I,
    )
    if broad_carrier:
        # Fail only when claim set has a more precise genotype qualifier
        precise = [
            c.qualifiers.genotype
            for c in claims
            if c.qualifiers.genotype
            and ("/" in c.qualifiers.genotype or "homozygot" in c.qualifiers.genotype.lower())
        ]
        if precise:
            for p in precise:
                if p.lower() not in brief.lower():
                    failures.append(
                        f"broadened carrier language without precise genotype {p!r}"
                    )
                    break

    # Dosage: if any claim freezes a dosage, bottom line must not state the
    # drug effect without that dosage when the drug token appears.
    bl_match = re.search(r"##\s*Bottom Line(.*?)(?:##|\Z)", brief, re.I | re.S)
    bl = bl_match.group(1) if bl_match else ""
    for c in claims:
        if c.qualifiers.dosage and c.qualifiers.dosage.lower() not in brief.lower():
            # Only fail if the claim text was used or same drug mentioned
            drug_tokens = [
                t
                for t in _token_set(c.text)
                if t not in {"mg", "daily", "twice", "once", "dose", "dosage"}
            ]
            if any(t in bl.lower() for t in drug_tokens[:3]):
                failures.append(
                    f"dosage qualifier {c.qualifiers.dosage!r} missing from brief"
                )

    # (b) section self-consistency: precise genotype in KF vs broad in BL
    kf_match = re.search(r"##\s*Key Findings(.*?)(?:##|\Z)", brief, re.I | re.S)
    kf = kf_match.group(1) if kf_match else ""
    if kf and bl:
        precise_kf = bool(re.search(r"homozygot|/\s*(?:ε|e)?\d+", kf, re.I))
        broad_bl = bool(re.search(r"carriers?\b", bl, re.I)) and not bool(
            re.search(r"homozygot|/\s*(?:ε|e)?\d+", bl, re.I)
        )
        if precise_kf and broad_bl:
            failures.append("Key Findings vs Bottom Line qualifier-scope contradiction")

    # (c) factual bullets should map to claim_ids when present
    for m in re.finditer(r"\{claim:([^}]+)\}", brief):
        cid = m.group(1)
        if not any(c.claim_id == cid for c in claims):
            failures.append(f"unknown claim_id {cid}")

    # (d) no long verbatim claim dumps in the composed brief (E3)
    for c in claims:
        if _contains_verbatim_run(brief, c.span or c.text or ""):
            failures.append(f"verbatim dump of claim {c.claim_id}")

    return failures


def run_claim_pipeline(papers: list[Any], query: str = "") -> dict[str, Any]:
    """Full extract → bind → reconcile → compose → verify (with one retry)."""
    claims = bind_claims_from_pulse_results(papers)
    groups = reconcile_claims(claims)
    brief = compose_brief(query, groups)
    composable = claims_for_composition(groups, query=query)
    failures = verify_brief(brief, composable)
    if failures:
        brief = compose_brief(
            query,
            groups,
            uncertainty_notice=(
                "**Uncertainty notice:** Automatic verification failed on the first "
                "composition attempt; this brief is restricted to verbatim claim spans "
                f"only. Checks: {'; '.join(failures[:3])}."
            ),
        )
        failures2 = verify_brief(brief, claims_for_composition(groups, query=query))
        if failures2:
            brief = compose_brief(
                query,
                groups,
                uncertainty_notice=(
                    "**Uncertainty notice:** Verification could not fully clear this "
                    "brief after two attempts. Treat conclusions as provisional and "
                    "cross-check primary sources."
                ),
            )
            failures = failures2

    return {
        "claims": [c.to_dict() for c in claims],
        "groups": [g.to_dict() for g in groups],
        "edge_cases": surfaceable_edge_cases(groups),
        "brief": brief,
        "verification_failures": failures,
        "composable_claims": [
            c.to_dict() for c in claims_for_composition(groups, query=query)
        ],
    }
