"""
LENA Connection Test Suite

Run with: python -m tests.test_connections
(from the backend/ directory)

Tests all five data source APIs plus OpenAI and Supabase.
The five public data sources (PubMed, ClinicalTrials, Cochrane, WHO, CDC)
should work without any API keys.
OpenAI and Supabase require keys in .env to pass.
"""

import asyncio
import json
import sys
from datetime import datetime


async def run_all_tests():
    """Run connection tests for all services."""
    print("=" * 60)
    print("LENA - Connection Test Suite")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("=" * 60)
    print()

    results = {}
    total = 0
    passed = 0
    failed = 0

    # --- Test 1: PubMed / NCBI ---
    print("[1/7] Testing PubMed / NCBI E-Utilities...")
    try:
        from app.services.pubmed import test_connection
        result = await test_connection()
        results["pubmed"] = result
        status = result.get("status", "unknown")
        if status == "connected":
            print(f"  PASS - Found {result.get('results_found', 0)} results")
            print(f"  Sample: {result.get('sample_title', 'N/A')[:80]}")
            passed += 1
        else:
            print(f"  FAIL - {result.get('error', 'Unknown error')}")
            failed += 1
    except Exception as e:
        print(f"  FAIL - Exception: {e}")
        results["pubmed"] = {"status": "error", "error": str(e)}
        failed += 1
    total += 1
    print()

    # --- Test 2: ClinicalTrials.gov ---
    print("[2/7] Testing ClinicalTrials.gov v2 API...")
    try:
        from app.services.clinical_trials import test_connection
        result = await test_connection()
        results["clinical_trials"] = result
        status = result.get("status", "unknown")
        if status == "connected":
            print(f"  PASS - Found {result.get('results_found', 0)} trials")
            print(f"  Sample: {result.get('sample_title', 'N/A')[:80]}")
            passed += 1
        else:
            print(f"  FAIL - {result.get('error', 'Unknown error')}")
            failed += 1
    except Exception as e:
        print(f"  FAIL - Exception: {e}")
        results["clinical_trials"] = {"status": "error", "error": str(e)}
        failed += 1
    total += 1
    print()

    # --- Test 3: Cochrane (via PubMed) ---
    print("[3/7] Testing Cochrane Library (via PubMed)...")
    try:
        from app.services.cochrane import test_connection
        result = await test_connection()
        results["cochrane"] = result
        status = result.get("status", "unknown")
        if status == "connected":
            print(f"  PASS - Found {result.get('results_found', 0)} reviews")
            print(f"  Sample: {result.get('sample_title', 'N/A')[:80]}")
            passed += 1
        else:
            print(f"  FAIL - {result.get('error', 'Unknown error')}")
            failed += 1
    except Exception as e:
        print(f"  FAIL - Exception: {e}")
        results["cochrane"] = {"status": "error", "error": str(e)}
        failed += 1
    total += 1
    print()

    # --- Test 4: WHO IRIS ---
    print("[4/7] Testing WHO IRIS Repository...")
    try:
        from app.services.who_iris import test_connection
        result = await test_connection()
        results["who_iris"] = result
        status = result.get("status", "unknown")
        if status == "connected":
            print(f"  PASS - Found {result.get('results_found', 0)} documents")
            print(f"  Sample: {result.get('sample_title', 'N/A')[:80]}")
            passed += 1
        else:
            print(f"  FAIL - {result.get('error', 'Unknown error')}")
            failed += 1
    except Exception as e:
        print(f"  FAIL - Exception: {e}")
        results["who_iris"] = {"status": "error", "error": str(e)}
        failed += 1
    total += 1
    print()

    # --- Test 5: CDC Open Data ---
    print("[5/7] Testing CDC Open Data (Socrata)...")
    try:
        from app.services.cdc import test_connection
        result = await test_connection()
        results["cdc"] = result
        status = result.get("status", "unknown")
        if status == "connected":
            print(f"  PASS - Found {result.get('results_found', 0)} datasets")
            print(f"  Sample: {result.get('sample_name', 'N/A')[:80]}")
            passed += 1
        else:
            print(f"  FAIL - {result.get('error', 'Unknown error')}")
            failed += 1
    except Exception as e:
        print(f"  FAIL - Exception: {e}")
        results["cdc"] = {"status": "error", "error": str(e)}
        failed += 1
    total += 1
    print()

    # --- Test 6: OpenAI (requires API key) ---
    print("[6/7] Testing OpenAI API...")
    try:
        from app.services.openai_service import test_connection
        result = await test_connection()
        results["openai"] = result
        status = result.get("status", "unknown")
        if status == "connected":
            print(f"  PASS - Model: {result.get('model_tested', 'N/A')}")
            print(f"  Response: {result.get('response', 'N/A')}")
            passed += 1
        else:
            print(f"  SKIP - {result.get('error', 'API key not configured')}")
            # Don't count as failed if key is just missing
            if not result.get("api_key_configured"):
                print("  (Set OPENAI_API_KEY in .env to enable)")
                total -= 1  # Don't count against score
            else:
                failed += 1
    except Exception as e:
        print(f"  SKIP - {e}")
        results["openai"] = {"status": "skipped", "error": str(e)}
        total -= 1
    total += 1
    print()

    # --- Test 7: Supabase (requires credentials) ---
    print("[7/7] Testing Supabase...")
    try:
        from app.db.supabase import test_connection
        result = await test_connection()
        results["supabase"] = result
        status = result.get("status", "unknown")
        if status == "connected":
            print(f"  PASS - {result.get('note', 'Connected')}")
            passed += 1
        else:
            print(f"  SKIP - {result.get('error', 'Credentials not configured')}")
            if not result.get("url_configured"):
                print("  (Set SUPABASE_URL and SUPABASE_ANON_KEY in .env to enable)")
                total -= 1
            else:
                failed += 1
    except Exception as e:
        error_msg = str(e)
        if "must be set" in error_msg:
            print(f"  SKIP - Supabase credentials not configured")
            print("  (Set SUPABASE_URL and SUPABASE_ANON_KEY in .env to enable)")
            results["supabase"] = {"status": "skipped", "error": error_msg}
            total -= 1
        else:
            print(f"  FAIL - {e}")
            results["supabase"] = {"status": "error", "error": error_msg}
            failed += 1
    total += 1
    print()

    # --- Summary ---
    print("=" * 60)
    print("RESULTS SUMMARY")
    print("=" * 60)
    print(f"  Total tested:  {total}")
    print(f"  Passed:        {passed}")
    print(f"  Failed:        {failed}")
    print(f"  Skipped:       {7 - total}")
    print()

    # Categorise
    public_apis = ["pubmed", "clinical_trials", "cochrane", "who_iris", "cdc"]
    public_passed = sum(
        1 for k in public_apis
        if results.get(k, {}).get("status") == "connected"
    )
    print(f"  Public APIs (no key needed): {public_passed}/5 connected")
    print(f"  OpenAI: {results.get('openai', {}).get('status', 'not tested')}")
    print(f"  Supabase: {results.get('supabase', {}).get('status', 'not tested')}")
    print()

    if public_passed == 5:
        print("All five public data sources are live. LENA's foundation is solid.")
    elif public_passed >= 3:
        print("Most data sources connected. Check the failures above.")
    else:
        print("Multiple connection issues detected. Check network and try again.")

    print("=" * 60)

    # Save results to file
    with open("tests/connection_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nDetailed results saved to tests/connection_results.json")

    return passed, failed, total


if __name__ == "__main__":
    passed, failed, total = asyncio.run(run_all_tests())
    sys.exit(0 if failed == 0 else 1)
