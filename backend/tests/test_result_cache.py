"""
Tests for Result Cache Service

Tests in-memory caching with TTL and size limits.

Run with: pytest tests/test_result_cache.py -v
"""

import pytest
import time
from app.services.result_cache import (
    cache_result,
    get_cached_result,
    clear_cache,
    get_cache_stats,
    _make_cache_key,
)


class TestCacheKey:
    """Test cache key generation."""

    def test_cache_key_deterministic(self):
        """Same parameters should generate same key."""
        key1 = _make_cache_key("heart failure", ["pubmed", "cochrane"], True)
        key2 = _make_cache_key("heart failure", ["pubmed", "cochrane"], True)
        assert key1 == key2

    def test_cache_key_different_queries(self):
        """Different queries should generate different keys."""
        key1 = _make_cache_key("heart failure", ["pubmed"], True)
        key2 = _make_cache_key("diabetes management", ["pubmed"], True)
        assert key1 != key2

    def test_cache_key_different_sources(self):
        """Different sources should generate different keys."""
        key1 = _make_cache_key("heart failure", ["pubmed"], True)
        key2 = _make_cache_key("heart failure", ["cochrane"], True)
        assert key1 != key2

    def test_cache_key_source_order_independent(self):
        """Source order shouldn't matter (sorted)."""
        key1 = _make_cache_key("heart failure", ["pubmed", "cochrane"], True)
        key2 = _make_cache_key("heart failure", ["cochrane", "pubmed"], True)
        assert key1 == key2

    def test_cache_key_alt_medicine_toggle(self):
        """Alt medicine toggle should affect key."""
        key1 = _make_cache_key("turmeric", sources=None, include_alt_medicine=True)
        key2 = _make_cache_key("turmeric", sources=None, include_alt_medicine=False)
        assert key1 != key2

    def test_cache_key_none_sources(self):
        """None sources should work."""
        key = _make_cache_key("heart failure", sources=None, include_alt_medicine=True)
        assert key


class TestCacheStorage:
    """Test storing and retrieving cached results."""

    def test_cache_and_retrieve(self):
        """Store result and retrieve it."""
        query = "heart failure treatment"
        result = {"status": "validated", "results": []}

        cache_result(query, result)
        cached = get_cached_result(query)

        assert cached is not None
        assert cached == result

    def test_cache_miss_returns_none(self):
        """Non-existent key should return None."""
        cached = get_cached_result("nonexistent_query_xyz")
        assert cached is None

    def test_cache_with_sources(self):
        """Cache result with specific sources."""
        query = "heart failure"
        sources = ["pubmed", "cochrane"]
        result = {"status": "validated"}

        cache_result(query, result, sources=sources)
        cached = get_cached_result(query, sources=sources)

        assert cached == result

    def test_cache_requires_exact_source_match(self):
        """Must use same sources to retrieve."""
        query = "heart failure"
        result = {"status": "validated"}

        cache_result(query, result, sources=["pubmed"])

        # Try to retrieve with different sources
        cached = get_cached_result(query, sources=["cochrane"])
        assert cached is None

    def test_cache_multiple_queries(self):
        """Multiple queries should have separate cache entries."""
        result1 = {"query": "heart failure"}
        result2 = {"query": "diabetes management"}

        cache_result("heart failure", result1)
        cache_result("diabetes management", result2)

        assert get_cached_result("heart failure") == result1
        assert get_cached_result("diabetes management") == result2


class TestCacheTTL:
    """Test time-to-live expiration."""

    def test_cache_expires_after_ttl(self):
        """Cached result should expire after TTL."""
        query = "test_query"
        result = {"data": "test"}

        # Store result
        cache_result(query, result)
        assert get_cached_result(query) is not None

        # Artificially set created_at to old timestamp
        import app.services.result_cache as cache_module
        cache_key = _make_cache_key(query)
        cache_module._CACHE_STORE[cache_key]["created_at"] = time.time() - 400  # 400s ago (TTL=300s)

        # Should be expired
        cached = get_cached_result(query)
        assert cached is None

    def test_cache_not_expired_before_ttl(self):
        """Cached result should not expire before TTL."""
        query = "test_query"
        result = {"data": "test"}

        cache_result(query, result)

        # Should still be valid
        cached = get_cached_result(query)
        assert cached == result


class TestCacheEviction:
    """Test LRU eviction when cache is full."""

    def test_cache_respects_max_size(self):
        """Cache should not exceed max entries."""
        import app.services.result_cache as cache_module

        # Fill cache to near max
        max_size = cache_module._CACHE_MAX_ENTRIES
        for i in range(max_size + 10):
            cache_result(f"query_{i}", {"data": f"result_{i}"})

        # Cache should not exceed max
        assert len(cache_module._CACHE_STORE) <= max_size

    def test_oldest_entry_evicted(self):
        """Oldest entry should be evicted first."""
        import app.services.result_cache as cache_module

        # Store one entry
        cache_result("query_old", {"data": "old"})
        old_key = _make_cache_key("query_old")

        # Fill cache beyond capacity
        for i in range(cache_module._CACHE_MAX_ENTRIES):
            cache_result(f"query_new_{i}", {"data": f"new_{i}"})

        # Old entry should be evicted
        assert old_key not in cache_module._CACHE_STORE

    def test_recent_entries_preserved(self):
        """Most recent entries should be preserved during eviction."""
        import app.services.result_cache as cache_module
        import time

        clear_cache()

        # Store many old entries first
        for i in range(cache_module._CACHE_MAX_ENTRIES - 5):
            cache_result(f"query_old_{i}", {"data": f"old_{i}"})

        # Small sleep to ensure clear temporal ordering
        time.sleep(0.01)

        # Store a recent entry
        recent_query = "query_recent"
        recent_result = {"data": "recent"}
        cache_result(recent_query, recent_result)

        # Store a few more to trigger eviction
        for i in range(10):
            cache_result(f"query_newer_{i}", {"data": f"newer_{i}"})

        # Recent entry should still be cached (not oldest, so not evicted)
        cached = get_cached_result(recent_query)
        assert cached is not None


class TestClearCache:
    """Test cache clearing."""

    def test_clear_cache_empties_all_entries(self):
        """clear_cache should remove all entries."""
        # Add some entries
        cache_result("query1", {"data": "result1"})
        cache_result("query2", {"data": "result2"})
        cache_result("query3", {"data": "result3"})

        # Clear cache
        clear_cache()

        # All should be gone
        assert get_cached_result("query1") is None
        assert get_cached_result("query2") is None
        assert get_cached_result("query3") is None

    def test_cache_functional_after_clear(self):
        """Cache should work normally after being cleared."""
        # Add and clear
        cache_result("query1", {"data": "result1"})
        clear_cache()

        # Should be able to add again
        cache_result("query2", {"data": "result2"})
        assert get_cached_result("query2") == {"data": "result2"}


class TestCacheStats:
    """Test cache statistics."""

    def test_cache_stats_structure(self):
        """Stats should have required fields."""
        stats = get_cache_stats()
        assert "total_entries" in stats
        assert "max_entries" in stats
        assert "ttl_seconds" in stats
        assert "usage_percent" in stats

    def test_cache_stats_accuracy(self):
        """Stats should accurately reflect cache state."""
        clear_cache()
        cache_result("query1", {"data": "result1"})
        cache_result("query2", {"data": "result2"})

        stats = get_cache_stats()
        assert stats["total_entries"] == 2

    def test_usage_percent_calculation(self):
        """Usage percent should be calculated correctly."""
        clear_cache()
        cache_result("query1", {"data": "result1"})

        stats = get_cache_stats()
        # 1 entry out of max
        expected = (1 / stats["max_entries"]) * 100
        assert stats["usage_percent"] == pytest.approx(expected, rel=0.1)


class TestCacheEdgeCases:
    """Test edge cases."""

    def test_cache_empty_result(self):
        """Should be able to cache empty results."""
        cache_result("query", {})
        cached = get_cached_result("query")
        assert cached == {}

    def test_cache_none_sources_and_false_altmedicine(self):
        """Should handle None sources and alt medicine toggle."""
        result = {"data": "test"}
        cache_result("query", result, sources=None, include_alt_medicine=False)
        cached = get_cached_result("query", sources=None, include_alt_medicine=False)
        assert cached == result

    def test_cache_large_result(self):
        """Should cache large results."""
        large_result = {
            "data": "x" * 100000,  # 100KB
            "nested": {"deep": {"deeper": "value"}}
        }
        cache_result("large_query", large_result)
        cached = get_cached_result("large_query")
        assert cached == large_result

    def test_cache_special_characters_in_query(self):
        """Should handle special characters in query."""
        query = "heart failure & (cardiac OR ventricular)?"
        result = {"data": "test"}
        cache_result(query, result)
        cached = get_cached_result(query)
        assert cached == result

    def test_cache_unicode_in_query(self):
        """Should handle unicode characters."""
        query = "prévalence de l'insuffisance cardiaque"
        result = {"data": "test"}
        cache_result(query, result)
        cached = get_cached_result(query)
        assert cached == result
