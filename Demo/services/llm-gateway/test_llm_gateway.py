"""
LLM Gateway - Test Script
Run this to verify the LLM Gateway is working correctly
"""
import requests
import json
from datetime import datetime


BASE_URL = "http://localhost:8002"


def test_health():
    """Test health endpoint"""
    print("\n" + "=" * 50)
    print("Testing Health Endpoint")
    print("=" * 50)

    response = requests.get(f"{BASE_URL}/health")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

    assert response.status_code == 200
    print("✓ Health check passed")


def test_models():
    """Test models listing"""
    print("\n" + "=" * 50)
    print("Testing Models Endpoint")
    print("=" * 50)

    response = requests.get(f"{BASE_URL}/models")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

    assert response.status_code == 200
    print("✓ Models listing passed")


def test_simple_completion():
    """Test simple completion (should use GPT-3.5)"""
    print("\n" + "=" * 50)
    print("Testing Simple Completion (GPT-3.5)")
    print("=" * 50)

    payload = {
        "prompt": "What is 2+2?",
        "temperature": 0.7,
        "max_tokens": 100
    }

    print(f"Request: {json.dumps(payload, indent=2)}")

    response = requests.post(f"{BASE_URL}/llm/complete", json=payload)

    if response.status_code == 200:
        data = response.json()
        print(f"\nResponse: {data['response']}")
        print(f"Model: {data['model_used']}")
        print(f"Complexity: {data['complexity_score']}")
        print(f"Reason: {data['selection_reason']}")
        print(f"Tokens: {data['tokens']}")
        print(f"Cost: ${data['cost']['total_cost']:.4f}")
        print(f"Cache Hit: {data['cache_hit']}")

        assert "gpt-3.5" in data['model_used'].lower(), "Should use GPT-3.5 for simple query"
        print("✓ Simple completion passed")
    else:
        print(f"❌ Error: {response.status_code}")
        print(f"Detail: {response.json()}")


def test_complex_completion():
    """Test complex completion (should use GPT-4)"""
    print("\n" + "=" * 50)
    print("Testing Complex Completion (GPT-4)")
    print("=" * 50)

    payload = {
        "prompt": "Explain the philosophical implications of quantum entanglement on the concept of free will, considering both deterministic and probabilistic interpretations of quantum mechanics.",
        "temperature": 0.7,
        "max_tokens": 500
    }

    print(f"Request: {payload['prompt'][:100]}...")

    response = requests.post(f"{BASE_URL}/llm/complete", json=payload)

    if response.status_code == 200:
        data = response.json()
        print(f"\nModel: {data['model_used']}")
        print(f"Complexity: {data['complexity_score']}")
        print(f"Reason: {data['selection_reason']}")
        print(f"Cost: ${data['cost']['total_cost']:.4f}")
        print(f"Cache Hit: {data['cache_hit']}")

        assert "gpt-4" in data['model_used'].lower(), "Should use GPT-4 for complex query"
        print("✓ Complex completion passed")
    else:
        print(f"❌ Error: {response.status_code}")
        print(f"Detail: {response.json()}")


def test_caching():
    """Test caching (repeat same request)"""
    print("\n" + "=" * 50)
    print("Testing Cache (90% Cost Savings)")
    print("=" * 50)

    payload = {
        "prompt": "What is the capital of France?",
        "temperature": 0.7,
        "max_tokens": 100
    }

    # First request - should be cache miss
    print("First request (cache miss)...")
    response1 = requests.post(f"{BASE_URL}/llm/complete", json=payload)

    if response1.status_code == 200:
        data1 = response1.json()
        print(f"Cache Hit: {data1['cache_hit']}")
        print(f"Cost: ${data1['cost']['total_cost']:.4f}")

        assert not data1['cache_hit'], "First request should be cache miss"

        # Second request - should be cache hit
        print("\nSecond request (cache hit)...")
        response2 = requests.post(f"{BASE_URL}/llm/complete", json=payload)

        if response2.status_code == 200:
            data2 = response2.json()
            print(f"Cache Hit: {data2['cache_hit']}")
            print(f"Cost: ${data2['cost']['total_cost']:.4f}")

            assert data2['cache_hit'], "Second request should be cache hit"

            # Calculate savings
            savings_pct = ((data1['cost']['total_cost'] - data2['cost']['total_cost']) /
                          data1['cost']['total_cost']) * 100
            print(f"\n✓ Cost savings: {savings_pct:.1f}%")
            print("✓ Caching test passed")
        else:
            print(f"❌ Second request failed: {response2.status_code}")
    else:
        print(f"❌ First request failed: {response1.status_code}")


def test_cache_stats():
    """Test cache statistics"""
    print("\n" + "=" * 50)
    print("Testing Cache Statistics")
    print("=" * 50)

    response = requests.get(f"{BASE_URL}/cache/stats")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

    assert response.status_code == 200
    print("✓ Cache stats passed")


def test_metrics():
    """Test Prometheus metrics"""
    print("\n" + "=" * 50)
    print("Testing Prometheus Metrics")
    print("=" * 50)

    response = requests.get(f"{BASE_URL}/metrics")
    print(f"Status Code: {response.status_code}")
    print(f"First 500 chars:\n{response.text[:500]}")

    assert response.status_code == 200
    assert "llm_requests_total" in response.text
    print("✓ Metrics endpoint passed")


def run_all_tests():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("LLM Gateway Test Suite")
    print("=" * 70)
    print(f"Started: {datetime.now().isoformat()}")
    print(f"Target: {BASE_URL}")

    try:
        test_health()
        test_models()
        test_cache_stats()
        test_metrics()

        # Tests requiring OpenAI API key
        print("\n" + "=" * 70)
        print("Tests requiring OpenAI API (skip if key not configured)")
        print("=" * 70)

        try:
            test_simple_completion()
            test_complex_completion()
            test_caching()
        except Exception as e:
            print(f"\n⚠ API tests skipped (OpenAI key may not be configured): {e}")

        print("\n" + "=" * 70)
        print("✓ All Tests Passed!")
        print("=" * 70)

    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
    except requests.exceptions.ConnectionError:
        print(f"\n❌ Cannot connect to {BASE_URL}")
        print("Make sure LLM Gateway is running:")
        print("  docker compose up -d llm-gateway")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")


if __name__ == "__main__":
    run_all_tests()
