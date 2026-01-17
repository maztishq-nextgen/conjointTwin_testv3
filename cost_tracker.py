import threading
from typing import Dict, Any


class CostTracker:
    """Track OpenAI API usage and costs."""

    PRICING = {
        "gpt-4o": {"input": 0.0025, "output": 0.01},
        "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
        "gpt-4-turbo": {"input": 0.01, "output": 0.03},
        "gpt-4": {"input": 0.03, "output": 0.06},
        "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
    }

    def __init__(self):
        self.lock = threading.Lock()
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.total_cost = 0.0
        self.requests = 0

    def track(self, model: str, prompt_tokens: int, completion_tokens: int) -> Dict[str, Any]:
        pricing = self.PRICING.get(model, {"input": 0.01, "output": 0.03})
        cost = (prompt_tokens / 1000 * pricing["input"]) + (completion_tokens / 1000 * pricing["output"])

        with self.lock:
            self.total_prompt_tokens += prompt_tokens
            self.total_completion_tokens += completion_tokens
            self.total_cost += cost
            self.requests += 1

        return {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "cost": cost,
            "model": model,
        }

    def get_stats(self) -> Dict[str, Any]:
        with self.lock:
            return {
                "total_prompt_tokens": self.total_prompt_tokens,
                "total_completion_tokens": self.total_completion_tokens,
                "total_cost": round(self.total_cost, 6),
                "requests": self.requests,
            }

    def reset(self):
        with self.lock:
            self.total_prompt_tokens = 0
            self.total_completion_tokens = 0
            self.total_cost = 0.0
            self.requests = 0


cost_tracker = CostTracker()
