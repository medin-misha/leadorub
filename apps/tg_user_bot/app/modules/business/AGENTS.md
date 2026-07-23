# business module

DMCAGuardian lead funnel for agencies: the product layer behind
`/start business` (deep link `t.me/<bot>?start=business`).

## Flow

`run_start_funnel(message)` is called by the system `/start` handler after
provisioning and FSM reset when the deep-link payload equals
`BUSINESS_START_PAYLOAD` (`business`). It sends, in order:

1. `welcome` text (agency guide pitch);
2. the guide PDF from `settings.business_guide_path` with the `guide_caption`
   text (2s delay — the welcome promises the file "in a couple of seconds");
3. video from `settings.business_video_path` with the `video_caption` text and
   the contact keyboard;
4. sets the backend funnel state to `business_start` via
   `PUT /telegram/state` (service token).

Missing asset files are logged and skipped without breaking the chain; if the
video is missing, the caption and keyboard are sent as a plain message so the
contact buttons still reach the user. Backend state failures are logged only —
they must never break the /start UX.

## Structure

- `service.py` — funnel orchestration, `BUSINESS_START_PAYLOAD` and
  `BUSINESS_START_STATE` constants.
- `keyboards.py` — contact keyboard: URL button to `ADMIN_CONTACT_URL`
  (omitted when unset) and a WebApp button to `CLIENT_MINIAPP_URL`.
- `messages.py`/`messages.json` — cached text templates.
- No router: both inline buttons are URL/WebApp buttons handled by the
  Telegram client, so the module registers nothing in `app/bot/registry.py`.

## Rules

- User/funnel state lives in the backend (`user_stats.state`, named states);
  the bot stores nothing locally.
- `guide_caption` and `video_caption` must stay within Telegram's 1024-char
  caption limit (guarded by `tests/test_business_funnel.py`).
- Asset paths come from `BUSINESS_GUIDE_PATH`/`BUSINESS_VIDEO_PATH`; defaults
  currently reuse the persona assets until agency-specific files are added to
  `assets/`.
- `/start` routing lives in the system module: payload `business` comes here,
  everything else (empty payload, `source_*`) goes to the `persona` funnel.
