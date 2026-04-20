"""
main.py — Entry point for Amul Protein Tracker.

Usage:
    python main.py                   # runs forever at configured interval
    python main.py --interval 10     # override interval (minutes)
    python main.py --once            # single run then exit (used by GitHub Actions)
"""

import argparse
import csv
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import yaml

from notifier import send_status_email
from tracker import scrape_website

# ─────────────────────────────────────────────
#  Logging
# ─────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("tracker.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
#  State file
# ─────────────────────────────────────────────

STATE_FILE = Path("state.json")


def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    return {}


def save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, indent=2))


# ─────────────────────────────────────────────
#  Watch-list helpers
# ─────────────────────────────────────────────

def is_watched(product_name: str, keywords: list[str]) -> bool:
    """Return True if the product matches any watch keyword (case-insensitive)."""
    if not keywords:
        return True  # watch everything when list is empty
    name_lower = product_name.lower()
    return any(kw.lower() in name_lower for kw in keywords)


# ─────────────────────────────────────────────
#  Core check
# ─────────────────────────────────────────────

def run_check(config: dict, state: dict, is_startup: bool = False) -> dict:
    email_cfg      = config["email"]
    notify_cfg     = config.get("notifications", {})
    watch_keywords = config.get("watch_keywords", [])

    always_send        = notify_cfg.get("always_send", False)
    notify_restock     = notify_cfg.get("notify_on_restock", True)
    notify_stockout    = notify_cfg.get("notify_on_stockout", False)

    for site in config.get("websites", []):
        site_name = site["name"]
        logger.info("─" * 55)
        logger.info("Checking: %s", site_name)

        products = scrape_website(site)

        if not products:
            logger.warning("No products returned — skipping for %s", site_name)
            continue

        # ── Console table (all products always) ──
        _print_table(site_name, products, watch_keywords)

        # ── Diff against previous state ───────────
        prev_state = state.get(site_name, {})
        restocked  = []   # SOLD OUT → AVAILABLE
        stockedout = []   # AVAILABLE → SOLD OUT
        new_state  = {}

        for p in products:
            key  = p["name"]
            prev = prev_state.get(key, "UNKNOWN")
            curr = p["status"]
            new_state[key] = curr

            if not is_watched(key, watch_keywords):
                continue  # skip diff for non-watched products

            if notify_restock and prev == "SOLD OUT" and curr == "AVAILABLE":
                restocked.append(key)
                logger.info("🎉 RESTOCKED: %s", key)

            if notify_stockout and prev == "AVAILABLE" and curr == "SOLD OUT":
                stockedout.append(key)
                logger.info("⚠️  SOLD OUT:  %s", key)

        state[site_name] = new_state

        # ── Decide whether to email ───────────────
        has_change      = bool(restocked or stockedout)
        startup_notify  = is_startup and notify_cfg.get("send_on_startup", True)

        # Filter the product list shown in email to watched items only
        # (unless watching everything)
        email_products = (
            [p for p in products if is_watched(p["name"], watch_keywords)]
            if watch_keywords else products
        )

        # ── Write history to CSV ──────────────────
        history_file = Path("run_history.csv")
        write_header = not history_file.exists()
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(history_file, mode="a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if write_header:
                writer.writerow(["Timestamp", "Site", "Product", "Status", "Price"])
            for p in email_products:
                writer.writerow([timestamp, site_name, p["name"], p["status"], p.get("price", "")])

        should_send = always_send or has_change or startup_notify

        if should_send:
            send_status_email(
                email_cfg   = email_cfg,
                site_name   = site_name,
                products    = email_products,
                restocked   = restocked,
                stockedout  = stockedout,
                is_startup  = is_startup,
            )
        else:
            watched_names = [p["name"] for p in email_products]
            statuses      = [p["status"] for p in email_products]
            logger.info(
                "No change in watched products — email skipped.\n"
                "  Watched: %s",
                " | ".join(f"{n.split(',')[0]}: {s}" for n, s in zip(watched_names, statuses))
            )

    return state


def _print_table(site_name: str, products: list[dict], watch_keywords: list[str]) -> None:
    logger.info("📦 %s — %d products", site_name, len(products))
    logger.info("%-55s  %-10s  %s", "Product", "Status", "Price")
    logger.info("-" * 85)
    for p in products:
        icon  = "✅" if p["status"] == "AVAILABLE" else "❌"
        watch = " 👀" if is_watched(p["name"], watch_keywords) and watch_keywords else ""
        logger.info(
            "%s  %-52s  %-10s  %s%s",
            icon,
            p["name"][:52],
            p["status"],
            p.get("price", ""),
            watch,
        )


# ─────────────────────────────────────────────
#  Main
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Amul Protein Stock Tracker")
    parser.add_argument("--interval", type=float, help="Check interval in minutes")
    parser.add_argument("--once",     action="store_true", help="Run once and exit")
    args = parser.parse_args()

    # ── Load config ───────────────────────────
    config_path = Path("config.yaml")
    if not config_path.exists():
        logger.error("config.yaml not found.")
        sys.exit(1)

    with open(config_path) as f:
        config = yaml.safe_load(f)

    # ── Override password from env var ────────
    # GitHub Actions injects GMAIL_PASSWORD secret as env var.
    env_password = os.environ.get("GMAIL_PASSWORD", "").strip()
    if env_password:
        config["email"]["sender_password"] = env_password
        logger.info("Using Gmail password from GMAIL_PASSWORD environment variable.")

    # ── Validate password ─────────────────────
    if not config["email"].get("sender_password", "").strip():
        logger.error(
            "\n❌  sender_password is empty!\n"
            "    • Local: paste it in config.yaml → email → sender_password\n"
            "    • GitHub Actions: add GMAIL_PASSWORD as a repository secret\n"
            "      (Settings → Secrets → Actions → New repository secret)\n"
        )
        sys.exit(1)

    interval_min = args.interval or config.get("check_interval_minutes", 30)
    interval_sec = interval_min * 60
    watch        = config.get("watch_keywords", [])

    logger.info("═" * 55)
    logger.info("  Amul Protein Tracker  🥛")
    logger.info("  Interval : %g minutes", interval_min)
    logger.info("  Sites    : %d", len(config.get("websites", [])))
    logger.info("  Email    → %s", config["email"]["recipient_email"])
    if watch:
        logger.info("  Watching : %s", " | ".join(watch))
    else:
        logger.info("  Watching : ALL products")
    logger.info("═" * 55)

    state     = load_state()
    first_run = True

    while True:
        now = datetime.now().strftime("%d %b %Y  %H:%M:%S")
        logger.info("\n⏰  Run at: %s", now)

        try:
            state = run_check(config, state, is_startup=first_run)
            save_state(state)
        except KeyboardInterrupt:
            raise
        except Exception as exc:
            logger.error("Unexpected error: %s", exc, exc_info=True)

        first_run = False

        if args.once:
            logger.info("--once flag set — exiting.")
            break

        logger.info("💤  Next check in %g minutes …\n", interval_min)
        time.sleep(interval_sec)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n⛔  Tracker stopped by user.")
