"""Local guideline retrieval. Uses FAISS + sentence-transformers when installed, else TF-IDF."""
import os
import re
from functools import lru_cache
from pathlib import Path

GL_DIR = Path(__file__).resolve().parent.parent / "data" / "guidelines"


def load_chunks():
    """Split each guideline file into sections that keep source, page, date and version."""
    out = []
    for p in sorted([*GL_DIR.glob("*.txt"), *GL_DIR.glob("*.md")]):
        meta, page, cur = {}, 1, None
        for line in p.read_text().splitlines():
            if m := re.match(r"(TITLE|VERSION|EFFECTIVE):\s*(.+)", line):
                meta[m[1].lower()] = m[2]
            elif line.startswith("# ") and "title" not in meta:
                meta["title"] = line[2:].strip()
            elif m := re.match(r"\[Page (\d+)\]", line):
                page = int(m[1])
            elif line.startswith("## "):
                cur = {"source": meta.get("title", p.stem), "section": line[3:].strip(), "page": page,
                       "effective_date": meta.get("effective", ""), "version": meta.get("version", ""),
                       "file": p.name, "text": ""}
                out.append(cur)
            elif cur and line.strip():
                cur["text"] += line.strip() + " "
    return out


class Index:
    def __init__(self, chunks):
        self.chunks, self.mode = chunks, "tfidf"
        texts = [c["section"] + ". " + c["text"] for c in chunks]
        if not texts:
            return
        try:  # semantic search is opt-in: set USE_EMBEDDINGS=1
            if os.getenv("USE_EMBEDDINGS") != "1":
                raise RuntimeError("embeddings disabled")
            import faiss
            from sentence_transformers import SentenceTransformer
            self.m = SentenceTransformer("all-MiniLM-L6-v2")
            e = self.m.encode(texts, normalize_embeddings=True).astype("float32")
            self.ix = faiss.IndexFlatIP(e.shape[1])
            self.ix.add(e)
            self.mode = "faiss"
        except Exception:
            # Fast keyword fallback, no downloads
            from sklearn.feature_extraction.text import TfidfVectorizer
            self.v = TfidfVectorizer(stop_words="english")
            self.X = self.v.fit_transform(texts)

    def search(self, q, k=3):
        if not self.chunks:
            return []
        if self.mode == "faiss":
            s, i = self.ix.search(self.m.encode([q], normalize_embeddings=True).astype("float32"), k)
            pairs = list(zip(i[0], s[0]))
        else:
            sims = (self.X @ self.v.transform([q]).T).toarray().ravel()
            pairs = [(j, sims[j]) for j in sims.argsort()[::-1][:k]]
        return [{**self.chunks[j], "score": round(float(s), 3)} for j, s in pairs if j >= 0 and s > 0.05]


@lru_cache(maxsize=1)
def get_index():
    return Index(load_chunks())


def search(q, k=3):
    return get_index().search(q, k)