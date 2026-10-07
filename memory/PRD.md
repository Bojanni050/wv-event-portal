# White Vision Event Portal — PRD

## Original problem statement
Build a modern, premium customer portal for White Vision, a Dutch professional DJ and event entertainment company (standalone app, future app.white-vision.nl, separate from WordPress). Every customer gets a personal event environment: dashboard with progress ("Your event is 68% ready"), My Event, Talk to your DJ (WhatsApp-like chat with timestamps, read/unread, attachments, notifications, pinned agreements), Music (Must Play, Don't Play, Favorites, Special moments), Timeline (customer suggests, staff manages definitive), Invitation builder (templates, photo, colors, typography, layout; preview, save, share, export PNG/PDF), Files. Separate White Vision admin: create customers/events, assign DJs, status, messages, timelines, music, files, invitation templates; dashboard with upcoming, attention, unread, incomplete, recent. Statuses New/Preparing/Ready/Completed + % progress. Premium, elegant, not CRM-like; desktop + mobile. API designed so WordPress can later create/update customers & events. Future: Spotify, email, WhatsApp, RSVP, payments, multiple DJs, gallery, AI, reminders.

User choices: Dutch UI; email+password login; files stored in database (PostgreSQL BYTEA); React+FastAPI+PostgreSQL accepted; seed demo data (opt-in via SEED_DEMO).

## Architecture
- Backend FastAPI (modular): database.py (SQLAlchemy 2.0 async engine/session), core.py (JWT cookie auth, role registry, event scoping), models.py (ORM tables), schemas.py (request/response), services.py (progress/stats), routes/{auth, events, messages, music, timeline, files, invitations, rsvp, admin, integrations}.py, seed.py (admin bootstrap + template reference data + optional demo data). Schema is managed with Alembic migrations.
- Tables: users, customers, djs, events, messages, music_items (external_ref JSONB for Spotify), timeline_items, files (BYTEA contents), invitations, invitation_templates, rsvps, login_attempts, password_reset_tokens
- Roles: customer, dj (assigned events only), admin (all). STAFF_ROLES in core.py
- WordPress: POST /api/integrations/wordpress/sync (X-API-Key = WP_API_KEY) upserts customer+event by external_id
- Frontend React (JS) + Tailwind + shadcn; dark velvet + gold; Cormorant Garamond + Plus Jakarta Sans. Shared feature modules used by customer and admin views. Public invitation page /u/:token

## Implemented (2026-10-06)
- Auth (login/logout/me/refresh/password change, brute-force lockout), no public signup
- Customer dashboard with hero, countdown, progress breakdown, 6 cards
- Event details with customer-editable vs staff-only fields
- Chat with polling, read receipts, attachments, pin → "Belangrijke afspraken", notification bell
- Music lists + 5 special moments + search
- Timeline with suggest/confirm flow
- Invitation builder: 5 templates, 4 layouts, 5 fonts, palettes/colors, photo upload, save, share link, PNG export
- Files (GridFS) with categories and filters
- Admin: overview, events (search/filter/create/detail tabs/status/delete), customers & DJs (optional login), templates CRUD
- Tested: 32/32 backend tests, frontend smoke flows

## Implemented (2026-10-06, iteration 2-3)
- Invitation PDF export (148x185mm) next to PNG
- RSVP: public form on shared invitation (/u/:token), toggle + deadline in builder, "Gasten" page (stats, filters, search, delete, CSV export), dashboard card, admin tab
- Customer account page (/event/:id/account): edit name/email/phone (synced to customer record), change password (current + new)
- Wachtwoord vergeten: login link → /wachtwoord-vergeten, reset email via Emergent-managed Resend (sender "White Vision"), /wachtwoord-herstellen?token= (sha256-hashed single-use token, 1h, max 3/hour, no email enumeration). FRONTEND_URL in backend/.env sets the link domain (set to https://app.white-vision.nl in production)
- Welkomstmail: admin "Nieuwe klant" dialog sends welcome email by default (account with unusable password + 7-day set-password link, /wachtwoord-herstellen?welkom=1); resend button per customer card (max 3/hour), welcome_sent_at status

## Backlog
- P1: PDF export of invitation; DELETE DJ endpoint; forgot-password via email (needs email provider); tighten CORS_ORIGINS to production domain
- P2: Spotify search, email/WhatsApp notifications, RSVP/guest management, payments/deposit status, multiple DJs, photo gallery, AI planning, reminders, TypeScript migration
