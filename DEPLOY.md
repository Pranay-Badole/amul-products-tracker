# 🚀 Deploying to GitHub Actions (Free, Auto-runs Forever)

## Overview

GitHub Actions runs your tracker in the cloud **for free** on a schedule.
No server needed. No laptop kept on. Runs every 30 minutes automatically.

```
Your Mac  →  Push to GitHub  →  GitHub Actions runs on schedule  →  Email you  →  💤
```

---

## Step 1: Create a GitHub Account

Go to [github.com](https://github.com) and sign up (free).

---

## Step 2: Create a New Repository

1. Click **+** → **New repository**
2. Name it: `amul-protein-tracker`
3. Set to **Private** ← important (your email password is in config.yaml)
4. Click **Create repository**

---

## Step 3: Clear Password from config.yaml

> ⚠️ Your App Password must NOT be stored in git.
> We use a GitHub Secret instead — it's encrypted and never visible in logs.

In `config.yaml`, blank out the password:
```yaml
email:
  sender_password: ""    # ← leave empty, GitHub Secret handles this
```

---

## Step 4: Push Your Code to GitHub

```bash
cd "/Users/admin/Documents/P Projects/Amul Protein Tracker"

git init
git add .
git commit -m "Initial commit — Amul Protein Tracker"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/amul-protein-tracker.git
git push -u origin main
```

Replace `YOUR_USERNAME` with your actual GitHub username.

---

## Step 5: Add Gmail Password as a Secret

1. On GitHub, open your repository
2. Go to **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Name: `GMAIL_PASSWORD`
5. Value: `zrsp zxda htey zekr` (your 16-char App Password)
6. Click **Add secret**

---

## Step 6: Enable Actions

1. Go to the **Actions** tab in your repository
2. Click **Enable GitHub Actions** (if prompted)
3. You'll see the `Amul Protein Tracker` workflow listed

---

## Step 7: Test It Manually

Don't wait for the schedule — run it now:

1. Go to **Actions** tab
2. Click **Amul Protein Tracker** in the left sidebar
3. Click **Run workflow** → **Run workflow**
4. Watch the logs in real-time
5. Check your email — you should get a status email within ~2 minutes

---

## Adjusting the Schedule

Edit `.github/workflows/tracker.yml` and change the cron:

| You want | Cron value |
|----------|-----------|
| Every 15 min | `*/15 * * * *` |
| Every 30 min | `*/30 * * * *` |
| Every hour | `0 * * * *` |
| Every 6 hours | `0 */6 * * *` |

> **Note:** GitHub Actions minimum reliable interval is ~15-30 minutes.
> Very frequent schedules (< 15 min) may be delayed by GitHub.

---

## What Happens Each Run

```
1. GitHub starts an Ubuntu runner (free)
2. Checks out your repo (includes state.json from last run)
3. Installs Python + Playwright Chromium
4. Runs: python main.py --once
   - Scrapes shop.amul.com for pincode 411057
   - Compares Plain Lassi + Rose Lassi status vs last run
   - Sends email ONLY if status changed (no spam!)
5. Commits updated state.json back to repo
6. Runner shuts down
```

---

## GitHub Actions Free Limits

| Resource | Free Limit |
|----------|-----------|
| Minutes/month | 2,000 (private repo) |
| Minutes/month | Unlimited (public repo) |
| Storage | 500 MB |

Each run takes ~2-3 minutes → **2,000 ÷ 3 ≈ 666 runs/month free**.
At 30-min intervals: 48 runs/day × 30 days = **1,440 runs/month** ✅ under limit.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Workflow not running | Go to Actions tab and enable it |
| Email not sending | Check `GMAIL_PASSWORD` secret is set correctly |
| `state.json` not updating | Check the "Save state" step in Actions logs |
| Push permission denied | Go to Settings → Actions → General → Allow write permissions |
