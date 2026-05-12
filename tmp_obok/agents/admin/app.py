#!/usr/bin/env python3
from flask import Flask, request, jsonify
import json, uuid, time, os

app = Flask(__name__)
WORKSPACE = os.path.join(os.path.dirname(__file__),'..','..','workspace')
TASK_QUEUE = os.path.join(WORKSPACE,'tasks.jsonl')

os.makedirs(WORKSPACE, exist_ok=True)

@app.route('/task', methods=['POST'])
def create_task():
    body = request.get_json() or {}
    task = {
        'task_id': str(uuid.uuid4()),
        'from': 'admin',
        'to': body.get('to','worker_fetcher'),
        'type': body.get('type','generic'),
        'payload': body.get('payload',{}),
        'created_at': int(time.time()),
        'status':'queued'
    }
    with open(TASK_QUEUE,'a',encoding='utf-8') as f:
        f.write(json.dumps(task,ensure_ascii=False)+'\n')
    return jsonify({'ok':True,'task':task})

@app.route('/health')
def health():
    return 'ok'

if __name__=='__main__':
    app.run(port=5100)
