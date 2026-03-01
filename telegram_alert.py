name: Daily Telegram Alert

on:
  schedule:
    # 9:00am AEDT (UTC+11) = 22:00 UTC
    # 9:00am AEST (UTC+10) = 23:00 UTC
    # Running at 23:00 UTC covers both daylight saving periods
    - cron: "0 23 * * 1-5"
  workflow_dispatch:  # allow manual trigger for testing

jobs:
  send-alert:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repo
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: pip install yfinance

      - name: Send Telegram alert
        env:
          TELEGRAM_TOKEN:   ${{ secrets.TELEGRAM_TOKEN }}
          TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
        run: python scripts/telegram_alert.py
