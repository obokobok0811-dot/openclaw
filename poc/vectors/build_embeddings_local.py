#!/usr/bin/env python3
"""Build local embeddings using sentence-transformers and FAISS
Reads contacts from DB and builds an embedding per contact (name + email + notes)
"""
import argparse
import sqlite3
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
import os

MODEL_NAME = 'all-MiniLM-L6-v2'


def load_contacts(db_path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute('SELECT id, name, canonical_email, notes FROM contacts')
    rows = cur.fetchall()
    return rows


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--db', default='poc/crm.db')
    p.add_argument('--index', default='poc/vectors/faiss.index')
    args = p.parse_args()

    os.makedirs(os.path.dirname(args.index), exist_ok=True)
    rows = load_contacts(args.db)
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
    faiss.write_index(index, args.index)
    # save id mapping
    with open(args.index + '.ids','w') as fh:
        for i in ids:
            fh.write(str(i)+"\n")
    print('FAISS index built at', args.index)

if __name__=='__main__':
    main()
