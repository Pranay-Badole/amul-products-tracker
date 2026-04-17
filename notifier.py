"""
notifier.py — Sends email notifications via Gmail SMTP.
"""

import logging
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)


def send_status_email(
    email_cfg: dict,
    site_name: str,
    products: list[dict],
    restocked: list[str],
    stockedout: list[str] = None,
    is_startup: bool = False,
) -> bool:
    """
    Send a formatted email with the product status table.

    Args:
        email_cfg   : email section from config.yaml
        site_name   : friendly name of the tracked website
        products    : list of {name, status, price} dicts (already filtered to watched)
        restocked   : product names that just flipped SOLD OUT → AVAILABLE
        stockedout  : product names that just flipped AVAILABLE → SOLD OUT
        is_startup  : True if this is the first run notification

    Returns:
        True if email was sent successfully, False otherwise.
    """
    if stockedout is None:
        stockedout = []
    sender   = email_cfg["sender_email"]
    password = email_cfg["sender_password"]
    recipient = email_cfg["recipient_email"]

    if not password:
        logger.error("Gmail App Password is empty — configure sender_password in config.yaml")
        return False

    subject = _build_subject(site_name, restocked, stockedout, is_startup)
    html    = _build_html(site_name, products, restocked, stockedout, is_startup)
    text    = _build_text(site_name, products, restocked, stockedout)

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = f"Amul Tracker 🥛 <{sender}>"
        msg["To"]      = recipient

        msg.attach(MIMEText(text, "plain"))
        msg.attach(MIMEText(html, "html"))

        with smtplib.SMTP(email_cfg["smtp_host"], email_cfg["smtp_port"]) as server:
            server.ehlo()
            server.starttls()
            server.login(sender, password)
            server.sendmail(sender, recipient, msg.as_string())

        logger.info("✅ Email sent → %s | Subject: %s", recipient, subject)
        return True

    except smtplib.SMTPAuthenticationError:
        logger.error("❌ Gmail authentication failed. Check your App Password in config.yaml.")
    except Exception as exc:
        logger.error("❌ Failed to send email: %s", exc)

    return False


# ─────────────────────────────────────────────
#  Email builders
# ─────────────────────────────────────────────

def _build_subject(site_name: str, restocked: list[str], stockedout: list[str], is_startup: bool) -> str:
    if restocked and stockedout:
        return f"🟢❌ [{site_name}] Stock changes: {len(restocked)} restocked, {len(stockedout)} sold out"
    if restocked:
        return f"🟢 [{site_name}] {len(restocked)} item(s) back in stock!"
    if stockedout:
        return f"❌ [{site_name}] {len(stockedout)} item(s) just sold out"
    if is_startup:
        return f"🔔 [{site_name}] Tracker started — watching for stock changes"
    return f"📋 [{site_name}] Stock status update"


def _build_html(site_name: str, products: list[dict], restocked: list[str], stockedout: list[str], is_startup: bool) -> str:
    now = datetime.now().strftime("%d %b %Y, %I:%M %p")

    # Build rows
    rows_html = ""
    for p in products:
        is_new = p["name"] in restocked
        status_color = "#22c55e" if p["status"] == "AVAILABLE" else "#ef4444"
        status_bg    = "#f0fdf4" if p["status"] == "AVAILABLE" else "#fef2f2"
        badge        = (
            f'<span style="background:{status_color};color:#fff;'
            f'padding:3px 10px;border-radius:20px;font-size:12px;font-weight:600;">'
            f'{p["status"]}</span>'
        )
        new_badge = (
            ' <span style="background:#f59e0b;color:#fff;'
            'padding:2px 7px;border-radius:12px;font-size:11px;font-weight:700;">NEW ✨</span>'
            if is_new else ""
        )
        price_cell = f'<td style="padding:10px 14px;color:#6b7280;">{p.get("price","")}</td>'

        rows_html += (
            f'<tr style="background:{status_bg};border-bottom:1px solid #e5e7eb;">'
            f'<td style="padding:10px 14px;font-weight:500;color:#111827;">'
            f'{p["name"]}{new_badge}</td>'
            f'{price_cell}'
            f'<td style="padding:10px 14px;">{badge}</td>'
            f'</tr>'
        )

    restock_banner = ""
    if restocked:
        items_list = "".join(f"<li>{n}</li>" for n in restocked)
        restock_banner = f"""
        <div style="background:#f0fdf4;border:2px solid #22c55e;border-radius:10px;
                    padding:16px 20px;margin-bottom:16px;">
          <p style="margin:0 0 8px;font-weight:700;color:#166534;font-size:15px;">
            🎉 Back in Stock!
          </p>
          <ul style="margin:0;padding-left:20px;color:#166534;">{items_list}</ul>
        </div>"""

    stockout_banner = ""
    if stockedout:
        items_list2 = "".join(f"<li>{n}</li>" for n in stockedout)
        stockout_banner = f"""
        <div style="background:#fef2f2;border:2px solid #ef4444;border-radius:10px;
                    padding:16px 20px;margin-bottom:16px;">
          <p style="margin:0 0 8px;font-weight:700;color:#991b1b;font-size:15px;">
            ❌ Just Sold Out
          </p>
          <ul style="margin:0;padding-left:20px;color:#991b1b;">{items_list2}</ul>
        </div>"""

    startup_banner = ""
    if is_startup and not restocked and not stockedout:
        startup_banner = """
        <div style="background:#eff6ff;border:1px solid #bfdbfe;border-radius:10px;
                    padding:12px 16px;margin-bottom:16px;color:#1e40af;font-size:13px;">
          ✅ Tracker is running. You'll be notified when watched items restock.
        </div>"""

    return f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8"></head>
    <body style="margin:0;padding:0;background:#f3f4f6;font-family:'Segoe UI',Arial,sans-serif;">
      <table width="100%" cellpadding="0" cellspacing="0" style="background:#f3f4f6;padding:30px 0;">
        <tr><td align="center">
          <table width="620" cellpadding="0" cellspacing="0"
                 style="background:#fff;border-radius:16px;overflow:hidden;
                        box-shadow:0 4px 24px rgba(0,0,0,0.08);">

            <!-- Header -->
            <tr>
              <td style="background:linear-gradient(135deg,#1e3a5f,#2563eb);
                         padding:28px 32px;text-align:center;">
                <p style="margin:0;font-size:28px;">🥛</p>
                <h1 style="margin:8px 0 4px;color:#fff;font-size:22px;font-weight:700;">
                  {site_name}
                </h1>
                <p style="margin:0;color:#93c5fd;font-size:13px;">Stock Status Report · {now}</p>
              </td>
            </tr>

            <!-- Body -->
            <tr>
              <td style="padding:28px 32px;">
                {restock_banner}
                {stockout_banner}
                {startup_banner}

                <table width="100%" cellpadding="0" cellspacing="0"
                       style="border-radius:10px;overflow:hidden;
                              border:1px solid #e5e7eb;font-size:14px;">
                  <thead>
                    <tr style="background:#f8fafc;">
                      <th style="padding:10px 14px;text-align:left;color:#6b7280;
                                 font-weight:600;border-bottom:2px solid #e5e7eb;">Product</th>
                      <th style="padding:10px 14px;text-align:left;color:#6b7280;
                                 font-weight:600;border-bottom:2px solid #e5e7eb;">Price</th>
                      <th style="padding:10px 14px;text-align:left;color:#6b7280;
                                 font-weight:600;border-bottom:2px solid #e5e7eb;">Status</th>
                    </tr>
                  </thead>
                  <tbody>{rows_html}</tbody>
                </table>

                <p style="margin:20px 0 0;font-size:12px;color:#9ca3af;text-align:center;">
                  Next check in a few minutes · 
                  <a href="{_site_url(site_name)}" style="color:#2563eb;">View products →</a>
                </p>
              </td>
            </tr>

            <!-- Footer -->
            <tr>
              <td style="background:#f8fafc;padding:16px 32px;text-align:center;
                         border-top:1px solid #e5e7eb;">
                <p style="margin:0;font-size:11px;color:#9ca3af;">
                  Amul Protein Tracker · Automated alert — do not reply
                </p>
              </td>
            </tr>

          </table>
        </td></tr>
      </table>
    </body>
    </html>
    """


def _build_text(site_name: str, products: list[dict], restocked: list[str], stockedout: list[str] = None) -> str:
    now   = datetime.now().strftime("%d %b %Y, %I:%M %p")
    lines = [
        f"{site_name} — Stock Status",
        f"Checked at: {now}",
        "=" * 50,
    ]
    if restocked:
        lines.append("🎉 RESTOCKED:")
        for r in restocked:
            lines.append(f"  ✅ {r}")
        lines.append("")
    if stockedout:
        lines.append("❌ SOLD OUT:")
        for r in stockedout:
            lines.append(f"  ❌ {r}")
        lines.append("")

    for p in products:
        icon = "✅" if p["status"] == "AVAILABLE" else "❌"
        lines.append(f"{icon}  {p['name']}")
        if p.get("price"):
            lines.append(f"     {p['price']}")

    return "\n".join(lines)


def _site_url(site_name: str) -> str:
    """Return a URL for the site name (fallback)."""
    if "amul" in site_name.lower():
        return "https://shop.amul.com/en/browse/protein"
    return "#"
