#!/usr/bin/env python3
"""Quick Gmail checker via IMAP."""

import email
import imaplib
import os
from email.header import decode_header

# You'll need to set these env vars or update manually
IMAP_SERVER = "imap.gmail.com"
EMAIL = os.environ.get("GMAIL_EMAIL", "")
PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")


def check_gmail():
    if not EMAIL or not PASSWORD:
        print("Set env vars: GMAIL_EMAIL and GMAIL_APP_PASSWORD")
        print("\nTo get app password:")
        print("1. Go to https://myaccount.google.com/apppasswords")
        print("2. Create new app password for 'Mail'")
        print("3. Set: export GMAIL_EMAIL='your@email.com'")
        print("   export GMAIL_APP_PASSWORD='xxxx xxxx xxxx xxxx'")
        return

    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(EMAIL, PASSWORD)
        mail.select("inbox")

        # Get recent emails
        _status, messages = mail.search(None, "ALL")
        email_ids = messages[0].split()[-5:]  # Last 5 emails

        print(f"📧 Recent emails for {EMAIL}:\n")

        for eid in reversed(email_ids):
            _status, msg_data = mail.fetch(eid, "(RFC822)")
            if msg_data and isinstance(msg_data[0], tuple) and len(msg_data[0]) > 1:
                raw_email = msg_data[0][1]
                if isinstance(raw_email, bytes):
                    msg = email.message_from_bytes(raw_email)
                else:
                    continue
            else:
                continue

            # Subject
            subject = decode_header(msg["Subject"])[0][0]
            if isinstance(subject, bytes):
                subject = subject.decode()

            # From
            from_addr = decode_header(msg["From"])[0][0]

            print(f"From: {from_addr}")
            print(f"Subject: {subject}")
            print("-" * 50)

        mail.close()
        mail.logout()

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    check_gmail()
