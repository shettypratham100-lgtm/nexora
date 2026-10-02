# Nexora — Setup Guide

Everything in this zip has been tested end-to-end in a sandbox environment
with the same DB credentials as your `.env`. Nothing here has touched your
real MySQL database — this is just the updated code.

## 1. Prerequisites (you already have these)

- Python 3.10+
- MySQL Server, running, with a database matching your `.env`:
  `DB_NAME=nw_nexora_db`, `DB_USER=nexora_user`, etc.
- LibreOffice installed (needed for Document Toolkit's DOCX↔PDF and
  PPT→PDF conversions). `nexora/settings.py` auto-detects `soffice` on
  your PATH; if it can't find it, it falls back to the Windows path
  `C:\Program Files\LibreOffice\program\soffice.exe`. If yours is
  installed somewhere else, update that fallback path.

## 2. Set up the virtual environment

```bash
cd nexora
python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate

pip install -r requirements.txt
```

Note: the original `requirements.txt` was UTF-16 encoded and contained a
huge unrelated pip-freeze (torch, transformers, etc.). It's been replaced
with a clean list of only what the project actually imports.

## 3. Database

Your `.env` already has the DB credentials. Just make sure MySQL is
running locally, then:

```bash
python manage.py migrate
```

This applies one new migration (`document_toolkit`) plus a handful of new
fields on `Collection`/`Resource` for starring and trash — nothing
destructive, nothing touches your existing data.

## 4. Create an account / run it

```bash
python manage.py createsuperuser   # optional, for /admin/
python manage.py runserver
```

Visit `http://127.0.0.1:8000/` and register a new account (or log in if
you already have one in your DB).

## 5. What's new since your original zip

- **Document Toolkit** — fully built: Create PDF, Merge, Split, Compress,
  Page Numbers, Watermark, Rotate, PDF↔DOCX, PPT→PDF, Image→PDF.
- **Trash** — deleting a resource/collection now soft-deletes it for 30
  days (`settings.TRASH_RETENTION_DAYS`) before permanent removal.
- **Starred** — star any resource or collection, view them all in one
  place.
- **Storage quota** — 10GB per user (`settings.USER_STORAGE_LIMIT_GB`),
  enforced on upload.
- **Full visual redesign** — new logo, light theme, dashboard, sidebar,
  dark-mode toggle, collapsible sidebar.
- **Search fixes** — live-as-you-type suggestions and recent searches
  now actually work (previously broken/incomplete).
- **Self-hosted assets** — Bootstrap, Bootstrap Icons, and fonts are now
  served locally instead of from CDNs, so the app doesn't depend on
  external network access to render.

## 6. Known gaps / next steps

Not yet redesigned to match your latest reference images:
- Collections grid (colored folder icons)
- Collection detail page (tabbed file table)
- PDF/resource viewer page

Ask me to continue on any of these whenever you're ready.
