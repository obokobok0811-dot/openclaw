#!/usr/bin/env python3
"""Build embeddings excluding noise contacts listed in poc/vectors/excluded_ids.json"""
import argparse
import sqlite3
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
import os
import json

MODEL_NAME = 'all-MiniLM-L6-v2'


def load_contacts(db_path, excluded_ids):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute('SELECT id, name, canonical_email, notes FROM contacts')
    rows = cur.fetchall()
    out = []
    for r in rows:
        cid = r[0]
        if cid in excluded_ids:
            continue
        out.append(r)
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--db', default='poc/crm.db')
    parser.add_argument('--index', default='poc/vectors/faiss.index')
    parser.add_argument('--excluded', default='poc/vectors/excluded_ids.json')
    args = parser.parse_args()

    excluded = []
    if os.path.exists(args.excluded):
        with open(args.excluded,'r') as fh:
            excluded = json.load(fh)

    rows = load_contacts(args.db, excluded)
    texts = []
    ids = []
    for r in rows:
        cid, name, email, notes = r
        txt = f"{name} {email or ''} {notes or ''}"
        texts.append(txt)
        ids.append(cid)

    model = SentenceTransformer(MODEL_NAME)
    embeddings = model.encode(texts, show_progress_bar=True)
    d = embeddings.shape[1]
    index = faiss.IndexFlatL2(d)
    index.add(np.array(embeddings).astype('float32'))
    os.makedirs(os.path.dirname(args.index), exist_ok=True)
    faiss.write_index(index, args.index)
    with open(args.index + '.ids','w') as fh:
        for i in ids:
            fh.write(str(i)+"\n")
    print('Filtered FAISS index built at', args.index)

if __name__=='__main__':
    main()
