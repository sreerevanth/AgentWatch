import asyncio


class BFTAuditor:
    def __init__(self, configs: list[dict], quorum_size: int = 2):
        self.configs = configs
        self.quorum_size = quorum_size

    async def _audit_provider(self, config: dict, step_number: int, step_data: dict) -> dict:
        # Mock provider audit
        await asyncio.sleep(0.5)
        return {"score": 1.0, "provider": config.get("provider")}

    async def audit_step(self, step_number: int, step_data: dict) -> dict:
        tasks = [self._audit_provider(c, step_number, step_data) for c in self.configs]

        try:
            # Fix #511: Wrap gather with wait_for to prevent hanging if all timeout
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True), timeout=1.5
            )
        except TimeoutError:
            return {"error": "Global consensus timeout", "consensus_score": 0.0}

        valid_results = [r for r in results if not isinstance(r, Exception)]
        if len(valid_results) < self.quorum_size:
            return {"error": "Quorum not reached", "consensus_score": 0.0}

        return {"consensus_score": 1.0, "individual_scores": valid_results}
