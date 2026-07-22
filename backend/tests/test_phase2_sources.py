"""
Phase-2 source integration smoke tests (mocked HTTP).

Checklist:
1. biorxiv scored + preprint flag
2. chembl enrichment (not in PULSE map as scored-only... chembl is enrichment)
3. opentargets enrichment
4. synapse fail-loud without token
5. consensus fail-loud without key + scored map entry
6. biorender auth_required when no token
7. owkin dormant when OWKIN_ENABLED=false
Baseline: existing 11 ALL_SOURCES still present.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.pulse_engine import (
    EVIDENCE_WEIGHTS,
    SOURCE_EVIDENCE_DEFAULTS,
    SourceResult,
    ValidationStatus,
    run_pulse_validation,
)
from app.core.source_keys import MissingConsensusApiKeyError, MissingSynapseApiTokenError
from app.services.search_orchestrator import (
    ALL_SOURCES,
    ENRICHMENT_SOURCES,
    SOURCE_QUERY_MAP,
)


CORE_11 = {
    "pubmed", "clinical_trials", "cochrane", "who_iris", "cdc", "openalex",
    "semantic_scholar", "europe_pmc", "dailymed", "ods_dsld", "openfda",
}


def test_baseline_11_sources_unchanged():
    assert CORE_11.issubset(set(ALL_SOURCES))
    for name in CORE_11:
        assert name in SOURCE_QUERY_MAP


def test_phase2_scored_sources_wired():
    assert "biorxiv" in ALL_SOURCES
    assert "consensus" in ALL_SOURCES
    assert "biorxiv" in SOURCE_QUERY_MAP
    assert "consensus" in SOURCE_QUERY_MAP
    for name in ENRICHMENT_SOURCES:
        assert name not in ALL_SOURCES  # enrichment must not enter scored list


def test_preprint_weight_below_case_report():
    assert "preprint" in EVIDENCE_WEIGHTS
    assert EVIDENCE_WEIGHTS["preprint"] < EVIDENCE_WEIGHTS["case_report"]
    assert EVIDENCE_WEIGHTS["preprint"] > EVIDENCE_WEIGHTS["editorial"]
    # Existing weights untouched
    assert EVIDENCE_WEIGHTS["systematic_review"] == 1.5
    assert EVIDENCE_WEIGHTS["rct"] == 1.3
    assert SOURCE_EVIDENCE_DEFAULTS["biorxiv"] == "preprint"


@pytest.mark.asyncio
async def test_preprint_only_never_validated():
    results = {
        "biorxiv": [
            SourceResult(
                source_name="biorxiv",
                title="CRISPR preprint A",
                summary="We found that CRISPR editing reduced disease markers in mice.",
                is_preprint=True,
                study_type="preprint",
            ),
            SourceResult(
                source_name="biorxiv",
                title="CRISPR preprint B",
                summary="We found that CRISPR editing reduced disease markers in a murine model.",
                is_preprint=True,
                study_type="preprint",
            ),
        ],
    }
    # Pad with another preprint-labelled source to force agreement path
    results["openalex"] = [
        SourceResult(
            source_name="openalex",
            title="Related preprint mirror",
            summary="Preprint: CRISPR editing reduced disease markers.",
            is_preprint=True,
            study_type="preprint",
        ),
    ]
    report = await run_pulse_validation("CRISPR disease markers", results)
    assert report.status != ValidationStatus.VALIDATED


@pytest.mark.asyncio
async def test_chembl_search_mocked():
    from app.services import chembl

    fake = {
        "molecules": [
            {
                "molecule_chembl_id": "CHEMBL25",
                "pref_name": "ASPIRIN",
                "molecule_type": "Small molecule",
                "max_phase": 4,
                "molecule_structures": {"canonical_smiles": "CC(=O)Oc1ccccc1C(=O)O"},
                "molecule_properties": {"full_molformula": "C9H8O4"},
            }
        ]
    }
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = fake
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.get = AsyncMock(return_value=mock_resp)

    with patch("app.services.chembl.httpx.AsyncClient", return_value=mock_client):
        rows = await chembl.search_chembl("aspirin", max_results=3)
    assert rows and rows[0].chembl_id == "CHEMBL25"


@pytest.mark.asyncio
async def test_synapse_fail_loud_without_token():
    from app.services import synapse
    from app.core import config as cfg

    with patch.object(cfg.settings, "synapse_api_token", None):
        with pytest.raises(MissingSynapseApiTokenError):
            await synapse.search_synapse("alzheimers")


@pytest.mark.asyncio
async def test_consensus_fail_loud_without_key():
    from app.services import consensus_api
    from app.core import config as cfg

    with patch.object(cfg.settings, "consensus_api_key", None):
        with pytest.raises(MissingConsensusApiKeyError):
            await consensus_api.search_consensus("magnesium sleep")


@pytest.mark.asyncio
async def test_biorender_auth_required_without_token():
    from app.services import biorender
    from app.core import config as cfg

    with patch.object(cfg.settings, "biorender_access_token", None):
        figures, meta = await biorender.search_biorender("neuron synapse")
    assert figures == []
    assert meta.get("auth_required") is True


@pytest.mark.asyncio
async def test_owkin_dormant_when_disabled():
    from app.services import owkin
    from app.core import config as cfg

    with patch.object(cfg.settings, "owkin_enabled", False):
        rows = await owkin.search_owkin("glioblastoma pathology")
    assert rows == []


@pytest.mark.asyncio
async def test_enrichment_isolation_does_not_raise():
    from app.services.search_orchestrator import search_enrichment_sources

    # Synapse will fail loud internally but enrichment wrapper must catch
    payload, errors = await search_enrichment_sources(
        "aspirin COX2", persona="pharmacist", include_owkin=False,
    )
    assert "chembl" in payload
    assert "opentargets" in payload
    assert "owkin" in payload
    assert payload["owkin"] == []
