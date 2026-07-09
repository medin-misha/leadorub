# Requisition Module — Bot Specification

This module implements the user-side FSM (Finite State Machine) survey flow for submitting product requisitions (applications).

## Overview

The module uses aiogram FSM to sequentially collect user input for different types of applications and sends them to the backend via `get_backend_client().create_requisition()`.

---

## Commands & Interactivity

1. **/apply** — Opens the inline keyboard for choosing a product (Consultation or Community).
2. **Consultation Flow** (`apply:consultation`):
   * State: `ConsultationStates.waiting_for_name` -> Ask name.
   * State: `ConsultationStates.waiting_for_phone` -> Ask phone (shows ReplyKeyboard with sharing contact button).
   * State: `ConsultationStates.waiting_for_description` -> Ask description -> POST to `/api/requisitions` -> Notify success.
3. **Community Flow** (`apply:community`):
   * State: `CommunityStates.waiting_for_name` -> Ask name.
   * State: `CommunityStates.waiting_for_experience` -> Ask experience / socials.
   * State: `CommunityStates.waiting_for_motivation` -> Ask motivation -> POST to `/api/requisitions` -> Notify success.

---

## Error Handling

If the backend request fails (e.g. `BackendClientError` is raised), the state is preserved and a general error message is shown to the user, allowing them to try again.
All active states can be cancelled using the inline "Отмена ❌" button or typing "Отмена ❌" in chat.
