# 🥛 Amul Protein Tracker

Automatically monitors the [Amul Protein Shop](https://shop.amul.com/en/browse/protein) and emails you whenever a sold-out item comes back in stock.

## Features

- ✅ Scrapes all products + availability status on every run
- 📧 Email notification when any item restocks (configurable)
- ⏰ Configurable check interval (default: every 5 minutes)
- 📍 Pincode-aware stock checking (pin: 411057)
- 🌐 Extensible — add any website via `config.yaml`

---

## Quick Start

### 1. Install dependencies

```bash
pip3 install -r requirements.txt
python3 -m playwright install chromium
```

### 2. Set up Gmail (one-time)

```bash
python3 setup_email.py
```

This walks you through getting a Gmail App Password and sends a test email.

### 3. Add your App Password to config.yaml

```yaml
email:
  sender_password: "xxxx xxxx xxxx xxxx"   # ← paste here
```

### 4. Run the tracker

```bash
# Runs forever, checks every 5 minutes
python3 main.py

# Custom interval (e.g. every 10 minutes)
python3 main.py --interval 10

# Single run (test / cron use)
python3 main.py --once
```

---

## What You'll Receive

**On startup:** A full product status table in your inbox.

**On restock:** An instant alert email like:

> 🟢 [Amul Protein Shop] 2 item(s) back in stock!

Each email shows every product with ✅ AVAILABLE or ❌ SOLD OUT status.

---

## Configuration (`config.yaml`)

| Key | Default | Description |
|-----|---------|-------------|
| `check_interval_minutes` | `5` | How often to check |
| `websites[].pincode` | `411057` | Delivery pincode |
| `notifications.notify_on_restock` | `true` | Email on restock |
| `notifications.always_send` | `false` | Email every run |
| `notifications.send_on_startup` | `true` | Email on first run |

### Adding Another Website (Generic)

```yaml
websites:
  - name: "My Other Shop"
    url: "https://example.com/products"
    pincode: ""
    type: "generic"
    product_selector: ".product-card"
    name_selector: "h3.title"
    soldout_selector: ".out-of-stock"
    soldout_text: "sold out"
```

---

## Files

| File | Purpose |
|------|---------|
| `main.py` | Entry point, scheduler, state management |
| `tracker.py` | Playwright scraper (Amul + generic) |
| `notifier.py` | Gmail SMTP email sender |
| `config.yaml` | All configuration |
| `setup_email.py` | One-time email setup wizard |
| `test_scraper.py` | Test scraping without email |
| `state.json` | Auto-generated — tracks last seen status |
| `tracker.log` | Auto-generated — execution log |

---

## Deployment (Free Servers)

### Option A: GitHub Actions (100% free, no server needed)

Create `.github/workflows/tracker.yml` — runs on a schedule in the cloud.

### Option B: Render.com Free Tier

Push to GitHub → connect to Render → set as a background worker.

> See deployment guide (coming soon).

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `sender_password is empty` | Run `python3 setup_email.py` |
| `SMTPAuthenticationError` | Use App Password, not Gmail password |
| `No products found` | Run `python3 debug_page.py` to inspect |
| Pincode not setting | The modal auto-opens on fresh headless session — already handled |
