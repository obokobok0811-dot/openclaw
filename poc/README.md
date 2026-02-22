Personal CRM PoC

Overview
- Local embeddings with sentence-transformers
- Gmail + Google Calendar collectors (readonly)
- Box connector to link documents to contacts
- SQLite database (crm.db) + FAISS vector index
- Flask API for natural language queries
- Telegram reminders (bot token required in credentials)

Setup
1. Create virtualenv and activate
   python3 -m venv .venv
   source .venv/bin/activate
2. Install deps
   pip install -r poc/requirements.txt
3. Place credentials in workspace/credentials:
   - google_oauth_client.json (OAuth client for Gmail/Calendar)
   - box_token.json (Box developer token or config)
   - telegram_bot.json (optional, for reminders)
4. Run setup script
   bash poc/setup_poc.sh

Quick test
- Collect last 30 days: python poc/collectors/gmail_collector.py --since_days 30 --out data/gmail_30.jsonl
- Extract contacts: python poc/processor/extract_contacts.py --gmail data/gmail_30.jsonl --db poc/crm.db
- Build embeddings: python poc/vectors/build_embeddings_local.py --db poc/crm.db
- Start API: python poc/api/flask_app.py

Notes
- This PoC is for local testing. Review and secure credentials before production use.
