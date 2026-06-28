### Background
The `OwaspScanner` class in `agentwatch/security/owasp.py` encapsulates complex heuristic logic for security validation.

### Proposal
Wrapping this logic in an object-oriented class introduces unnecessary boilerplate. The scanner does not need to maintain complex state that warrants a dedicated class instantiation.

- **Action:** Refactor the `OwaspScanner` class into a single, straightforward, functional-style validation function.
- **Benefit:** This promotes a leaner, functional design, reduces instantiation overhead, and makes the security validation pipeline much easier to read and test.

### Acceptance Criteria
- [ ] Replace `OwaspScanner` class with a functional equivalent.
- [ ] Update all calling sites to use the new function.
- [ ] Verify security test coverage remains intact.
