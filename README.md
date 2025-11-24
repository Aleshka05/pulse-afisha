# Pulse Afisha

**Pulse Afisha** is a web application for discovering and creating city events  
with an interactive map, role-based access (admin / organizer / user / guest)  
and a full-featured management panel.

The project is designed as a **production-ready product**, not just a demo:  
it includes roles, moderation, support, favorites, RSVP, and Yandex Maps integration.

Production domain: **`pulse.of.by`** (via Cloudflare Tunnel + Docker).

---

## Core Features

### General

- User registration and authentication (JWT).
- Role-based access:
  - **Guest** – can browse the event feed and map without authentication.
  - **User** – profile, favorites, event RSVPs, support tickets.
  - **Organizer** – creates and manages events.
  - **Admin** – manages users, moderates events, handles support.

- Interactive map (Yandex Maps):
  - Events are displayed on the map using coordinates.
  - Filters by category, date, and current map area.
  - Clicking a marker shows a short preview and a link to event details.

---

## Roles and Capabilities

### Guest

- View the event feed.
- View events on the map.
- Open event details (without RSVP / favorites).

### User

- **Profile**:
  - View and edit contact details (phone, Telegram, “about me”).
  - Preference settings (categories, event formats).
- **Favorites**:
  - Add/remove events to/from favorites.
  - View a list of favorite events.
- **RSVP**:
  - RSVP statuses: `going`, `interested`, `canceled`.
  - View own RSVPs on a dedicated page.
  - Change or cancel RSVP.
- **Organizer role request**:
  - Submit an organizer role request from the profile page.
  - View the status of the latest request and admin comment.
- **Support**:
  - Send messages/complaints to admins.
  - View own support threads on the support page.

### Organizer

- Manage own events:
  - Create events (title, description, category, time, address, coordinates, free/paid, capacity).
  - Edit and delete own events.
- Send events for moderation:
  - Draft and rejected events can be submitted for review.
- Event statuses:
  - `draft`, `pending_moderation`, `published`, `rejected`, `archived`.
- RSVP monitoring:
  - Stats per status (`going` / `interested` / `canceled`).
  - View lists of users who RSVPed (via organizer/admin endpoints).

### Admin

- **Users (`/admin/users`)**:
  - View users list.
  - Block / unblock users.
  - Change role: `user` ↔ `organizer` ↔ `admin`.
- **Event moderation (`/admin/events`)**:
  - View events in `pending_moderation`.
  - Publish events (set status `published`).
  - Reject with a moderation comment (reason).
  - Delete events when needed.
- **Organizer requests (`/admin/organizer-requests`)**:
  - View organizer role requests.
  - Approve (change user role to `organizer`).
  - Reject with a comment.
- **Support tickets (`/admin/support-tickets`)**:
  - View user support tickets.
  - Reply, close, or delete tickets.

---

## Architecture Overview

The repository is organized as a monorepo:

```text
backend/    # FastAPI + SQLAlchemy + PostgreSQL
frontend/   # Next.js 16 + React 19 + Tailwind CSS
docker-compose.yml
