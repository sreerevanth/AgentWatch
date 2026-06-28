### Background
The `date-fns` library is currently used in `frontend/package.json` for date formatting operations. While it's a great library, it introduces an unnecessary dependency and increases our JavaScript bundle size.

### Proposal
Modern JavaScript engines have excellent built-in support for date formatting through the `Intl.DateTimeFormat` native API. By transitioning our date formatting logic to use `Intl.DateTimeFormat`, we can:
- Eliminate the `date-fns` dependency entirely.
- Reduce the application's overall bundle size, leading to faster load times.
- Align with modern, native web standards.

### Acceptance Criteria
- [ ] Remove `date-fns` from `package.json`.
- [ ] Refactor all existing `date-fns` imports to use `Intl.DateTimeFormat`.
- [ ] Verify that all dates render correctly across different locales.
