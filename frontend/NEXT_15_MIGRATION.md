# Next.js 15 migration note (frontend/)

This records the `next` 14 → 15 upgrade done for the security fix in #596, what was verified, and the
one piece of follow-up work left out of scope.

## What changed

- `next` `14.2.30` → `15.5.20`
- `eslint-config-next` bumped to match
- `react` unchanged at `18.3.1` (Next 15 accepts `react ^18.2.0 || ^19.0.0`, so no React 19 migration)

## Why this is low-risk for this app

Next 15's headline breaking changes target the **App Router** — async `params`/`searchParams`, and
changed Server-Component caching defaults. This frontend is **Pages Router only**, so none of them
apply:

| Next 15 breaking change | Present here? |
|---|---|
| `app/` directory | none |
| `getServerSideProps` / `getStaticProps` | 0 usages |
| `next/font` | 0 usages |
| async `params` / `searchParams` (App Router) | n/a — Pages Router |

`next.config.js` uses only `reactStrictMode`, `output: 'standalone'`, and `transpilePackages`, all of
which remain valid in 15. The API proxy at `pages/api/v1/[...path].ts` uses the standard
`NextApiRequest` / `NextApiResponse` signature, unchanged in 15.

## What was verified

Run on Linux (the same environment as CI):

- **`npm run type-check` (`tsc --noEmit`)** — passes.
- **`npm run build`** — passes; all 16 routes (14 pages + 2 API routes) compile, and the pages prerender as static content.
- **Runtime.** Started the production server (`next start`) and exercised the routes; every one returns
  HTTP 200 and renders real content, with no server errors:

  | Route | Result |
  |---|---|
  | `/` (dashboard) | 200 |
  | `/replay` | 200 |
  | `/costs` | 200 |
  | `/security` | 200 |
  | `/policies` | 200 |
  | `/sessions/[id]` (dynamic) | 200 |
  | `/api/health` (API route) | 200 |

  Server ready in ~0.4s; no runtime regressions observed.

## Follow-up left out of scope: the ESLint migration

`next lint` is **deprecated** in Next 15.5 (it now prints a deprecation warning and is scheduled for
removal in Next 16); the recommended path is the standard ESLint CLI, and Next ships a
`next-lint-to-eslint-cli` codemod to migrate. Wiring that up here — adding an `.eslintrc.json` so the
project lints — makes `next build` start running ESLint, which then surfaces **7 pre-existing errors**
in `pages/replay.tsx` (unescaped `'` and `"`). Those errors predate this upgrade — the build has simply
never linted, because no ESLint config was committed for it to find.

Fixing that properly means its own PR: an ESLint config plus fixing those 7 errors. Pulling it into this
security upgrade would block a CVE fix behind unrelated lint churn. CI does not run lint
(`npm ci` → type-check → build), so nothing is red today.

**Follow-up issue:** add an ESLint config to `frontend/` and fix the 7 pre-existing `react/no-unescaped-entities`
errors in `pages/replay.tsx`.

## Security payoff

```
before : 5 vulnerabilities — 4 high, 1 moderate
after  : 2 vulnerabilities — 0 high, 2 moderate
```

All four HIGH advisories cleared, including the middleware-redirect SSRF. The two remaining are moderate
(a `next` moderate and a `postcss` XSS reached transitively through `next`), and clear when `next` bumps
its own dependency.
