# Fitness Trainer Funnel Module (AGENTS.md)

## Purpose
This module implements the "Tochka Sborki" fitness trainer funnel integrated with the existing Vue 3 Telegram Mini App (`client_miniapp`).

## Architecture
- `/start` renders the fitness trainer introduction and a single inline button.
- `tocka_zborki:get_guide` sends the configured PDF, edits the original message to the follow-up copy, and replaces its keyboard with the consultation Mini App button.
- `keyboards.py` owns both the callback button and the `WebAppInfo` button using `settings.client_miniapp_url`.
- `messages.json`: Localized templates (Russian language).

## Integration Guidelines
- Mini App URL: Configured via `CLIENT_MINIAPP_URL` in `.env`.
- Training guide: Configured via `TRAINING_GUIDE_PATH`; defaults to `assets/sila_tvorozhka.pdf` inside the bot service.
- Caddy Routing: Caddy is configured to proxy `app.{$PUBLIC_HOST}` to `client_miniapp:80`.
- The Mini App submits directly to `POST /api/requisitions/public`; the bot does not duplicate that API integration.
