# Notes for agents working in this repository (Base44 sandbox)

## What this repository is

`public-apis` is a curated **Markdown data list** (`README.md`, ~2k lines) plus a
small Python validation toolkit under `scripts/`. There is no application
server, database, or frontend build — CI only runs the validators and the
unittest suite.

Because the sandbox preview needs a web entry point, `docker-compose.base44.yml`
serves the repository's own `README.md` rendered as HTML on host port 3000
(`.base44/preview/server.py`). It re-renders whenever `README.md` changes, so a
browser refresh shows edits with no restart.

## Runbook

```bash
docker compose -f docker-compose.base44.yml up -d        # preview on http://localhost:3000
docker compose -f docker-compose.base44.yml logs -f web
docker compose -f docker-compose.base44.yml down
```

The repo's own tooling runs as on-demand one-shot services (`tools` profile, so
they never block `up`):

```bash
docker compose -f docker-compose.base44.yml run --rm tests      # unittest suite, from scripts/
docker compose -f docker-compose.base44.yml run --rm validate   # format + duplicate-link checks
```

Both install `scripts/requirements.txt` on startup. There is no Python on the
sandbox host, so always run Python through these containers. To validate a
touched file directly:

```bash
docker compose -f docker-compose.base44.yml run --rm --entrypoint python validate scripts/validate/format.py README.md
```

No external credentials are required — the link checker only makes plain HTTP
requests (no API keys), so there are no secrets in `.base44/environment.json`.

## Non-obvious findings

- **Python 3.10 for the tooling services.** `scripts/requirements.txt` pins
  `requests==2.27.1` / `urllib3==1.26.8`, matching the CI's Python 3.8 era. The
  preview renderer uses Python 3.12 because it only needs `markdown`.
- **Pre-existing format-validator drift (do not "fix" as setup work).**
  `scripts/validate/format.py` only skips separator rows that start with `|---`,
  but this commit's `README.md` uses alignment separators (`|:---|:---|…`) and
  an unpiped header row after each `<br >`. The validator therefore prints ~549
  errors across 89 rows. That is a README-vs-validator mismatch inherited from
  this (111-day-old) commit, not a sandbox problem; the `validate` service exits
  non-zero for that reason. The 31 unittests in `scripts/tests` all pass.
- Only `.github/cs1586-APILayerLogoUpdate2022-LJ_v2-HighRes.png` is referenced by
  a relative path; the preview server serves repository files for such paths.
- No host/origin allowlists are involved: the preview server is stdlib
  `http.server` and does not validate `Host` or `Origin`, so no
  `BASE44_PREVIEW_MODE`-gated overrides are needed here.

## How to verify the setup works

```bash
curl -s http://localhost:3000/healthz                 # -> ok
curl -s http://localhost:3000/ | grep -c "<table>"     # -> 51 rendered category tables
docker compose -f docker-compose.base44.yml ps         # web is healthy
```
