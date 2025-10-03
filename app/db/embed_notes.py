import os
import pandas as pd
import psycopg
from dotenv import load_dotenv
from openai import AzureOpenAI

# Load environment variables
load_dotenv()

# Azure OpenAI client
client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
)
EMBED_MODEL = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")

# Postgres connection
conn = psycopg.connect(
    host=os.getenv("PGHOST"),
    port=os.getenv("PGPORT"),
    dbname=os.getenv("PGDATABASE"),
    user=os.getenv("PGUSER"),
    password=os.getenv("PGPASSWORD"),
    sslmode="require" if os.getenv("PGSSL", "true").lower() == "true" else "disable",
)

def get_embeddings_batch(texts):
    """Fetch embeddings in batch to reduce API calls."""
    resp = client.embeddings.create(model=EMBED_MODEL, input=texts)
    return [d.embedding for d in resp.data]

# Load CSV
df = pd.read_csv("data/claim_notes.csv")

# Process in batches of N (Azure recommends batching for speed)
BATCH_SIZE = 16
rows = df.to_dict("records")

with conn, conn.cursor() as cur:
    for i in range(0, len(rows), BATCH_SIZE):
        batch = rows[i : i + BATCH_SIZE]
        texts = [r["note_text"] for r in batch]
        embeddings = get_embeddings_batch(texts)

        for r, emb in zip(batch, embeddings):
            cur.execute(
                """
                INSERT INTO claim_notes (note_id, claim_id, note_text, embedding)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (note_id) DO UPDATE
                SET note_text = EXCLUDED.note_text,
                    embedding = EXCLUDED.embedding
                """,
                (int(r["note_id"]), int(r["claim_id"]), r["note_text"], emb),
            )

print(f"✅ Inserted/updated {len(rows)} claim notes with embeddings.")
