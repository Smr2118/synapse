# PubMed Ingestion Pipeline — Technical Documentation

## Overview

This pipeline collects fitness and nutrition research abstracts from PubMed, converts them into vector embeddings, and stores them in Pinecone for semantic retrieval. It is the data foundation for the RAG layer in Synapse.

---

## Pipeline stages

```
PubMed API
    │
    ▼
collect_pubmed.py       ← search + fetch raw abstracts
    │
    ▼
data/pubmed/*.txt       ← one file per abstract (local only, gitignored)
    │
    ▼
ingest_pubmed.py        ← POST /ingest for each file
    │
    ▼
/ingest endpoint        ← chunk + embed
    │
    ▼
OpenAI Embeddings API   ← text-embedding-3-small (1536 dimensions)
    │
    ▼
Pinecone Index          ← persistent vector storage
```

---

## Step 1 — `collect_pubmed.py`

### What it does

Queries the PubMed E-utilities API for abstracts across 12 fitness and nutrition topics, deduplicates by PMID, and saves each abstract as a plain text file.

### PubMed E-utilities API

Two endpoints are used:

**`esearch.fcgi`** — returns a list of PMIDs matching a search query:
```
GET https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi
    ?db=pubmed
    &term=protein+intake+muscle+protein+synthesis
    &retmax=40
    &retmode=json
    &sort=relevance
```

**`efetch.fcgi`** — fetches the full abstract text for a list of PMIDs:
```
GET https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi
    ?db=pubmed
    &id=12345678,87654321
    &rettype=abstract
    &retmode=text
```

### Topics searched

| Topic | Purpose |
|-------|---------|
| protein intake muscle protein synthesis | Core macronutrient science |
| resistance training hypertrophy | Strength training evidence |
| intermittent fasting weight loss | Diet protocols |
| carbohydrate timing athletic performance | Fuelling strategies |
| dietary fat metabolism body composition | Fat and body composition |
| creatine supplementation exercise | Supplementation evidence |
| omega-3 fatty acids inflammation exercise | Anti-inflammatory nutrition |
| sleep quality athletic recovery | Recovery science |
| hydration performance endurance | Hydration evidence |
| vitamin D deficiency athletic performance | Micronutrient evidence |
| caloric deficit muscle preservation | Cutting protocols |
| high protein diet satiety | Hunger and adherence |

### Output format

Each abstract is saved as `data/pubmed/{pmid}.txt`:

```
17. Eur J Clin Nutr. 1999 Jun;53(6):495-502.

Satiety related to 24 h diet-induced thermogenesis...

Author A, Author B.

OBJECTIVE: ...
RESULTS: ...
CONCLUSION: ...

PMID: 10403587 [Indexed for MEDLINE]
```

### Rate limiting

NCBI allows 3 requests/second without an API key. The script sleeps 0.4s between batches to stay within limits. PMIDs are deduplicated across topics — an abstract appearing in multiple search results is only saved once.

### Result

- **457 unique abstracts** across 12 topics
- No API key required
- Fully reproducible — re-running the script skips existing files

---

## Step 2 — `ingest_pubmed.py`

### What it does

Reads each `.txt` file and calls `POST /ingest` on the local or Render API. Tracks progress in `data/pubmed/ingested.log` so it can be safely interrupted and resumed.

### Usage

```bash
# Local server (must be running)
python scripts/ingest_pubmed.py

# Against Render
python scripts/ingest_pubmed.py --url https://synapse-5w9z.onrender.com
```

### Resumability

Successfully ingested PMIDs are appended to `ingested.log`. On re-run, those PMIDs are skipped. This means you can:
- Interrupt mid-run and resume without re-embedding already-processed abstracts
- Add new abstracts later and only ingest the new ones

---

## Step 3 — `/ingest` endpoint

### What it does

For each abstract received:

1. **Chunk** — splits the text into 200-word chunks with 20-word overlap using `chunk_text()`
2. **Embed** — calls OpenAI `text-embedding-3-small` to convert each chunk into a 1536-dimension vector
3. **Upsert** — stores each vector in Pinecone with:
   - `id`: `{document_id}#{chunk_index}` (e.g. `pubmed_10403587#0`)
   - `values`: the 1536-dimension embedding
   - `metadata`: `{text: chunk_text, document_id: document_id}`

### Why chunking?

A full abstract is ~250–400 words. Chunking with overlap ensures:
- No single chunk exceeds the embedding model's context window
- Chunks at boundaries don't lose context (overlap preserves continuity)
- Retrieval returns the most relevant passage, not the whole abstract

### Chunking parameters

| Parameter | Value | Reason |
|-----------|-------|--------|
| `CHUNK_SIZE` | 200 words | Fits comfortably within embedding context |
| `CHUNK_OVERLAP` | 20 words | Preserves context at chunk boundaries |

Most abstracts produce 1–3 chunks. Total vectors in Pinecone: ~600–900.

---

## Step 4 — Pinecone storage

### Index configuration

| Setting | Value |
|---------|-------|
| Index name | `synapse` |
| Dimensions | `1536` |
| Metric | `cosine` |
| Cloud | AWS us-east-1 |

### Why cosine similarity?

Cosine measures the angle between two vectors, not their magnitude. This works well for semantic text similarity — two chunks that discuss the same concept will have embeddings pointing in the same direction regardless of length.

### Vector structure

Each vector stored in Pinecone:
```json
{
  "id": "pubmed_10403587#0",
  "values": [0.012, -0.034, 0.891, ...],
  "metadata": {
    "text": "In lean women, satiety and DIT were synchronously higher...",
    "document_id": "pubmed_10403587"
  }
}
```

The `metadata.text` field is what gets retrieved and passed to the LLM as context in the RAG query step.

---

## Environment variables required

| Variable | Used by |
|----------|---------|
| `OPENAI_API_KEY` | `/ingest` — calls OpenAI embeddings API |
| `PINECONE_API_KEY` | `/ingest` — authenticates to Pinecone |
| `PINECONE_INDEX` | `/ingest` — index name (default: `synapse`) |

---

## Regenerating the data

```bash
# 1. Collect abstracts
python scripts/collect_pubmed.py

# 2. Start the API server
uvicorn main:app --host 127.0.0.1 --port 8000 --reload

# 3. Ingest into Pinecone
python scripts/ingest_pubmed.py
```

The pipeline is fully reproducible from scratch. `data/` is gitignored — the scripts are the source of truth.
