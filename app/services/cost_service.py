# app/services/cost_service.py
from typing import Optional
from app.config.pricing import (
    INPUT_TOKEN_RATE,
    CACHED_INPUT_TOKEN_RATE,
    OUTPUT_TOKEN_RATE,
    REASONING_TOKEN_RATE,
    API_CALL_RATE,
)

class CostService:
    @staticmethod
    def price(
        type: str,
        quantity: int,
        token_input: Optional[int] = None,
        token_cached_input: Optional[int] = None,
        token_output: Optional[int] = None,
        token_reasoning: Optional[int] = None,
    ) -> int:
        """
        Calculate cost in micro-cents for a usage event.
        Categories are priced separately and summed after pricing, not before.
        """
        if type == "api_call":
            return quantity * API_CALL_RATE
        elif type == "ai_token":
            t_input = token_input or 0
            t_cached = token_cached_input or 0
            t_output = token_output or 0
            t_reasoning = token_reasoning or 0
            
            # Categories are priced separately, then summed
            input_cost = t_input * INPUT_TOKEN_RATE
            cached_cost = t_cached * CACHED_INPUT_TOKEN_RATE
            output_cost = t_output * OUTPUT_TOKEN_RATE
            reasoning_cost = t_reasoning * REASONING_TOKEN_RATE
            
            return input_cost + cached_cost + output_cost + reasoning_cost
        return 0
