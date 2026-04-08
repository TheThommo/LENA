"""
Tests for Geolocation Service

Tests IP geolocation with mocked HTTP calls and cache behavior.

Run with: pytest tests/test_geolocation.py -v
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.geolocation import geolocate_ip, _is_private_ip


class TestPrivateIPDetection:
    """Test detection of private/non-geolocatable IPs."""

    def test_localhost_127(self):
        """127.x.x.x should be detected as private."""
        assert _is_private_ip("127.0.0.1") is True

    def test_localhost_string(self):
        """'localhost' should be detected as private."""
        assert _is_private_ip("localhost") is True

    def test_private_192_168(self):
        """192.168.x.x should be detected as private."""
        assert _is_private_ip("192.168.1.1") is True

    def test_private_10(self):
        """10.x.x.x should be detected as private."""
        assert _is_private_ip("10.0.0.1") is True

    def test_private_172_16(self):
        """172.16.x.x should be detected as private."""
        assert _is_private_ip("172.16.0.1") is True

    def test_private_172_31(self):
        """172.31.x.x should be detected as private."""
        assert _is_private_ip("172.31.255.255") is True

    def test_ipv6_loopback(self):
        """::1 should be detected as private."""
        assert _is_private_ip("::1") is True

    def test_public_ip(self):
        """Public IP should not be private."""
        assert _is_private_ip("8.8.8.8") is False

    def test_public_ip_other(self):
        """Another public IP should not be private."""
        assert _is_private_ip("1.1.1.1") is False


class TestGeolocationBasic:
    """Test basic geolocation functionality."""

    @pytest.mark.asyncio
    async def test_geolocate_public_ip(self):
        """Public IP should be geolocated."""
        with patch("httpx.AsyncClient") as mock_client:
            # Mock the response
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_client.return_value.__aexit__ = AsyncMock(return_value=None)

            mock_instance.get = AsyncMock(
                return_value=MagicMock(
                    status_code=200,
                    json=lambda: {
                        "status": "success",
                        "country": "United States",
                        "city": "New York",
                        "lat": 40.7128,
                        "lon": -74.0060,
                    }
                )
            )

            result = await geolocate_ip("8.8.8.8")

            assert result is not None
            assert result["country"] == "United States"
            assert result["city"] == "New York"
            assert result["lat"] == 40.7128
            assert result["lon"] == -74.0060

    @pytest.mark.asyncio
    async def test_geolocate_private_ip_returns_none(self):
        """Private IPs should return None without API call."""
        result = await geolocate_ip("192.168.1.1")
        assert result is None

    @pytest.mark.asyncio
    async def test_geolocate_empty_ip_returns_none(self):
        """Empty IP should return None."""
        result = await geolocate_ip("")
        assert result is None

    @pytest.mark.asyncio
    async def test_geolocate_localhost_returns_none(self):
        """localhost should return None."""
        result = await geolocate_ip("localhost")
        assert result is None


class TestGeolocationCache:
    """Test geolocation caching behavior."""

    @pytest.mark.asyncio
    async def test_geolocate_caches_result(self):
        """Result should be cached after first lookup."""
        import app.services.geolocation as geo_module

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_client.return_value.__aexit__ = AsyncMock(return_value=None)

            mock_instance.get = AsyncMock(
                return_value=MagicMock(
                    status_code=200,
                    json=lambda: {
                        "status": "success",
                        "country": "USA",
                        "city": "Boston",
                        "lat": 42.3601,
                        "lon": -71.0589,
                    }
                )
            )

            # First call should hit API
            result1 = await geolocate_ip("1.2.3.4")
            assert result1["city"] == "Boston"

            # Reset mock call count
            mock_instance.get.reset_mock()

            # Second call should use cache
            result2 = await geolocate_ip("1.2.3.4")
            assert result2 == result1

            # API should not have been called again
            assert mock_instance.get.call_count == 0

    @pytest.mark.asyncio
    async def test_cache_respects_max_size(self):
        """Cache should not exceed max size."""
        import app.services.geolocation as geo_module

        geo_module._geo_cache.clear()

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_client.return_value.__aexit__ = AsyncMock(return_value=None)

            mock_instance.get = AsyncMock(
                return_value=MagicMock(
                    status_code=200,
                    json=lambda: {
                        "status": "success",
                        "country": "Test",
                        "city": "Test",
                        "lat": 0.0,
                        "lon": 0.0,
                    }
                )
            )

            # Fill cache beyond max
            for i in range(geo_module._CACHE_MAX_SIZE + 10):
                await geolocate_ip(f"1.2.3.{i % 256}")

            # Cache should not exceed max
            assert len(geo_module._geo_cache) <= geo_module._CACHE_MAX_SIZE


class TestGeolocationErrors:
    """Test error handling."""

    @pytest.mark.asyncio
    async def test_api_failure_returns_none(self):
        """API failure should return None."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_client.return_value.__aexit__ = AsyncMock(return_value=None)

            mock_instance.get = AsyncMock(
                return_value=MagicMock(
                    status_code=200,
                    json=lambda: {"status": "fail"}  # Not success
                )
            )

            result = await geolocate_ip("8.8.8.8")
            assert result is None

    @pytest.mark.asyncio
    async def test_http_error_returns_none(self):
        """HTTP error should return None."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_client.return_value.__aexit__ = AsyncMock(return_value=None)

            mock_instance.get = AsyncMock(
                side_effect=Exception("Connection error")
            )

            result = await geolocate_ip("8.8.8.8")
            assert result is None

    @pytest.mark.asyncio
    async def test_rate_limit_429_returns_none(self):
        """Rate limit (429) should return None."""
        import httpx

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_client.return_value.__aexit__ = AsyncMock(return_value=None)

            # Create a mock response with status 429
            mock_response = MagicMock()
            mock_response.status_code = 429

            mock_instance.get = AsyncMock(
                side_effect=httpx.HTTPStatusError("Rate limited", request=None, response=mock_response)
            )

            result = await geolocate_ip("8.8.8.8")
            assert result is None


class TestGeolocationResponseParsing:
    """Test parsing of API responses."""

    @pytest.mark.asyncio
    async def test_parse_complete_response(self):
        """Parse complete geolocation response."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_client.return_value.__aexit__ = AsyncMock(return_value=None)

            mock_instance.get = AsyncMock(
                return_value=MagicMock(
                    status_code=200,
                    json=lambda: {
                        "status": "success",
                        "country": "United Kingdom",
                        "city": "London",
                        "lat": 51.5074,
                        "lon": -0.1278,
                        "query": "1.1.1.1",
                    }
                )
            )

            result = await geolocate_ip("1.1.1.1")

            assert result["country"] == "United Kingdom"
            assert result["city"] == "London"
            assert result["lat"] == 51.5074
            assert result["lon"] == -0.1278

    @pytest.mark.asyncio
    async def test_parse_missing_fields(self):
        """Handle response with missing optional fields."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_client.return_value.__aexit__ = AsyncMock(return_value=None)

            mock_instance.get = AsyncMock(
                return_value=MagicMock(
                    status_code=200,
                    json=lambda: {
                        "status": "success",
                        "country": "Canada",
                        "city": None,  # Missing city
                        "lat": None,
                        "lon": None,
                    }
                )
            )

            result = await geolocate_ip("1.2.3.4")

            assert result is not None
            assert result["country"] == "Canada"
            assert result["city"] is None
