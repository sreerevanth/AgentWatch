### Background
The `SilenceBaseline` located in `agentwatch/scoring/silence.py` is defined as a standalone configuration dataclass.

### Proposal
This class has no inheritance and serves as a prime example of a YAGNI (You Aren't Gonna Need It) abstraction. Managing it as a separate class overcomplicates the module's structure without providing tangible architectural benefits.

- **Action:** Merge the `SilenceBaseline` attributes and logic directly into the `SilentFailureDetector`.
- **Benefit:** Reduces file complexity, flattens the scoring logic, and removes a redundant data structure.

### Acceptance Criteria
- [ ] Remove the `SilenceBaseline` dataclass.
- [ ] Integrate its properties natively into `SilentFailureDetector`.
- [ ] Ensure scoring pipeline tests pass successfully.
