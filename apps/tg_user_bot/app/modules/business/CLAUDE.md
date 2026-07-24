# Business Module Guide For AI Agents

## Purpose

DMCAGuardian lead funnel for agencies: the product layer behind `/start business`
(deep link `t.me/<bot>?start=business`). Interface details (trigger, backend state
endpoint, keyboard targets) are in [interface contracts](API.md).

## Flow

`run_start_funnel(message)` is called by the system `/start` handler after
provisioning and FSM reset when the deep-link payload equals
`BUSINESS_START_PAYLOAD` (`"business"`). It sends, in order:

1. `welcome` text (agency guide pitch);
2. after a 2 s delay, the guide PDF from `settings.business_guide_path` WITH the
   `guide_caption` text (this is the one behavioral difference from `persona`,
   whose guide has no caption);
3. after a 1 s delay, the video from `settings.business_video_path` with the
   `video_caption` text and the contact keyboard;
4. sets the backend funnel state to `business_start` via `PUT /telegram/state`.

Missing asset files are logged and skipped without breaking the chain; if the
video is missing, the caption and keyboard are sent as a plain message so the
contact buttons still reach the user. Backend state failures are logged only —
they must never break the `/start` UX.

## Structure

- `service.py` — funnel orchestration, `BUSINESS_START_PAYLOAD = "business"` and
  `BUSINESS_START_STATE = "business_start"`.
- `keyboards.py` — contact keyboard (identical to `persona`): a URL button to
  `ADMIN_CONTACT_URL` (omitted when unset) and a WebApp button to
  `CLIENT_MINIAPP_URL`.
- `messages.py` / `messages.json` — cached text templates (`welcome`,
  `guide_caption`, `video_caption`).
- No router: both inline buttons are URL/WebApp buttons handled by the Telegram
  client. `/start` routing lives in the system module: payload `business` comes
  here, everything else goes to the `persona` funnel.

## Rules For Agents

- User/funnel state lives in the backend (`user_stats.state`, named states); the
  bot stores nothing locally.
- `guide_caption` and `video_caption` must stay within Telegram's 1024-char
  caption limit (guarded by `tests/test_business_funnel.py`).
- Asset paths come from `BUSINESS_GUIDE_PATH` / `BUSINESS_VIDEO_PATH`; defaults
  currently reuse the persona assets (`sila_tvorozhka.pdf`, `coala.mp4`) until
  agency-specific files are added to `assets/`.
