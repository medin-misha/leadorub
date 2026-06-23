# admin_module

Admin authentication & authorization for the backend. See `CLAUDE.md` in this
directory for the full, authoritative description (model, auth gates, endpoints,
bootstrap, settings).

Quick notes for agents:
- Crypto primitives are in `app/core/security.py`, not here (core layer must not import modules).
- Auth gates to reuse from other modules: `require_admin`, `require_service`, `require_admin_or_service` in `dependencies.py`.
- Admin token is validated against the DB (`is_active`) on every request — deletion/deactivation revokes access immediately.
- Keep comments in Russian (project convention); docstrings already follow it.
