# Psychologist Funnel Module (AGENTS.md)

## Purpose
This module implements the psychologist sales funnel prototype integrated with a Vue 3 Telegram Mini App (`client_miniapp`).

## Architecture
- `handlers.py`: Catch-all handlers for the inline callbacks and WebApp data:
  - `psy:consultations`: Renders description of consultations and provides a callback to start registration.
  - `psy:contacts`: Renders contact info.
  - `psy:main_menu`: Back to the primary state.
  - `psy:apply_stub`: Sends a Reply Keyboard message with a button to open the client Mini App.
  - `F.web_app_data` handler: Receives data sent from `client_miniapp` via `Telegram.WebApp.sendData`, processes it, creates a requisition of type `consultation` via the backend client, and outputs a success confirmation message while removing the Reply Keyboard.
- `keyboards.py`: Handles keyboard markup configurations, including `get_web_app_keyboard()` utilizing `settings.client_miniapp_url`.
- `messages.json`: Localized templates (Russian language).

## Integration Guidelines
- Mini App URL: Configured via `CLIENT_MINIAPP_URL` in `.env`.
- Caddy Routing: Caddy is configured to proxy `app.{$PUBLIC_HOST}` to `client_miniapp:80`.
- Data format:
  `client_miniapp` outputs JSON to the bot in the following structure:
  ```json
  {
    "type": "individual|family|express",
    "type_title": "🧠 Individual Consultation (or similar)",
    "name": "User Name",
    "phone": "User Phone",
    "description": "User request description"
  }
  ```
  The bot maps this into the backend requisition service payload structure:
  ```python
  payload = {
      "name": name,
      "phone": phone,
      "description": description,
      "consultation_type": data.get("type"),
      "consultation_type_title": type_title,
      "source": "miniapp"
  }
  ```
