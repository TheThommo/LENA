"""
ClinicalTrials.gov API v2 Service

The v2 API is free, no API key required.
Docs: https://clinicaltrials.gov/data-api/api

Rate limits: 500 requests per minute (very generous)
"""

import httpx
from typing import Optional
from dataclasses import dataclass

BASE_URL = "https://clinicaltrials.gov/api/v2"


@dataclass
class ClinicalTrial:
    nct_id: str
    title: str
    status: str
    phase: Optional[str]
    conditions: list[str]
    interventions: list[str]
    start_date: Optional[str]
    completion_date: Optional[str]
    enrollment: Optional[int]
    summary: str
    url: str


async def search_trials(
    query: str,
    max_results: int = 10,
    status_filter: Optional[str] = None,
) -> list[ClinicalTrial]:
    """
    Search ClinicalTrials.gov for studies.

    Args:
        query: Search condition or keyword
        max_results: Number of results (max 100)
        status_filter: Optional filter like "RECRUITING", "COMPLETED"

    Returns:
        List of ClinicalTrial objects
    """
    params = {
        "query.term": query,
        "pageSize": min(max_results, 100),
        "format": "json",
    }

    if status_filter:
        params["filter.overallStatus"] = status_filter

    # Request specific fields to keep response lean
    params["fields"] = ",".join([
        "NCTId", "BriefTitle", "OverallStatus", "Phase",
        "Condition", "InterventionName", "StartDate",
        "CompletionDate", "EnrollmentCount", "BriefSummary",
    ])

    headers = {
        "User-Agent": "LENA-Research-Agent/1.0",
        "Accept": "application/json",
    }

    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        response = await client.get(f"{BASE_URL}/studies", params=params, headers=headers)
        response.raise_for_status()
        data = response.json()

    trials = []
    for study in data.get("studies", []):
        protocol = study.get("protocolSection", {})
        id_module = protocol.get("identificationModule", {})
        status_module = protocol.get("statusModule", {})
        design_module = protocol.get("designModule", {})
        conditions_module = protocol.get("conditionsModule", {})
        interventions_module = protocol.get("armsInterventionsModule", {})
        description_module = protocol.get("descriptionModule", {})

        nct_id = id_module.get("nctId", "")

        # Extract interventions
        intervention_names = []
        for interv in interventions_module.get("interventions", []):
            name = interv.get("name", "")
            if name:
                intervention_names.append(name)

        trials.append(ClinicalTrial(
            nct_id=nct_id,
            title=id_module.get("briefTitle", "No title"),
            status=status_module.get("overallStatus", "Unknown"),
            phase=",".join(design_module.get("phases", [])) or None,
            conditions=conditions_module.get("conditions", []),
            interventions=intervention_names,
            start_date=status_module.get("startDateStruct", {}).get("date"),
            completion_date=status_module.get("completionDateStruct", {}).get("date"),
            enrollment=design_module.get("enrollmentInfo", {}).get("count"),
            summary=description_module.get("briefSummary", ""),
            url=f"https://clinicaltrials.gov/study/{nct_id}",
        ))

    return trials


async def test_connection() -> dict:
    """Test the ClinicalTrials.gov API connection."""
    try:
        trials = await search_trials("diabetes type 2", max_results=3)
        return {
            "source": "ClinicalTrials.gov",
            "status": "connected",
            "test_query": "diabetes type 2",
            "results_found": len(trials),
            "sample_title": trials[0].title if trials else "N/A",
            "sample_status": trials[0].status if trials else "N/A",
            "api_key_required": False,
        }
    except Exception as e:
        return {
            "source": "ClinicalTrials.gov",
            "status": "error",
            "error": str(e),
        }
