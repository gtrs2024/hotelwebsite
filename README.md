# Elara — Premium Luxury Restaurant Website

A full-stack luxury restaurant website built with **Python Flask**, **SQLite**, and **Jinja2** templating. Features a public-facing website with elegant design, a complete admin dashboard, reservation inquiry system, menu management, and gallery management.

---

## Live Preview

> Designed for: **Elara Fine Dining, Lonavala, Maharashtra, India**

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11 + Flask 3 |
| Database | SQLite (built into Python) |
| Templating | Jinja2 |
| Frontend | HTML5, CSS3, Vanilla JavaScript |
| Auth | Werkzeug password hashing + Flask sessions |
| Security | Flask-WTF CSRF protection |
| Fonts | Google Fonts (Playfair Display, Cormorant Garamond, Poppins) |
| Icons | Font Awesome 6 |
| Deployment | Render (with Gunicorn) |

---

## What You Need to Install

### 1. Python 3.11+

Download from: https://www.python.org/downloads/

Verify installation:
```bash
python3 --version
```

### 2. pip (Python package manager)

Usually comes with Python. Verify:
```bash
pip --version
```

### 3. Python Dependencies

All dependencies are listed in `restaurant/requirements.txt`:

```
Flask==3.0.3
Flask-WTF==1.2.1
Werkzeug==3.0.3
Pillow==10.4.0
gunicorn==21.2.0        # Required for Render deployment only
```

---

## Local Setup (Step by Step)

### Step 1 — Clone the repository

```bash
git clone https://github.com/gtrs2024/hotelwebsite1.git
cd hotelwebsite1
```

### Step 2 — Navigate to the restaurant folder

```bash
cd restaurant
```

### Step 3 — Create a virtual environment (recommended)

```bash
python3 -m venv venv

# Activate on Mac/Linux:
source venv/bin/activate

# Activate on Windows:
venv\Scripts\activate
```

### Step 4 — Install dependencies

```bash
pip install -r requirements.txt
```

### Step 5 — Initialize the database

```bash
python3 database.py
```

This creates `restaurant.db` and seeds it with:
- Default admin account
- 16 sample menu items across 4 categories
- 9 sample gallery images

### Step 6 — Run the development server

```bash
python3 app.py
```

Open your browser: **http://localhost:8000**

---

## Project Structure

```
hotelwebsite1/
└── restaurant/
    ├── app.py                  # Main Flask application, all routes
    ├── database.py             # SQLite setup and seed data
    ├── requirements.txt        # Python dependencies
    ├── run.sh                  # Startup script (for Replit/Render)
    ├── restaurant.db           # SQLite database (auto-created)
    │
    ├── templates/              # Jinja2 HTML templates
    │   ├── base.html           # Base layout (navbar, footer)
    │   ├── index.html          # Home page
    │   ├── menu.html           # Menu page (tabbed)
    │   ├── gallery.html        # Gallery + lightbox
    │   ├── reservation.html    # Reservation inquiry form
    │   ├── contact.html        # Contact + Google Map
    │   └── admin/
    │       ├── base_admin.html # Admin base layout (sidebar)
    │       ├── login.html      # Admin login page
    │       ├── dashboard.html  # Dashboard with stats
    │       ├── reservations.html  # Manage reservations
    │       ├── menu.html          # Manage menu items
    │       └── gallery.html       # Manage gallery images
    │
    └── static/
        ├── css/
        │   └── style.css       # All styles (luxury design)
        ├── js/
        │   └── main.js         # Animations, navbar, lightbox
        └── images/
            └── gallery/        # Uploaded gallery images stored here
```

---

## Pages

| URL | Page |
|-----|------|
| `/` | Home page with hero, about, experiences, menu preview, gallery preview |
| `/menu` | Full menu with tabbed categories |
| `/gallery` | Image gallery with lightbox |
| `/reservation` | Reservation inquiry form |
| `/contact` | Contact info + embedded Google Map |
| `/admin/login` | Admin login |
| `/admin/dashboard` | Admin overview with stats |
| `/admin/reservations` | Manage reservation requests |
| `/admin/menu` | Add / edit / delete menu items |
| `/admin/gallery` | Upload / remove gallery images |

---

## Admin Login

> Default credentials (change immediately in production):

| Field | Value |
|-------|-------|
| URL | `http://localhost:8000/admin/login` |
| Username | `admin` |
| Password | `admin123` |

---

## Database Schema

### admins
| Column | Type |
|--------|------|
| id | INTEGER PRIMARY KEY |
| username | TEXT UNIQUE |
| password_hash | TEXT |

### reservations
| Column | Type |
|--------|------|
| id | INTEGER PRIMARY KEY |
| customer_name | TEXT |
| phone | TEXT |
| email | TEXT |
| preferred_date | TEXT |
| preferred_time | TEXT |
| guests | INTEGER |
| special_requests | TEXT |
| status | TEXT (New / Contacted / Pending) |
| created_at | DATETIME |

### menu_items
| Column | Type |
|--------|------|
| id | INTEGER PRIMARY KEY |
| category | TEXT |
| name | TEXT |
| description | TEXT |
| price | REAL |

### gallery
| Column | Type |
|--------|------|
| id | INTEGER PRIMARY KEY |
| image_path | TEXT |
| caption | TEXT |

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `SECRET_KEY` | Yes (production) | Flask session secret key. Set a long random string |
| `PORT` | Optional | Port to run on (default: 8000) |

For local development, a fallback secret key is built in. **Always set a real SECRET_KEY in production.**

---

## Deployment to Render

### Step 1 — Add Gunicorn to requirements.txt

Open `restaurant/requirements.txt` and add:
```
gunicorn==21.2.0
```

Commit and push:
```bash
git add .
git commit -m "Add gunicorn for Render deployment"
git push
```

### Step 2 — Create a new Web Service on Render

1. Go to **https://render.com** → Sign in
2. Click **New → Web Service**
3. Connect your GitHub repository (`hotelwebsite1`)
4. Configure:

| Setting | Value |
|---------|-------|
| Name | elara-restaurant |
| Root Directory | `restaurant` |
| Runtime | Python 3 |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `gunicorn app:app --bind 0.0.0.0:$PORT` |

### Step 3 — Add Environment Variables in Render

In the Render dashboard → Environment → Add:

| Key | Value |
|-----|-------|
| `SECRET_KEY` | `your-very-long-random-secret-key-here` |

### Step 4 — Deploy

Click **Create Web Service**. Render will build and deploy automatically.

> **Note on SQLite:** Render's file system is ephemeral — the SQLite database resets on each deploy. For persistent production data, consider migrating to **PostgreSQL** (Render offers a free managed Postgres tier).

---

## Security Features

- ✅ Passwords hashed with `werkzeug.security.generate_password_hash`
- ✅ CSRF protection on all forms via Flask-WTF
- ✅ Parameterised SQL queries (no SQL injection)
- ✅ Input validation on all form submissions
- ✅ Session-based admin authentication with `login_required` decorator
- ✅ File upload validation (allowed extensions only)

---

## Design System

| Element | Value |
|---------|-------|
| Primary (Background) | `#111111` |
| Secondary (Light) | `#F8F5F0` |
| Accent (Gold) | `#C8A96A` |
| Heading Font | Playfair Display |
| Subheading Font | Cormorant Garamond |
| Body Font | Poppins |

---

## License

This project is for personal / commercial use. Image credits: [Unsplash](https://unsplash.com).
