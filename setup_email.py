"""
setup_email.py — Verify your Gmail App Password works before running the tracker.
Run: python3 setup_email.py
"""
import smtplib, sys, getpass
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

print("=" * 55)
print("  Amul Tracker — Gmail SMTP Setup")
print("=" * 55)
print()
print("You need a Gmail App Password (NOT your regular password).")
print("Steps:")
print("  1. Go to https://myaccount.google.com/apppasswords")
print("  2. Enable 2-Factor Authentication if not done yet")
print('  3. Create an App Password → select "Mail" + "Mac"')
print("  4. Copy the 16-character password (spaces don't matter)")
print()

email = input("Your Gmail address: ").strip()
password = getpass.getpass("Gmail App Password (hidden): ").strip().replace(" ", "")

print("\nTesting SMTP connection …")
try:
    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.ehlo()
        server.starttls()
        server.login(email, password)

        # Send test email
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "✅ Amul Tracker — Email setup successful!"
        msg["From"] = email
        msg["To"] = email
        msg.attach(MIMEText(
            "Your Amul Protein Tracker email is configured correctly.\n\n"
            "You will receive stock alerts at this address.",
            "plain"
        ))
        server.sendmail(email, email, msg.as_string())

    print()
    print("✅  Success! Test email sent to", email)
    print()
    print("Now paste this into config.yaml → email → sender_password:")
    print()
    print(f'  sender_password: "{password}"')
    print()

except smtplib.SMTPAuthenticationError:
    print()
    print("❌  Authentication failed!")
    print("    Make sure you used an APP PASSWORD, not your Gmail password.")
    print("    Get one at: https://myaccount.google.com/apppasswords")
    sys.exit(1)
except Exception as e:
    print(f"❌  Error: {e}")
    sys.exit(1)
