import os
from openai import AzureOpenAI
from .sql_tool import run_parameterized
from dotenv import load_dotenv

# Try to register pgvector adapter if available
try:
    from psycopg import connect
    from pgvector.psycopg import register_vector
    import psycopg

    # Optional: register globally so psycopg knows how to handle Python lists as vectors
    # You can also call register_vector(conn) after you open a connection in sql_tool.py
    register_vector(psycopg)
    _HAS_PGVECTOR = True
except ImportError:
    _HAS_PGVECTOR = False

load_dotenv()
client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
)
EMBED_MODEL = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")


def retrieve_similar_notes(query_text: str, k: int = 5):
    # Get embedding from Azure OpenAI
    resp = client.embeddings.create(model=EMBED_MODEL, input=query_text)
    emb = resp.data[0].embedding

    if _HAS_PGVECTOR:
        # pgvector adapter will handle Python list -> vector
        sql = """
        SELECT note_id, claim_id, note_text,
               embedding <=> %s AS distance
        FROM claim_notes
        ORDER BY distance ASC
        LIMIT %s;
        """
        return run_parameterized(sql, (emb, k))
    else:
        # Fall back: explicit cast to vector
        sql = """
        SELECT note_id, claim_id, note_text,
               embedding <=> %s::vector AS distance
        FROM claim_notes
        ORDER BY distance ASC
        LIMIT %s;
        """
        return run_parameterized(sql, (emb, k))
