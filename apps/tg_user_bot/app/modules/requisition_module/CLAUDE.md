# Requisition Module Guide For AI Agents

## Purpose

`app.modules.requisition_module` implements the user-side FSM survey for
submitting requisitions (applications). It collects input step by step and posts
it to the backend via `get_backend_client().create_requisition(...)`. Command,
callback and endpoint contracts are in [interface contracts](API.md).

## Layout

- `handlers.py` — `Router(name="requisitions")`, all handlers, and the backend
  call. There is no `service.py`: the logic is small enough to live in handlers.
- `keyboards.py` — inline/reply keyboards and callback constants
  (`APPLY_CONSULTATION_CALLBACK`, `APPLY_COMMUNITY_CALLBACK`, `CANCEL_CALLBACK`).
- `states.py` — `ConsultationStates` and `CommunityStates`.

## Flows

- `/apply` (`@login_required`) clears state and shows the product menu.
- Consultation (`apply:consultation`): name → phone (reply "Поделиться контактом
  📱" button or typed) → description → POST → success.
- Community (`apply:community`): name → experience/socials → motivation → POST →
  success.

The requisition `type` sent to the backend is the hardcoded string
`"consultation"` / `"community"` (not the `apply:`-prefixed callback data).

## Rules For Agents

- Keep the backend contract in [API.md](API.md) in sync with the backend
  `requisition` module.
- On `BackendClientError` the module keeps the FSM state and shows a generic
  retry message so the user can resubmit. Note: the error branch does NOT clear
  state — only the success branch does.
- Cancellation works two ways: the inline "Отмена ❌" button (`apply:cancel`) and
  the typed text "Отмена ❌"; each step also checks for the text manually.
- `login_required` guards `/apply`. The flow-start callbacks are protected
  indirectly through it; do not rely on them re-checking auth.
- If a survey grows non-trivial, extract a `service.py` rather than expanding
  `handlers.py`.
