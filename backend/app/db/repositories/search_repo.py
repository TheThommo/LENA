"""
Search Repository

CRUD operations for searches and search results.
Core data access layer for the clinical research search engine.
"""

from uuid import UUID
from typing import Optional, List
from app.db.supabase import get_supabase_client, get_supabase_admin_client
from app.models import (
    Search,
    SearchCreate,
    SearchResult,
    SearchResultCreate,
    SearchWithResults,
)


class SearchRepository:
    """Repository for search operations."""

    @staticmethod
    async def create(search_create: SearchCreate) -> Optional[Search]:
        """Create a new search."""
        try:
            client = get_supabase_client()
            response = (
                client.table("searches")
                .insert(
                    {
                        "query": search_create.query,
                        "session_id": str(search_create.session_id),
                        "user_id": str(search_create.user_id)
                        if search_create.user_id
                        else None,
                        "tenant_id": str(search_create.tenant_id),
                        "persona_type": search_create.persona_type.value,
                        "source_filter": search_create.source_filter,
                    }
                )
                .execute()
            )
            if response.data and len(response.data) > 0:
                return Search(**response.data[0])
            return None
        except Exception as e:
            print(f"Error creating search: {e}")
            return None

    @staticmethod
    async def get_by_id(search_id: UUID) -> Optional[Search]:
        """Get a search by ID."""
        try:
            client = get_supabase_client()
            response = (
                client.table("searches").select("*").eq("id", str(search_id)).execute()
            )
            if response.data and len(response.data) > 0:
                return Search(**response.data[0])
            return None
        except Exception as e:
            print(f"Error fetching search: {e}")
            return None

    @staticmethod
    async def get_by_session_id(session_id: UUID) -> List[Search]:
        """Get all searches in a session."""
        try:
            client = get_supabase_client()
            response = (
                client.table("searches")
                .select("*")
                .eq("session_id", str(session_id))
                .order("created_at", desc=True)
                .execute()
            )
            return [Search(**row) for row in response.data] if response.data else []
        except Exception as e:
            print(f"Error fetching session searches: {e}")
            return []

    @staticmethod
    async def get_by_user_id(user_id: UUID, limit: int = 50) -> List[Search]:
        """Get recent searches for a user."""
        try:
            client = get_supabase_client()
            response = (
                client.table("searches")
                .select("*")
                .eq("user_id", str(user_id))
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            return [Search(**row) for row in response.data] if response.data else []
        except Exception as e:
            print(f"Error fetching user searches: {e}")
            return []

    @staticmethod
    async def get_by_tenant_id(tenant_id: UUID, limit: int = 100) -> List[Search]:
        """Get recent searches for a tenant."""
        try:
            client = get_supabase_client()
            response = (
                client.table("searches")
                .select("*")
                .eq("tenant_id", str(tenant_id))
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            return [Search(**row) for row in response.data] if response.data else []
        except Exception as e:
            print(f"Error fetching tenant searches: {e}")
            return []

    @staticmethod
    async def get_with_results(search_id: UUID) -> Optional[SearchWithResults]:
        """Get a search with all its results."""
        try:
            # Fetch the search
            search = await SearchRepository.get_by_id(search_id)
            if not search:
                return None

            # Fetch the results
            results = await SearchResultRepository.get_by_search_id(search_id)

            return SearchWithResults(**search.model_dump(), results=results)
        except Exception as e:
            print(f"Error fetching search with results: {e}")
            return None


class SearchResultRepository:
    """Repository for search result operations."""

    @staticmethod
    async def create(
        search_result_create: SearchResultCreate,
    ) -> Optional[SearchResult]:
        """Create a new search result."""
        try:
            client = get_supabase_client()
            response = (
                client.table("search_results")
                .insert(
                    {
                        "search_id": str(search_result_create.search_id),
                        "source_name": search_result_create.source_name.value,
                        "title": search_result_create.title,
                        "authors": search_result_create.authors,
                        "year": search_result_create.year,
                        "doi": search_result_create.doi,
                        "pmid": search_result_create.pmid,
                        "url": search_result_create.url,
                        "abstract": search_result_create.abstract,
                        "relevance_score": search_result_create.relevance_score,
                        "pulse_status": search_result_create.pulse_status.value,
                    }
                )
                .execute()
            )
            if response.data and len(response.data) > 0:
                return SearchResult(**response.data[0])
            return None
        except Exception as e:
            print(f"Error creating search result: {e}")
            return None

    @staticmethod
    async def create_batch(
        search_results: List[SearchResultCreate],
    ) -> List[SearchResult]:
        """Create multiple search results in one operation."""
        try:
            client = get_supabase_client()
            insert_data = [
                {
                    "search_id": str(result.search_id),
                    "source_name": result.source_name.value,
                    "title": result.title,
                    "authors": result.authors,
                    "year": result.year,
                    "doi": result.doi,
                    "pmid": result.pmid,
                    "url": result.url,
                    "abstract": result.abstract,
                    "relevance_score": result.relevance_score,
                    "pulse_status": result.pulse_status.value,
                }
                for result in search_results
            ]
            response = client.table("search_results").insert(insert_data).execute()
            return (
                [SearchResult(**row) for row in response.data]
                if response.data
                else []
            )
        except Exception as e:
            print(f"Error creating search results batch: {e}")
            return []

    @staticmethod
    async def get_by_id(result_id: UUID) -> Optional[SearchResult]:
        """Get a search result by ID."""
        try:
            client = get_supabase_client()
            response = (
                client.table("search_results")
                .select("*")
                .eq("id", str(result_id))
                .execute()
            )
            if response.data and len(response.data) > 0:
                return SearchResult(**response.data[0])
            return None
        except Exception as e:
            print(f"Error fetching search result: {e}")
            return None

    @staticmethod
    async def get_by_search_id(search_id: UUID) -> List[SearchResult]:
        """Get all results for a search."""
        try:
            client = get_supabase_client()
            response = (
                client.table("search_results")
                .select("*")
                .eq("search_id", str(search_id))
                .order("relevance_score", desc=True)
                .execute()
            )
            return (
                [SearchResult(**row) for row in response.data]
                if response.data
                else []
            )
        except Exception as e:
            print(f"Error fetching search results: {e}")
            return []

    @staticmethod
    async def get_by_source(search_id: UUID, source_name: str) -> List[SearchResult]:
        """Get all results from a specific source for a search."""
        try:
            client = get_supabase_client()
            response = (
                client.table("search_results")
                .select("*")
                .eq("search_id", str(search_id))
                .eq("source_name", source_name)
                .execute()
            )
            return (
                [SearchResult(**row) for row in response.data]
                if response.data
                else []
            )
        except Exception as e:
            print(f"Error fetching results by source: {e}")
            return []

    @staticmethod
    async def get_by_pmid(pmid: str) -> List[SearchResult]:
        """Get all search results with a specific PMID."""
        try:
            client = get_supabase_client()
            response = (
                client.table("search_results")
                .select("*")
                .eq("pmid", pmid)
                .execute()
            )
            return (
                [SearchResult(**row) for row in response.data]
                if response.data
                else []
            )
        except Exception as e:
            print(f"Error fetching results by PMID: {e}")
            return []

    @staticmethod
    async def update_pulse_status(result_id: UUID, pulse_status: str) -> Optional[SearchResult]:
        """Update the PULSE validation status for a result."""
        try:
            client = get_supabase_client()
            response = (
                client.table("search_results")
                .update({"pulse_status": pulse_status})
                .eq("id", str(result_id))
                .execute()
            )
            if response.data and len(response.data) > 0:
                return SearchResult(**response.data[0])
            return None
        except Exception as e:
            print(f"Error updating PULSE status: {e}")
            return None
