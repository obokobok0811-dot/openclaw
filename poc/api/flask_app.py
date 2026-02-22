#!/usr/bin/env python3
from flask import Flask, request, jsonify
import faiss
import numpy as np
import sqlite3
from sentence_transformers import SentenceTransformer
import os

app = Flask(__name__)
MODEL_NAME = 'all-MiniLM-L6-v2'
MODEL = SentenceTransformer(MODEL_NAME)
INDEX_PATH = 'poc/vectors/faiss.index'
ID_MAP_PATH = INDEX_PATH + '.ids'

if os.path.exists(INDEX_PATH):
    index = faiss.read_index(INDEX_PATH)
    with open(ID_MAP_PATH,'r') as fh:
        id_map = [int(x.strip()) for x in fh.readlines()]
else:
    index = None
    id_map = []

DB_PATH = 'poc/crm.db'

@app.route('/query', methods=['POST'])
def query():
    data = request.json
    q = data.get('query')
    k = data.get('k',5)
    vec = MODEL.encode([q]).astype('float32')
    if index is None:
        return jsonify({'error':'no index found'}), 500
    D, I = index.search(vec, k)
    results = []
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    for dist, idx in zip(D[0], I[0]):
        cid = id_map[idx]
        cur.execute('SELECT id,name,canonical_email,company,role,notes FROM contacts WHERE id=?',(cid,))
        row = cur.fetchone()
        if row:
            results.append({'score': float(dist), 'contact': {'id':row[0],'name':row[1],'email':row[2],'company':row[3],'role':row[4],'notes':row[5]}})
    return jsonify({'results':results})

if __name__=='__main__':
    app.run(port=5000)
