# Hair by Pannu — WhatsApp Booking Bot

An AI-powered WhatsApp assistant for **Hair by Pannu**, a premium mobile hair salon in Abu Dhabi. Customers message the salon's WhatsApp number, and the bot handles greetings, service & pricing questions, and appointment booking — then notifies the admin when a booking is confirmed.

## How it works

```
Customer WhatsApp message
        │
        ▼
  UltraMsg webhook  →  Flask app (/webhook)
        │
        ▼
  GPT-4o-mini (via OpenRouter) — conversational flow:
    greet → ask name → services/pricing or booking flow → confirm
        │
        ▼
  Reply sent back via UltraMsg  +  admin notified on confirmed booking
```

- **Framework:** Flask
- **WhatsApp API:** [UltraMsg](https://ultramsg.com/)
- **AI model:** GPT-4o-mini via [OpenRouter](https://openrouter.ai/)
- **Hosting:** Render

## Features

- Natural-language greeting and service/price lookup (full price list for blow dry, haircuts, styling, treatments, coloring)
- Guided, one-question-at-a-time booking flow (service → date → time → location)
- Per-customer conversation memory (last 12 messages) so the bot keeps context
- Admin WhatsApp notification on every confirmed booking
- Simple `/book` REST endpoint and `/bookings` + `/admin` views for manual bookings and a lightweight dashboard

## Setup

1. Clone the repo and install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Copy `.env.example` to `.env` and fill in your keys (see below).
3. Run locally:
   ```bash
   python app.py
   ```
4. Point your UltraMsg instance's webhook at `https://<your-deployed-url>/webhook`.

### Environment variables

| Variable | Description |
|---|---|
| `ULTRAMSG_TOKEN` | API token from your UltraMsg instance |
| `ULTRAMSG_INSTANCE` | Your UltraMsg instance ID |
| `ADMIN_PHONE` | WhatsApp number (with country code, no `+`) to receive booking alerts |
| `OPENROUTER_API_KEY` | API key from [OpenRouter](https://openrouter.ai/) |

## Testing

`test_bot.sh` runs a smoke test against a deployed instance (bot alive check, webhook, booking creation, bookings list, admin dashboard):

```bash
./test_bot.sh
```

Update the base URL and any placeholder phone number in the script to match your own deployment before running.

## Notes / known limitations

- Bookings and chat sessions are currently stored **in memory** (a Python dict) — they reset on every restart or redeploy. This is fine for a demo/MVP; a production version would move this to a database (e.g. SQLite/Postgres).
- No authentication on `/admin` or `/bookings` — add access control before exposing this publicly at scale.

## License

MIT
