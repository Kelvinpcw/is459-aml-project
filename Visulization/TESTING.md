# Local prototype checks

**Date:** 29 October 2026. **Scope:** only the invented fixtures and interface in `Visulization`.

These are not pipeline/data validation results, detector effectiveness measurements, AWS observations or evidence of production readiness.

## Results

| Check | Observed result |
| --- | --- |
| Node model tests | **27/27 passed**, Node.js v26.7.0. |
| Browser smoke checks | **41/41 passed** in the in-app Chromium browser. |
| Responsive layouts | All four views at **390, 768, 1024 and 1440 CSS pixels** had no whole-page horizontal overflow. Wide tables scroll inside their own containers. |
| Browser console | No errors reported during the final smoke run. |
| JavaScript syntax | All four JavaScript source files passed `node --check`. |
| Local links / assets | **14 references checked; no missing targets.** |
| Automated Lighthouse accessibility | **100/100** on each of the four default views after contrast/accessible-name corrections. |
| Automated Lighthouse best practices / SEO | **100/100 / 100/100** on each of the four default views. |
| Final automated audit failures | None reported on the four default views. |
| Cloud actions / costs | **None.** No AWS calls, paid processing, deployments or credentials used. |

Lighthouse scores are a limited automated check, **not** a WCAG conformance certificate, screen-reader user test, performance benchmark or guarantee for every dynamic state. No initial-load/cached-interaction latency target is claimed as measured.

## What is exercised

### Model tests

- Exclusive period ends and separate development/holdout/tail populations.
- Sum-count rates instead of daily-rate averages.
- Both currency dimensions applied to counts, support and baseline.
- Bank/format population consistency and reconciliation of alternative summary grains.
- Support applied after aggregation; low support not ranked by purported risk.
- Zero-baseline and empty-population handling.
- Eight-decimal exact monetary totals, including values beyond JavaScript Number precision.
- Descriptive interval bounds.
- Label-free case-fixture schema, stable source identities, parallel records and unknown entities.
- Fan support, snapshot boundaries and participant resolution.
- Independent graph node/link caps without loss or mutation of full evidence.
- Search filters, complete source-linked CSV, identity propagation and CSV escaping.

### Browser checks

- Default format view, currency-side recomputation and retained control focus.
- Sparse-tail warning and all bank-pair/format rows, including low support.
- Keyboard chart/node selection and segment/source dialogs.
- Fan-in arrow/hub semantics and cycle chronology caution.
- Compact and expanded wide-case graph counters.
- Full evidence pagination and intercepted in-memory CSV/JSON downloads, including all 124 records despite graph caps.
- Search empty/reset states.
- Unavailable performance metrics and clearly labelled proposal target.
- Release identity and truthfully named local fixture checks.
- Four-page × four-width overflow checks.

## Reproduce

From `Visulization`:

```sh
node --test tests/model.test.cjs
```

For the browser checks, start the optional local server:

```sh
python3 -m http.server 5387 --bind 127.0.0.1
```

Open **http://127.0.0.1:5387/tests/browser-smoke.html**. The harness displays its results and does not save or publish downloads. It needs HTTP for same-origin iframe inspection; the dashboard itself does not require a server.

Lighthouse was run through the in-app browser’s audit API. Its reports remain managed browser-tool artifacts, not part of this deliverable.

## Preview and remaining limitations

Use [`index.html`](index.html) for the actual interactive visual design. Desktop rendering was inspected through the browser API, including a 1440px isolated viewport. Final static screenshot saving was blocked when the browser Review tab ceased to be visible; no outdated or fabricated screenshots are presented as the final design.

Not tested: real datasets, real backend adapters, cloud IAM isolation, authentication, release publication/recovery, production-scale graph loading, screen-reader workflows, cross-browser compatibility or analyst usability sessions.

During the original local design task, no files in `Implementation` or GitHub content were read, and no git commits, pushes, remote fetches or cloud changes were performed. Existing work outside `Visulization` was left untouched. The subsequent publication task reads shared repository context and publishes this prototype; its checks and scope are recorded in the [team handoff](../Implementation/team-handoffs/2026-10-29-collaboration-and-prototype.md). Earlier audit results above remain historical unless explicitly rerun there.
