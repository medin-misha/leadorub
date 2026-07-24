# Persona Module Guide For AI Agents

## Purpose

DMCAGuardian lead funnel: the product layer behind a plain `/start`. Interface
details (trigger, backend state endpoint, keyboard targets) are in [interface
contracts](API.md).

## Flow

`run_start_funnel(message)` is called by the system `/start` handler after
provisioning and FSM reset, for any payload that is not `business`. It sends, in
order:

1. `welcome` text (guide pitch);
2. after a 2 s delay (the welcome promises the file "in a couple of seconds"),
   the guide PDF from `settings.persona_guide_path` — sent WITHOUT a caption;
3. after a 1 s delay, the `coala` video from `settings.persona_video_path` with
   the `video_caption` text and the contact keyboard;
4. sets the backend funnel state to `persona_start` via `PUT /telegram/state`.

Missing asset files are logged and skipped without breaking the chain; if the
video is missing, the caption and keyboard are sent as a plain message so the
contact buttons still reach the user. Backend state failures are logged only —
they must never break the `/start` UX.

## Structure

- `service.py` — funnel orchestration, `PERSONA_START_STATE = "persona_start"`.
- `keyboards.py` — contact keyboard: a URL button to `ADMIN_CONTACT_URL` (omitted
  when unset) and a WebApp button to `CLIENT_MINIAPP_URL` (always shown).
- `messages.py` / `messages.json` — cached text templates (`welcome`,
  `video_caption`; no `guide_caption`).
- No router: both inline buttons are URL/WebApp buttons handled by the Telegram
  client, so the module registers nothing in `app/bot/registry.py`. `/start`
  routing itself lives in the system module.

## Rules For Agents

- User/funnel state lives in the backend (`user_stats.state`, named states); the
  bot stores nothing locally.
- `video_caption` must stay within Telegram's 1024-char caption limit (guarded by
  `tests/test_persona_funnel.py`).
- New assets go to `assets/` and are configured via `PERSONA_*` env settings.
