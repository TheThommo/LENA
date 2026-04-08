"""
Search Models

Represents searches and search results in the LENA platform.
Core data models for the clinical research search engine.
"""

from uuid import UUID
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from app.models.enums import PersonaType, SearchSource, PulseStatus


class SearchBase(BaseModel):
    """Base fields for search operations."""
    query: str = Field(..., min_length=1, max_length=2000)
    persona_type: PersonaType = PersonaType.GENERAL
    source_filter: Optional[List[SearchSource]] = None


class SearchCreate(SearchBase):
    """Fields required to create a search."""
    session_id: UUID
    user_id: Optional[UUID] = None
    tenant_id: UUID


class Search(SearchBase):
    """Full search record from database."""
    id: UUID
    session_id: UUID
    user_id: Optional[UUID] = None
    tenant_id: UUID
    created_at: datetime
    # query_vector: Optional[List[float]] = None  # pgvector future feature

    class Config:
        from_attributes = True


class SearchResultBase(BaseModel):
    """Base fields for search result operations."""
    source_name: SearchSource
    title: str = Field(..., min_length=1, max_length=1000)
    authors: Optional[str] = Field(None, max_length=2000)
    year: Optional[int] = Field(None, ge=1900, le=2100)
    doi: Optional[str] = Field(None, max_length=100)
    pmid: Optional[str] = Field(None, max_length=50)
    url: Optional[str] = Field(None, max_length=500)
    abstract: Optional[str] = Field(None, max_length=5000)
    relevance_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    pulse_status: PulseStatus = PulseStatus.PENDING


class SearchResultCreate(SearchResultBase):
    """Fields required to create a search result."""
    search_id: UUID


class SearchResult(SearchResultBase):
    """Full search result record from database."""
    id: UUID
    search_id: UUID
    created_at: datetime
    # full_text_vector: Optional[List[float]] = None  # pgvector future feature

    class Config:
        from_attributes = True


class SearchWithResults(Search):
    """Search with its results."""
    results: List[SearchResult] = []
