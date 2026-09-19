# Development

- Keep the runtime Python 3.11+ standard-library-only and portable across macOS/Linux.
- Keep Jev questions bounded. Do not make Jev generate prose or replace deterministic integrity checks.
- Run `python3 -m unittest discover -s tests -v` after code changes.
- Live evaluation is opt-in and spends money. Honor the user's cumulative budget; use synthetic fixtures only.
- Do not commit credentials, env files, real vaults, or captured user documents.
- Document behavioral limits and measured evidence accurately; do not turn smoke checks into accuracy claims.
