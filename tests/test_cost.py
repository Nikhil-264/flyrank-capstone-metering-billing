import pytest
from app.services.cost_service import CostService

def test_cost_service_pricing_worked_example():
    # Worked example in pricing-plan.md:
    # 10,000 input tokens, 2,000 cached input tokens, 3,000 output tokens, 500 reasoning tokens.
    # input_rate = 10, cached_rate = 2, output_rate = 30, reasoning_rate = 30
    # Expected total = (10,000 * 10) + (2,000 * 2) + (3,000 * 30) + (500 * 30)
    #                = 100,000 + 4,000 + 90,000 + 15,000
    #                = 209,000 micro-cents (0.209 cents)
    cost = CostService.price(
        type="ai_token",
        quantity=15500,
        token_input=10000,
        token_cached_input=2000,
        token_output=3000,
        token_reasoning=500
    )
    assert cost == 209000

def test_cost_service_pricing_categories_separately():
    # Make sure rates are applied individually, not lumped together
    # Check only cached input (rate=2)
    cost_cached = CostService.price(type="ai_token", quantity=100, token_cached_input=100)
    assert cost_cached == 200

    # Check only input (rate=10)
    cost_input = CostService.price(type="ai_token", quantity=100, token_input=100)
    assert cost_input == 1000

    # Check reasoning billed as output (rate=30)
    cost_reasoning = CostService.price(type="ai_token", quantity=100, token_reasoning=100)
    assert cost_reasoning == 3000

def test_cost_service_api_call():
    # API calls have flat monthly model, so per-call rate = 0 (or flat rate in config)
    cost = CostService.price(type="api_call", quantity=1)
    assert cost == 0

def test_cost_service_invalid_type():
    cost = CostService.price(type="unknown_type", quantity=100)
    assert cost == 0
