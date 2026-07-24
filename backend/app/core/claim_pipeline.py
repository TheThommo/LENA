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
    if len(sent) < 30 or len(sent) > 600:
        return False
    return bool(
        re.search(
            r"(?:found|showed|demonstrated|reported|observed|measured|"
            r"estimated|associated|reduced|increased|decreased|improved|"
            r"exclude[sd]?|approv(?:ed|al)|authori[sz]ation|contraindicat|"
            r"recommend|significant|compared|versus|vs\.?|dose|label|"
            r"indicat|risk|mortality|hospitalisation|hospitalization|"
            r"supersede|declined|positive opinion|benefit|conclude[sd]?|"
            r"suggest(?:s|ed)?|indicate[sd]?|reveal(?:s|ed)?|confirm(?:s|ed)?|"
            r"prevalence|incidence|effective|efficacy|correlated|"
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
    """Compose a bullet that retains every frozen qualifier token."""
    text = claim.span.strip()
    # Ensure freeze tokens appear (span already contains them; guard against trim)
    for token in claim.qualifiers.freeze_tokens():
        if token.lower() not in text.lower():
            text = f"{text} ({token})"
    cites = ", ".join(claim.source_ids)
    year_bit = f", {claim.year}" if claim.year else ""
    return f"- {text} [{cites}{year_bit}] {{claim:{claim.claim_id}}}"


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


def claims_for_composition(groups: list[ClaimGroup]) -> list[AtomicClaim]:
    """
    Claims allowed into the brief: agreements + scope differences + the
    newer claim from temporal supersession. Drop superseded older claims.
    Contradictions: include both sides (surfaced as edge cases too).
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
    return _drop_broadened_peers(selected)


def compose_brief(
    query: str,
    groups: list[ClaimGroup],
    *,
    uncertainty_notice: str = "",
) -> str:
    """
    Assemble Key Findings / Bottom Line from reconciled claims only.
    No paraphrase that can drop or broaden qualifiers — span text is used.
    """
    claims = claims_for_composition(groups)
    edges = surfaceable_edge_cases(groups)

    lines: list[str] = []
    if uncertainty_notice:
        lines.append(uncertainty_notice.strip())
        lines.append("")

    # Opening: first high-signal claim, qualifiers intact
    if claims:
        opener = claims[0].span.strip()
        lines.append(opener)
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
                lines.append(
                    f"  - {c.get('span') or c.get('text')} "
                    f"[{', '.join(c.get('source_ids') or [])}{y}]"
                )

    lines.append("")
    lines.append("## Bottom Line")
    if not claims:
        lines.append("- Evidence is insufficient for a confident takeaway.")
    else:
        # Bottom line uses the same claim spans — never a broadened rewrite
        for c in claims[:3]:
            qbits = c.qualifiers.freeze_tokens()
            core = c.span.strip()
            if qbits:
                # Reinforce that qualifiers are load-bearing
                missing = [t for t in qbits if t.lower() not in core.lower()]
                if missing:
                    core = f"{core} ({'; '.join(missing)})"
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

    return failures


def run_claim_pipeline(papers: list[Any], query: str = "") -> dict[str, Any]:
    """Full extract → bind → reconcile → compose → verify (with one retry)."""
    claims = bind_claims_from_pulse_results(papers)
    groups = reconcile_claims(claims)
    brief = compose_brief(query, groups)
    failures = verify_brief(brief, claims_for_composition(groups))
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
        failures2 = verify_brief(brief, claims_for_composition(groups))
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
        "composable_claims": [c.to_dict() for c in claims_for_composition(groups)],
    }
