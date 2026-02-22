#!/usr/bin/env python3
"""Simple reminder runner: polls reminders table and sends Telegram messages for due reminders"""
import time
import sqlite3
import os
from datetime import datetime
import json

try:
    from telegram import Bot
    TELEGRAM_OK = True
except Exception:
    TELEGRAM_OK = False

DB='poc/crm.db'
TOKEN_PATH='credentials/telegram_bot.json'


def send_telegram(chat_id, text):
    if not TELEGRAM_OK:
        print('python-telegram-bot not installed')
        return
    with open(TOKEN_PATH,'r') as fh:
        cfg=json.load(fh)
    token = cfg.get('token')
    bot = Bot(token=token)
    bot.send_message(chat_id=chat_id, text=text)


def run_loop():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    while True:
        now = datetime.utcnow().isoformat()
        cur.execute("SELECT id,contact_id,title,body,due_at FROM reminders WHERE status='pending' AND due_at<=?",(now,))
        rows = cur.fetchall()
        for r in rows:
            rid, cid, title, body, due_at = r
            # send telegram to configured chat (here using pairing file)
            try:
                with open('credentials/telegram_pairing.json','r') as fh:
                    pair=json.load(fh)
                chat = pair.get('user_id')
            except Exception:
                chat=None
            msg = f"Reminder: {title}\n{body}\n(contact id: {cid})"
            if chat:
                send_telegram(chat, msg)
            cur.execute("UPDATE reminders SET status='done' WHERE id=?",(rid,))
            conn.commit()
        time.sleep(30)

if __name__=='__main__':
    run_loop()
