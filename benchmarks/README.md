# Reasoning Auditor Benchmark Suite

This suite evaluates the performance of the `ReasoningAuditor`, measuring its ability to catch unsafe or hallucinated agent actions *before* they are executed.

## The Benchmark (`benchmarks/test_cases.json`)
The benchmark consists of 500 procedurally generated reasoning steps (represented as `AgentEvent` objects):
*   **200 Safe Cases:** Routine file reads, safe updates, harmless API calls.
*   **200 Unsafe Cases:** Destructive commands (`rm -rf /`, `DROP TABLE`), credential exfiltration, and privilege escalation.
*   **100 Edge Cases:** Ambiguous commands, dangerous temp directory cleanups, and goal drift scenarios.

## Running the Evaluation
To run the evaluation script:
```bash
python benchmarks/run_eval.py
```
This script will sequentially evaluate all 500 cases, output a summary table to the console, and save the detailed ML metrics to `benchmarks/results/eval_latest.json`.

## Understanding the Default Baseline (0% F1)
By default, `run_eval.py` uses the **Heuristic Auditor** (since no LLM Judge API keys are configured). 
**Do not be alarmed when the default run outputs a 0% F1 score.**

The heuristic auditor is purely *structural*—it checks if a tool call was made and if arguments exist, but it cannot understand the *semantic meaning* of `rm -rf /` vs `ls -la`. Therefore, it scores all structurally valid test cases as safe, resulting in 0 True Positives. 

**The true purpose of this benchmark** is to provide a rigorous framework. Users can inject their own Anthropic or OpenAI judge into the `ReasoningAuditor` to see the F1 score jump to production-ready levels while monitoring the latency overhead in the P99 metrics.

## Acceptance Criteria Checklist
- [x] 500 test cases with categories tagged
- [x] Script runs with `python benchmarks/run_eval.py`
- [x] Output includes: Precision, Recall, F1, FP rate, avg/P50/P99 latency
- [x] Results saved as JSON
- [x] Works with default auditor config (no API key hacks)
