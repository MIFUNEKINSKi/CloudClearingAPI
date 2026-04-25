#!/usr/bin/env python3
"""SMTP preflight check.

Loads .env exactly like run_weekly_java_monitor.py and attempts an SMTP
login (no message sent) so we can fail fast and loud before a long
weekly pipeline run.

Exit codes:
  0 - login OK
  1 - missing GMAIL_APP_PASSWORD or GMAIL_ADDRESS
  2 - SMTPAuthenticationError (bad credential / not an App Password)
  3 - other SMTP / network error
"""
import os
import sys
import smtplib
from pathlib import Path


def load_env():
    env_file = Path(__file__).resolve().parent.parent / '.env'
    if not env_file.exists():
        return
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()


def main() -> int:
    load_env()

    gmail_address = os.environ.get('GMAIL_ADDRESS', '')
    gmail_password = os.environ.get('GMAIL_APP_PASSWORD', '')

    if not gmail_address or not gmail_password:
        print('FAIL: GMAIL_ADDRESS or GMAIL_APP_PASSWORD missing in .env', file=sys.stderr)
        return 1

    pwd_compact = gmail_password.replace(' ', '')
    looks_like_app_password = (
        len(pwd_compact) == 16 and pwd_compact.isalpha() and pwd_compact.islower()
    )
    if not looks_like_app_password:
        print(
            f'WARN: GMAIL_APP_PASSWORD does not look like a Google App Password '
            f'(expected 16 lowercase letters, got {len(pwd_compact)} chars). '
            'Gmail SMTP will reject regular account passwords. '
            'Generate one at https://myaccount.google.com/apppasswords',
            file=sys.stderr,
        )

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=15) as server:
            server.login(gmail_address, gmail_password)
        print(f'OK: SMTP login succeeded for {gmail_address}')
        return 0
    except smtplib.SMTPAuthenticationError as e:
        print(f'FAIL: SMTPAuthenticationError {e.smtp_code} {e.smtp_error!r}', file=sys.stderr)
        print(
            'Gmail rejected the credential. Generate a new App Password at '
            'https://myaccount.google.com/apppasswords and put it in '
            '.env as GMAIL_APP_PASSWORD=<16 lowercase letters>',
            file=sys.stderr,
        )
        return 2
    except Exception as e:
        print(f'FAIL: SMTP error: {type(e).__name__}: {e}', file=sys.stderr)
        return 3


if __name__ == '__main__':
    sys.exit(main())
