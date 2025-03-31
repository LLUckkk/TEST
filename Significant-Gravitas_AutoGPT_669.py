from typing import Any


class ExecutionStats:
    def __init__(self):
        self.execution_stats = {}

    def merge_stats(self, stats: dict[str, Any]) -> dict[str, Any]:
        for key, value in stats.items():
            if isinstance(value, dict):
                self.execution_stats.setdefault(key, {}).update(value)
            elif isinstance(value, (int, float)):
                self.execution_stats.setdefault(key, 0)
                self.execution_stats[key] += value
            elif isinstance(value, list):
                self.execution_stats.setdefault(key, [])
                self.execution_stats[key].extend(value)
            else:
                self.execution_stats[key] = value
        return self.execution_stats


obj = ExecutionStats()
stats1 = {
    "input_token_count": 150,
    "output_token_count": 200,
    "llm_call_count": 1,
    "llm_retry_count": 0
}
print(obj.merge_stats(stats1))

stats2 = {
    "execution_time": 2.5,
    "errors": ["timeout", "invalid response format"],
    "input_token_count": 300,
    "output_token_count": 350
}
print(obj.merge_stats(stats2))

stats3 = {
    "input_token_count": 500,
    "output_token_count": 600,
    "additional_info": {
        "model_version": "v2.1",
        "api_version": "v1.0"
    }
}
print(obj.merge_stats(stats3))

stats4 = {
    "input_token_count": 1000,
    "output_token_count": 1200,
    "warnings": ["slow response", "high token usage"],
    "llm_call_count": 2
}
print(obj.merge_stats(stats4))

stats5 = {
    "input_token_count": 250,
    "output_token_count": 300,
    "llm_call_count": 3,
    "llm_retry_count": 1,
    "response_times": [0.5, 0.7, 0.6]
}
print(obj.merge_stats(stats5))
