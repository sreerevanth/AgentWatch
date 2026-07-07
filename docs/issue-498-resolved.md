# Issue #498 Resolution Note

Issue [#498](https://github.com/sreerevanth/AgentWatch/issues/498) requested collapsing `TemporalDecayManager` into `ForgettingEngine`.

This work was completed and merged via [PR #533](https://github.com/sreerevanth/AgentWatch/pull/533) which closed issue [#476](https://github.com/sreerevanth/AgentWatch/issues/476) — the original task. The merge made `TemporalDecayManager` a redundant abstraction, fully resolving the intent of #498.

Closes #498