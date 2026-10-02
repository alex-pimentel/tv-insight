# Slide outline — tv-insight

Artifact from the `slide-design` pipeline (Steps 1–3). The generated deck is
[`tv-insight-deck.html`](./tv-insight-deck.html) (and the print output
[`tv-insight-deck.pdf`](./tv-insight-deck.pdf)).

## Step 1 — Content discovery

| Field | Value |
| --- | --- |
| Topic | `tv-insight` — Clean Architecture assignment (TVMaze + episodes + comments + AI insight) |
| Presenter | Alex Gomes — alex@agenteresolve.com.br |
| Source | [`../PRESENTATION.md`](../PRESENTATION.md), [`../ARCHITECTURE.md`](../ARCHITECTURE.md), [`../TRADEOFFS.md`](../TRADEOFFS.md), [`../CLIENT-FEEDBACK.md`](../CLIENT-FEEDBACK.md) |
| Purpose / CTA | Show the architecture and the decisions; end on `make up` → `localhost:7777` |
| Audience | Reviewers/banca: engineers, architecture-aware |
| Duration | 10 min deck (≈30–35 s/slide) |
| Language | English |
| Tone | Precise, technical, no hype |

## Step 2 — Structure (18 slides + appendix, one idea each)

| # | Type | Title |
| --- | --- | --- |
| 1 | title | Cover — Alex Gomes |
| 2 | quote | A deliberately small app — that is the test |
| 3 | feature-grid | Agenda |
| 4 | metrics | In one slide (386/95/11 · 321 MB) |
| 5 | comparison | The one decision everything follows from |
| 6 | content | What lives where — and what it buys |
| 7 | code | Make invalid states unrepresentable |
| 8 | diagram | Request flow: the series detail screen |
| 9 | section-divider | The AI feature |
| 10 | code | A port, a domain rule, and a chain |
| 11 | comparison | The decision matrix, in order |
| 12 | content | Failure is a first-class outcome |
| 13 | code | Caching without a stampede |
| 14 | content | Where it would break, and why I built it this way anyway |
| 15 | comparison | The architecture bent; it did not break (client feedback) |
| 16 | code | One command, two containers |
| 17 | comparison | Testing at four levels — and what it does not prove |
| 18 | metrics | If I had another week + contact |
| A1 | appendix | Appendix · the five files to read |

## Step 3 — Style

- **Preset**: Swiss Modern (direction **C — Swiss Claro**), adapted for offline use.
- **Background**: white `#ffffff` + visible 64px grid; 6px red top bar per slide.
- **Typography**: system stacks only (no Google Fonts / no CDN) — Helvetica/Arial for headings,
  system-ui for body, system mono for code.
- **Colors**: text `#1a1a1a` / `#666`, accent red `#ff3300`, secondary blue `#0066ff`.
- **Signature elements**: numbered eyebrow + slide number, red `rule` bars, bordered cards,
  metric row with red top border, red section divider.

## Step 4 — Format

- **HTML**, single file, **no external resources** (CSS-only animations + inline JS navigation).
- Prints to PDF via the browser (`@media print`, one slide per page).

## Step 5 — Validation

Checked programmatically: 18+1 sections, all required viewport rules (`100vh`/`100dvh`, `clamp()`,
`overflow: hidden`), `prefers-reduced-motion`, no `http(s)://` references, unique ids; plus a
headless render (0 overflow, 0 external requests, 0 console errors).
