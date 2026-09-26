# AWBench with real models (opt-in)

By default AWBench uses deterministic stub models. With provider credentials, the stub summarizers can be replaced by a real model:

```bash
ANTHROPIC_API_KEY=... python -m benchmarks.awbench.runner --seeds 1 \
    --real-model anthropic:claude-haiku-4-5-20251001 --archs tool_loop,rag_memory
OPENAI_API_KEY=... python -m benchmarks.awbench.runner --seeds 1 \
    --real-model openai:gpt-4o-mini --real-model-alt openai:gpt-4o
```

- **Credential check first.** Before anything runs, the runner checks that the provider accepts the credential. If it doesn't (key missing, or rejected with 401/403), it prints `SKIPPED_EXTERNAL_CREDENTIAL: <reason>`, writes nothing, and exits 0. A skip is never recorded as a result.
- **Separate results.** Results go to `results/real/`. They never replace the stub results (`results/latest.json`). The report's `config.models` names the real model.
- **Model substitution.** `--real-model-alt` sets the model used for the `model_substitution` scenario. Without it, the same model runs with a different instruction.
- **Ground truth.** The ground-truth structure is unchanged, because it is the program's data flow.
- **Real models differ from stubs.**
  - Real models are abstractive: an answer is not a copy of its sources. Best-effort lineage can therefore resolve intermediates that are ambiguous with extractive stubs (ADR-0017).
  - Real models are also not deterministic: replay and counterfactual comparisons against a recorded run can differ for that reason alone.
- **Cost.** Each run makes one call per model invocation in the matrix. Choose `--archs`, `--seeds` and the scenarios accordingly.

The pytest equivalent for the client sensors is `tests/v3/test_real_models.py`, marker `external`:

```bash
pytest tests/v3/test_real_models.py -m external -rs
```
