"""
ChEMBL compound / molecule search.

NOT scored by PULSE — enrichment "Compound Data" only.
API: https://www.ebi.ac.uk/chembl/api/data/ (no key)
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.core.logging import get_logger

logger = get_logger("lena.sources.chembl")

BASE_URL = "https://www.ebi.ac.uk/chembl/api/data"


@dataclass
class ChemblCompound:
    chembl_id: str
    name: str
    max_phase: Optional[float]
    molecule_type: Optional[str]
    smiles: Optional[str]
    formula: Optional[str]
    url: str
    summary: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError, httpx.HTTPStatusError)),
)
async def search_chembl(query: str, max_results: int = 8) -> list[ChemblCompound]:
    """Search ChEMBL molecules by free text / synonym."""
    params = {
        "q": query,
        "limit": min(max_results, 20),
        "format": "json",
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(f"{BASE_URL}/molecule/search", params=params)
        response.raise_for_status()
        data = response.json()

    compounds: list[ChemblCompound] = []
    molecules = data.get("molecules") or []
    for row in molecules:
        chembl_id = row.get("molecule_chembl_id") or ""
        if not chembl_id:
            continue
        prefs = row.get("pref_name") or chembl_id
        structs = row.get("molecule_structures") or {}
        props = row.get("molecule_properties") or {}
        max_phase = row.get("max_phase")
        mol_type = row.get("molecule_type")
        smiles = structs.get("canonical_smiles")
        formula = props.get("full_molformula")
        summary_parts = [f"ChEMBL ID {chembl_id}"]
        if mol_type:
            summary_parts.append(f"type={mol_type}")
        if max_phase is not None:
            summary_parts.append(f"max_phase={max_phase}")
        if formula:
            summary_parts.append(f"formula={formula}")
        compounds.append(
            ChemblCompound(
                chembl_id=chembl_id,
                name=prefs,
                max_phase=float(max_phase) if max_phase is not None else None,
                molecule_type=mol_type,
                smiles=smiles,
                formula=formula,
                url=f"https://www.ebi.ac.uk/chembl/compound_report_card/{chembl_id}/",
                summary="; ".join(summary_parts),
            )
        )
        if len(compounds) >= max_results:
            break
    return compounds
