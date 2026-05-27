# 🛒 Flipkart Price Drop Alert

<div align="center">

**Track Flipkart prices. Get Telegram alerts. Never miss a deal.**

[![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![Playwright](https://img.shields.io/badge/Scraper-Playwright-2EAD33?logo=playwright)](https://playwright.dev)
[![Supabase](https://img.shields.io/badge/Database-Supabase-3ECF8E?logo=supabase)](https://supabase.com)
[![Render](https://img.shields.io/badge/Hosted-Render-46E3B7?logo=render)](https://render.com)
[![GitHub Actions](https://img.shields.io/badge/CI%2FCD-GitHub%20Actions-2088FF?logo=github-actions)](https://github.com/features/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

</div>

---

## What is this?

Flipkart Price Drop Alert is a **fully automated price monitoring system** built with Python. You give it a Flipkart product URL and a target price — it checks the price every hour and sends you a **Telegram alert the moment the price drops**.

No spreadsheets. No manual checking. It just works.

---

## Features

- 🔍 **Flipkart scraper** — Playwright-based scraper that handles JavaScript-rendered pages
- ⏰ **Hourly price checks** — GitHub Actions cron runs every hour for free
- 📱 **Telegram alerts** — instant notification when price drops below your target
- 📊 **Price history** — every check is saved so you can see price trends over time
- 🤖 **Telegram bot commands** — `/check`, `/list`, `/help` from your phone
- 🌐 **REST API** — FastAPI backend with full Swagger docs at `/docs`
- 🔄 **Keep-alive** — self-pings every 14 minutes to keep Render free tier awake
- 🗄️ **Supabase database** — PostgreSQL with `products` and `price_history` tables

---

## Architecture

```
You (Telegram)
      │
      │  /check  /list  /add
      ▼
Telegram Bot  ◄──────────────────────────────┐
      │                                       │
      │                              Price Drop Alert
      ▼                                       │
FastAPI Backend (Render)                      │
      │                                       │
      ├── Playwright Scraper                  │
      │        │                              │
      │        ▼                              │
      │   Flipkart.com                        │
      │        │                              │
      │   Current Price ───────────────────── ┤
      │                                       │
      └── Supabase (PostgreSQL)               │
               │                             │
               ├── products table             │
               └── price_history table        │
                                              │
GitHub Actions (every hour) ──────────────────┘
runs checker.py → scrapes → compares → alerts
```

---

## Tech Stack

| Layer | Tool | Why |
|---|---|---|
| Language | Python 3.11 | Stable, wide package support |
| Web framework | FastAPI | Async, auto Swagger docs |
| Scraper | Playwright | Handles JS-rendered Flipkart pages |
| Database | Supabase (PostgreSQL) | Free tier, Mumbai region |
| Alerts | Telegram Bot API | Instant, free, easy to use |
| Scheduler | GitHub Actions cron | Free 2000 mins/month |
| Hosting | Render (free tier) | Auto-deploy from GitHub |
| HTTP client | httpx | Async HTTP for Telegram API |

---

## Project Structure

```
flipkart-price-alert/
├── .github/
│   └── workflows/
│       └── price-check.yml   ← runs every hour via GitHub Actions
├── backend/
│   ├── main.py               ← FastAPI app + keep-alive
│   ├── scraper.py            ← Playwright Flipkart scraper
│   ├── checker.py            ← price comparison + alert logic
│   ├── database.py           ← Supabase helper functions
│   ├── telegram_bot.py       ← Telegram alerts + command polling
│   ├── schema.sql            ← run this in Supabase SQL editor
│   ├── requirements.txt      ← Python dependencies
│   └── .env.example          ← environment variable template
├── .gitignore
└── README.md
```

---

## Quick Start

### Prerequisites

- Python 3.11
- Git
- A [Supabase](https://supabase.com) account (free)
- A Telegram account

---

### Step 1 — Clone and install

```bash
git clone https://github.com/YOUR_USERNAME/flipkart-price-alert.git
cd flipkart-price-alert/backend

py -3.11 -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Mac/Linux

pip install -r requirements.txt
playwright install chromium
```

---

### Step 2 — Set up Supabase

1. Go to [supabase.com](https://supabase.com) → New Project
2. Name: `flipkart-price-alert`, Region: **South Asia (Mumbai)**
3. Go to **SQL Editor → New Query**
4. Paste contents of `backend/schema.sql` → click **Run**
5. Go to **Settings → API** → copy:
   - **Project URL** → `SUPABASE_URL`
   - **anon public key** → `SUPABASE_KEY`
6. Go to **SQL Editor** and disable RLS:
```sql
alter table products disable row level security;
alter table price_history disable row level security;
```

---

### Step 3 — Create Telegram Bot

1. Open Telegram → search **@BotFather** → send `/newbot`
2. Follow prompts → copy the **token** → `TELEGRAM_BOT_TOKEN`
3. Send any message to your new bot
4. Visit in browser (replace token):
```
https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates
```
5. Find `"chat":{"id": XXXXXXXXX}` → that is your `TELEGRAM_CHAT_ID`

---

### Step 4 — Configure environment

```bash
cp .env.example .env
```

Fill in `backend/.env`:
```env
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_KEY=eyJhbGci...
TELEGRAM_BOT_TOKEN=7123456789:AAFxxx...
TELEGRAM_CHAT_ID=1234567890
RENDER_URL=https://your-app.onrender.com
```

---

### Step 5 — Test locally

```bash
# Test scraper
python scraper.py

# Test Telegram
python test_telegram.py

# Test full system
python test_full.py

# Run API
uvicorn main:app --reload
# Visit http://localhost:8000/docs
```

---

### Step 6 — Deploy to Render

1. Push code to GitHub
2. Go to [render.com](https://render.com) → New → Web Service
3. Connect your GitHub repo
4. Settings:
   - **Root Directory:** `backend`
   - **Build Command:** `pip install -r requirements.txt && playwright install chromium && playwright install-deps chromium`
   - **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Add all environment variables from `.env`
6. Add `RENDER_URL` = your Render app URL
7. Click **Deploy**

---

### Step 7 — Set up GitHub Actions

1. Go to your GitHub repo → **Settings → Secrets and variables → Actions**
2. Add these secrets:

| Secret | Value |
|---|---|
| `SUPABASE_URL` | your Supabase project URL |
| `SUPABASE_KEY` | your Supabase anon key |
| `TELEGRAM_BOT_TOKEN` | your bot token |
| `TELEGRAM_CHAT_ID` | your chat ID |

3. Go to **Actions tab** → click **Run workflow** to test manually

From now on it runs **every hour automatically for free**.

---

## API Reference

Once running, visit `/docs` for interactive Swagger UI.

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Health check |
| GET | `/api/products` | List all tracked products |
| POST | `/api/products` | Add new product to track |
| DELETE | `/api/products/{id}` | Stop tracking a product |
| GET | `/api/products/{id}/history` | Get price history |
| GET | `/api/products/{id}/check` | Check single product now |
| POST | `/api/check` | Check all products now |

### Add a product

```bash
curl -X POST https://your-app.onrender.com/api/products \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.flipkart.com/your-product-url",
    "target_price": 45000
  }'
```

---

## Telegram Commands

| Command | What it does |
|---|---|
| `/check` | Check all tracked products right now |
| `/list` | Show all products being tracked |
| `/help` | Show available commands |

---

## How it works

```
1. You add a Flipkart product URL + target price
         ↓
2. System saves it to Supabase
         ↓
3. GitHub Actions runs every hour
         ↓
4. Playwright visits the product page
         ↓
5. Extracts current price from HTML
         ↓
6. Compares with your target price
         ↓
7. Price dropped? → Telegram alert sent instantly
   No drop?      → Price saved to history, sleep
```

---

## Telegram Alert Example

```
🔥 Price Drop Alert!

APPLE iPhone 15 (Black, 128 GB)

Was:    ₹67,999
Now:    ₹59,900
Target: ₹60,000

You save ₹8,099 (12% off)

Buy on Flipkart →
```

---

## Database Schema

```sql
-- Products being tracked
create table products (
  id            bigint generated always as identity primary key,
  url           text not null,
  name          text not null,
  target_price  integer not null,
  active        boolean default true,
  created_at    timestamptz default now()
);

-- One row per price check
create table price_history (
  id          bigint generated always as identity primary key,
  product_id  bigint references products(id) on delete cascade,
  price       integer not null,
  checked_at  timestamptz default now()
);
```

---

## Environment Variables

| Variable | Description | Where to get it |
|---|---|---|
| `SUPABASE_URL` | Supabase project URL | Supabase → Settings → API |
| `SUPABASE_KEY` | Supabase anon public key | Supabase → Settings → API |
| `TELEGRAM_BOT_TOKEN` | Bot token from BotFather | Telegram → @BotFather |
| `TELEGRAM_CHAT_ID` | Your personal chat ID | `/getUpdates` API call |
| `RENDER_URL` | Your Render app URL | Render dashboard |

---

## Known Limitations

- Flipkart occasionally changes CSS selectors — scraper may need updating if prices stop being detected
- Render free tier sleeps after 15 mins of inactivity (keep-alive mitigates this)
- GitHub Actions free tier gives 2000 minutes/month — hourly checks use ~720 mins/month, well within limit

---

## Roadmap

- [ ] `/add <url> <price>` Telegram command
- [ ] Myntra scraper
- [ ] Amazon.in scraper
- [ ] Price history graph in Telegram
- [ ] Flash sale mode (15-minute checks)
- [ ] Multiple user support
- [ ] React dashboard UI

---

## Resume Description

> **Flipkart Price Drop Alert** | *Python, Playwright, FastAPI, Supabase, GitHub Actions, Telegram Bot API*
>
> Built a fully automated price monitoring system that scrapes Flipkart product pages hourly using Playwright, stores price history in Supabase PostgreSQL (Mumbai region), and delivers real-time Telegram alerts when prices fall below user-defined thresholds. Deployed FastAPI backend on Render with a self-ping keep-alive mechanism. Automated via GitHub Actions cron with zero server cost. Features REST API with Swagger docs, Telegram bot commands, and full price history logging.

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">
Built by Vishnu — from zero to production in one day.
</div>
