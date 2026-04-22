# Claude Code session prompts

**To use this file in one step:** open it in the project, then ask Claude Code: *“Read `.docs/claude-code-prompts.md` and run the prompt in section N (or the one I name). Follow `CLAUDE.md` and use the real shell — do not only suggest commands.”*

Copy one block below when you want a self-contained message without opening the file. Ground rules live in `CLAUDE.md`; scoring logic in `pipeline/config.yaml` and `pipeline/assets.yaml`.

**Defaults for this project:** qualitative scores use **Claude CLI** (subscription: `USE_CLAUDE_CLI=true`). A full scoring run can take a long time (many per-asset CLI calls). Use `./scripts/run-scoring.sh` (see script header for `SCORING_WALL_SECONDS`).

---

## 1. Full weekly scoring (snapshot + optional publish)

Use when you want a fresh `public/latest.json` and updated `pipeline/storage/history.sqlite`.

```
In cryptocurrencies-board: run the weekly scoring pipeline end-to-end using my local setup.

- Activate `.venv`, ensure `USE_CLAUDE_CLI=true` (subscription CLI; no Anthropic API unless I already set it).
- Run `./scripts/run-scoring.sh` from the repo root (or document why you use `python -m pipeline.run` instead). If it fails, read the latest `logs/scoring_*.log`, fix env/locks, retry once.
- Confirm `public/latest.json` and `pipeline/storage/history.sqlite` updated and `framework_version` / asset outputs look sane.
- If I asked to publish: `npm run build`, bump `public/index.html` dashboard.js cache query if the bundle changed, then `git add` only the relevant paths and commit with a conventional subject under 100 characters (no footer signature).

Do not refactor unrelated code. Follow CLAUDE.md for framework behavior.
```

**Variant — no git:** use section 2.

---

## 2. Weekly scoring, no commit

```
Run weekly scoring only: `./scripts/run-scoring.sh` from repo root with venv active. Do not commit or push. Report summary: run exit code, path to log, snapshot time, any assets that failed or hit qualitative timeouts.
```

---

## 3. Dry run (smoke test)

`--dry-run` **does not write** `public/latest.json` but still runs the full pipeline (network, APIs, **SQLite snapshots may still be written** — see `pipeline/run.py` `write_output`).

```
Activate `.venv`, run `python -m pipeline.run --dry-run`. Confirm it finishes; summarize any failures. Note: dry-run skips writing latest.json; database writes may still occur — tell me if that matters for my intent.
```

---

## 4. Dashboard bundle only

Use after editing `public/dashboard.jsx`.

```
From cryptocurrencies-board repo root: run `npm run build`. If `public/index.html` caches `dashboard.js` with a version query, bump it when the bundle changed. Report bundle output path and any errors.
```

---

## 5. Monthly discovery (ensemble)

```
Run `./scripts/run-discovery-ensemble.sh` from repo root. Ensure `claude` CLI is on PATH. When it finishes, point me to the new report path under `discovery/` and summarize additions/removals vs `pipeline/assets.yaml` (do not auto-edit assets unless I ask).
```

---

## 6. Interpret latest snapshot (no rescoring)

```
Read `public/latest.json` and give me a concise portfolio-level summary: GLI/Fear–Greed context, count by action state, any strong-accumulate or stand-aside, and 2–3 notable week-over-week changes if older snapshots exist in SQLite or git history. Do not run the scoring pipeline unless I say to run scoring.
```

---

## Tips

- Prefer **one goal per session** (scoring vs discovery vs dashboard) to avoid overlapping SQLite access and long runs.
- Name constraints explicitly: CLI-only, wall-clock timeout, conventional commit format.
