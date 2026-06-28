### Background
In `agentwatch/security/encryption.py`, key rotation is handled by the `KeyRotationManager` class.

### Proposal
The `KeyRotationManager` is an unnecessary structural wrapper. Key rotation processes in this context are fundamentally procedural and do not require the overhead of a dedicated manager class.

- **Action:** Deconstruct `KeyRotationManager` and export its capabilities as simple, standalone functions.
- **Benefit:** The codebase will become noticeably leaner, more maintainable, and will follow Pythonic functional principles rather than forced object-oriented patterns.

### Acceptance Criteria
- [ ] Break down `KeyRotationManager` methods into module-level functions.
- [ ] Update import statements across the project.
- [ ] Confirm all encryption/rotation tests are green.
