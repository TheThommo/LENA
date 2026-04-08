"""
Tests for Tenant Detection Module

Tests extraction of tenant identifier from request headers and subdomains.

Run with: pytest tests/test_tenant.py -v
"""

import pytest
from fastapi import Request
from starlette.testclient import TestClient

from app.core.tenant import detect_tenant


class MockRequest:
    """Mock FastAPI request for testing."""

    def __init__(self, host=None, tenant_header=None):
        self.headers = {}
        if host:
            self.headers["Host"] = host
        if tenant_header:
            self.headers["X-Tenant-ID"] = tenant_header


class TestTenantDetectionPriority:
    """Test tenant detection priority (header > subdomain > default)."""

    def test_header_takes_priority_over_subdomain(self):
        """X-Tenant-ID header should take priority over subdomain."""
        request = MockRequest(
            host="nyu.lena-research.com",
            tenant_header="acme",
        )
        tenant = detect_tenant(request)
        assert tenant == "acme"

    def test_subdomain_when_no_header(self):
        """Subdomain should be used when no header present."""
        request = MockRequest(host="nyu.lena-research.com")
        tenant = detect_tenant(request)
        assert tenant == "nyu"

    def test_default_lena_when_no_header_or_subdomain(self):
        """Should default to 'lena' when no header or subdomain."""
        request = MockRequest(host="lena-research.com")
        tenant = detect_tenant(request)
        assert tenant == "lena"


class TestSubdomainDetection:
    """Test subdomain extraction from Host header."""

    def test_single_subdomain(self):
        """Extract single subdomain."""
        request = MockRequest(host="nyu.lena-research.com")
        tenant = detect_tenant(request)
        assert tenant == "nyu"

    def test_multiple_level_subdomain(self):
        """Extract from multi-level subdomain (takes first part)."""
        request = MockRequest(host="dept.nyu.lena-research.com")
        tenant = detect_tenant(request)
        assert tenant == "dept"

    def test_www_prefix_ignored(self):
        """www prefix should be ignored."""
        request = MockRequest(host="www.lena-research.com")
        tenant = detect_tenant(request)
        assert tenant == "lena"

    def test_subdomain_case_insensitive(self):
        """Subdomain extraction should be case-insensitive."""
        request = MockRequest(host="NYU.LENA-RESEARCH.COM")
        tenant = detect_tenant(request)
        assert tenant == "nyu"

    def test_subdomain_with_port(self):
        """Port in Host header should be stripped."""
        request = MockRequest(host="nyu.lena-research.com:8000")
        tenant = detect_tenant(request)
        assert tenant == "nyu"

    def test_subdomain_localhost_with_port(self):
        """Localhost with port should return 'lena' (default)."""
        request = MockRequest(host="localhost:8000")
        tenant = detect_tenant(request)
        assert tenant == "lena"

    def test_subdomain_ip_address(self):
        """IP address should return 'lena' (default)."""
        request = MockRequest(host="192.168.1.1:8000")
        tenant = detect_tenant(request)
        assert tenant == "lena"


class TestHeaderDetection:
    """Test X-Tenant-ID header detection."""

    def test_header_basic(self):
        """Extract tenant from X-Tenant-ID header."""
        request = MockRequest(tenant_header="acme")
        tenant = detect_tenant(request)
        assert tenant == "acme"

    def test_header_case_insensitive(self):
        """Header value should be case-insensitive (lowercased)."""
        request = MockRequest(tenant_header="ACME")
        tenant = detect_tenant(request)
        assert tenant == "acme"

    def test_header_whitespace_trimmed(self):
        """Whitespace in header should be trimmed."""
        request = MockRequest(tenant_header="  acme  ")
        tenant = detect_tenant(request)
        assert tenant == "acme"

    def test_header_with_underscores(self):
        """Header with underscores should be preserved."""
        request = MockRequest(tenant_header="acme_corp")
        tenant = detect_tenant(request)
        assert tenant == "acme_corp"

    def test_header_with_hyphens(self):
        """Header with hyphens should be preserved."""
        request = MockRequest(tenant_header="acme-corp")
        tenant = detect_tenant(request)
        assert tenant == "acme-corp"


class TestDefaultTenant:
    """Test default tenant fallback."""

    def test_no_host_no_header(self):
        """No host and no header should return 'lena'."""
        request = MockRequest()
        tenant = detect_tenant(request)
        assert tenant == "lena"

    def test_empty_host(self):
        """Empty host should return 'lena'."""
        request = MockRequest(host="")
        tenant = detect_tenant(request)
        assert tenant == "lena"

    def test_root_domain_only(self):
        """Root domain without subdomain should return 'lena'."""
        request = MockRequest(host="example.com")
        tenant = detect_tenant(request)
        assert tenant == "lena"


class TestEdgeCases:
    """Test edge cases."""

    def test_mixed_case_host(self):
        """Mixed case hostname should be lowercased."""
        request = MockRequest(host="NYU.Example.COM")
        tenant = detect_tenant(request)
        assert tenant == "nyu"

    def test_port_with_subdomain(self):
        """Subdomain with port should work correctly."""
        request = MockRequest(host="client.example.com:3000")
        tenant = detect_tenant(request)
        assert tenant == "client"

    def test_long_tenant_id(self):
        """Long tenant IDs should work."""
        long_id = "very_long_tenant_identifier_for_testing"
        request = MockRequest(tenant_header=long_id)
        tenant = detect_tenant(request)
        assert tenant == long_id

    def test_numeric_tenant_id(self):
        """Numeric tenant IDs should work."""
        request = MockRequest(tenant_header="12345")
        tenant = detect_tenant(request)
        assert tenant == "12345"

    def test_single_character_subdomain(self):
        """Single character subdomain should work."""
        request = MockRequest(host="a.example.com")
        tenant = detect_tenant(request)
        assert tenant == "a"
