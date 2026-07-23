# persona module

DMCAGuardian lead funnel: the product layer behind `/start`.

## Flow

`run_start_funnel(message)` is called by the system `/start` handler after
provisioning and FSM reset. It sends, in order:

1. `welcome` text (guide pitch);
2. the guide PDF from `settings.persona_guide_path` (2s delay — the welcome
   promises the file "in a couple of seconds");
3. `coala` video from `settings.persona_video_path` with the `video_caption`
   text and the contact keyboard;
4. sets the backend funnel state to `persona_start` via
   `PUT /telegram/state` (service token).

Missing asset files are logged and skipped without breaking the chain; if the
video is missing, the caption and keyboard are sent as a plain message so the
contact buttons still reach the user. Backend state failures are logged only —
they must never break the /start UX.

## Structure

- `service.py` — funnel orchestration, `PERSONA_START_STATE` constant.
- `keyboards.py` — contact keyboard: URL button to `ADMIN_CONTACT_URL`
  (omitted when unset) and a WebApp button to `CLIENT_MINIAPP_URL`.
- `messages.py`/`messages.json` — cached text templates.
- No router: both inline buttons are URL/WebApp buttons handled by the
  Telegram client, so the module registers nothing in `app/bot/registry.py`.

## Rules

- User/funnel state lives in the backend (`user_stats.state`, named states);
  the bot stores nothing locally.
- `video_caption` must stay within Telegram's 1024-char caption limit
  (guarded by `tests/test_persona_funnel.py`).
- New assets go to `assets/` and are configured via `PERSONA_*` env settings.
