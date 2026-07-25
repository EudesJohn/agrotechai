"""
knowledge_base.py — Moteur de connaissances Agrotech
===================================================

Concu pour Vercel (serverless) : zero dependance lourde.

Moteurs de recherche :
  1. TF‑IDF + Wikipedia indexe   → scikit-learn (leger, 25MB)
  2. Wikipedia live search        → requetes HTTP (zero dep)
  3. ChromaDB + embeddings        → optionnel (requirements-advanced.txt)

Usage :
  >>> from ai_engine.knowledge_base import KnowledgeBase
  >>> kb = KnowledgeBase()
  >>> kb.search("comment traiter le mildiou sur les tomates")
  [{"title": "Mildiou", "content": "...", "score": 0.85}, ...]
"""

import os
import re
import json
import logging
import html
from pathlib import Path

logger = logging.getLogger(__name__)


# ──────────────────── Dependances optionnelles ────────────────────

HAS_WIKIPEDIA = False
HAS_TRANSFORMERS = False
HAS_CHROMA = False
HAS_SKLEARN = False

try:
    import wikipedia
    HAS_WIKIPEDIA = True
except ImportError:
    try:
        import wikipediaapi
        HAS_WIKIPEDIA = True
    except ImportError:
        pass

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    HAS_SKLEARN = True
except ImportError:
    pass

try:
    from sentence_transformers import SentenceTransformer
    HAS_TRANSFORMERS = True
except ImportError:
    pass

try:
    import chromadb
    from chromadb.config import Settings
    HAS_CHROMA = True
except ImportError:
    pass


# ──────────────────── Configuration ────────────────────

BASE_DIR = Path(__file__).resolve().parent.parent

# Vercel : seul /tmp est accessible en ecriture
if os.getenv('VERCEL', '') == '1' or os.getenv('VERCEL_ENV', ''):
    DATA_DIR = Path('/tmp') / 'data' / 'knowledge'
else:
    DATA_DIR = BASE_DIR / 'data' / 'knowledge'

# ChromaDB : desactive sur Vercel (disque ephemere) sauf si force
CHROMA_ENABLED = os.getenv('CHROMA_ENABLED', 'False') == 'True'
CHROMA_DIR = DATA_DIR / 'chroma'

os.makedirs(DATA_DIR, exist_ok=True)


# ──────────────────── Wikipedia scraper ────────────────────

class WikipediaScraper:
    """Scraper Wikipedia pour le contenu agricole (zerf dependance lourde)."""

    AGRI_TOPICS = [
        "plante medicinale", "agriculture", "culture", "maladie des plantes",
        "agriculture au Benin", "agriculture en Afrique", "sol", "engrais",
        "irrigation", "pesticide naturel", "permaculture", "agroecologie",
        "coton", "mais", "riz", "manioc", "igname", "maraichage",
        "arboriculture", "horticulture", "phytopathologie",
        "insecte ravageur", "lutte biologique",
    ]

    SPECIFIC_PLANTS = [
        "neem", "moringa", "aloe vera", "gingembre", "curcuma",
        "cotonnier", "mais", "riz", "manioc", "igname", "arachide",
        "niebe", "sorgho", "millet", "tomate", "oignon", "piment",
        "aubergine", "gombo", "chou", "laitue", "carotte",
        "haricot", "soja", "palmier a huile", "cacaoyer", "cafier",
        "anacardier", "agrume", "manguier", "bananier", "ananas",
        "patate douce", "taro", "fonio",
    ]

    def __init__(self, lang='fr'):
        self.lang = lang
        self._api = None

    @property
    def api(self):
        if self._api is None and not HAS_WIKIPEDIA:
            try:
                import wikipediaapi
                self._api = wikipediaapi.Wikipedia(
                    language=self.lang,
                    user_agent='AgrotechAI/1.0 (agriculture bot; contact@agrotech.bj)'
                )
                return self._api
            except ImportError:
                pass
        return None

    def search(self, query, results=5):
        """Recherche des articles Wikipedia (via lib ou HTTP)."""
        if HAS_WIKIPEDIA:
            import wikipedia
            try:
                wikipedia.set_lang(self.lang)
                titles = wikipedia.search(query, results=results)
                entries = []
                for title in titles:
                    try:
                        summary = wikipedia.summary(title, sentences=3)
                        page = wikipedia.page(title)
                        entries.append({
                            'title': title,
                            'summary': summary,
                            'url': page.url,
                            'content': page.content,
                            'categories': [c for c in page.categories if 'Categorie' not in c],
                        })
                    except Exception:
                        continue
                return entries
            except Exception as e:
                logger.warning(f"Wikipedia search error: {e}")
                return []

        # Fallback wikipediaapi
        api = self.api
        if api:
            page = api.page(query)
            if page.exists():
                return [{
                    'title': page.title,
                    'summary': page.summary[:500],
                    'url': page.fullurl,
                    'content': page.text,
                    'categories': [],
                }]
        return []


# ──────────────────── TF‑IDF Engine (moteur principal) ────────────────────

class TfidfEngine:
    """
    Moteur de recherche TF‑IDF.
    Fonctionne partout : Python pur + scikit-learn (25MB).
    """

    def __init__(self, language='french'):
        self.language = language
        self.documents = []
        self.metadatas = []
        self._vectorizer = None
        self._matrix = None

    def index(self, texts, metadatas=None):
        """Ajoute des documents a l'index."""
        if not texts:
            return
        self.documents.extend(texts)
        self.metadatas.extend(metadatas or [{}] * len(texts))
        self._vectorizer = None
        self._matrix = None
        logger.info(f"TF-IDF : {len(texts)} documents indexes (total: {len(self.documents)})")

    def search(self, query, top_k=5, min_score=0.1):
        """Recherche les documents les plus pertinents."""
        if not self.documents or not HAS_SKLEARN:
            return []

        try:
            corpus = self.documents + [query]
            self._vectorizer = TfidfVectorizer(
                max_features=5000,
                stop_words=self.language,
            )
            self._matrix = self._vectorizer.fit_transform(corpus)
            similarities = cosine_similarity(self._matrix[-1:], self._matrix[:-1]).flatten()

            top_indices = similarities.argsort()[-top_k:][::-1]
            results = []
            for idx in top_indices:
                score = float(similarities[idx])
                if score < min_score:
                    continue
                meta = self.metadatas[idx] if idx < len(self.metadatas) else {}
                results.append({
                    'title': meta.get('title', f'Document {idx}'),
                    'content': self.documents[idx][:500],
                    'score': round(score, 3),
                    'source': 'tfidf',
                    'url': meta.get('url', ''),
                })
            return results
        except Exception as e:
            logger.warning(f"TF-IDF search error: {e}")
            return []

    def clear(self):
        """Vide l'index."""
        self.documents = []
        self.metadatas = []
        self._vectorizer = None
        self._matrix = None

    @property
    def count(self):
        return len(self.documents)


# ──────────────────── ChromaDB Engine (optionnel, Vercel Pro+) ─────────────

class ChromaEngine:
    """Moteur vectoriel ChromaDB. Necessite chromadb + sentence-transformers."""

    def __init__(self):
        self._collection = None
        self._model = None

    def is_available(self):
        return HAS_CHROMA and HAS_TRANSFORMERS and CHROMA_ENABLED

    def _get_collection(self):
        if self._collection is None and self.is_available():
            try:
                os.makedirs(CHROMA_DIR, exist_ok=True)
                client = chromadb.PersistentClient(
                    path=str(CHROMA_DIR),
                    settings=Settings(anonymized_telemetry=False)
                )
                self._collection = client.get_or_create_collection(
                    name="agrotech_knowledge",
                    metadata={"hnsw:space": "cosine"}
                )
            except Exception as e:
                logger.warning(f"ChromaDB init error: {e}")
        return self._collection

    def _get_model(self):
        if self._model is None and HAS_TRANSFORMERS:
            try:
                model_name = os.getenv('EMBEDDING_MODEL', 'all-MiniLM-L6-v2')
                self._model = SentenceTransformer(model_name)
            except Exception as e:
                logger.warning(f"Embedding model error: {e}")
        return self._model

    def index(self, texts, metadatas=None, ids=None):
        col = self._get_collection()
        model = self._get_model()
        if not col or not model:
            return

        try:
            embeddings = model.encode(texts).tolist()
            col.add(
                documents=texts,
                metadatas=metadatas or [{}] * len(texts),
                ids=ids or [str(hash(t)) for t in texts],
                embeddings=embeddings,
            )
        except Exception as e:
            logger.warning(f"ChromaDB add error: {e}")

    def search(self, query, top_k=5):
        col = self._get_collection()
        model = self._get_model()
        if not col or not model:
            return []

        try:
            query_embedding = model.encode(query).tolist()
            r = col.query(query_embeddings=[query_embedding], n_results=top_k)

            results = []
            if r and r.get('documents') and r['documents']:
                for i, doc in enumerate(r['documents'][0]):
                    meta = (r.get('metadatas', [[]])[0] or [{}])[i] if r.get('metadatas') else {}
                    score = (r.get('distances', [[]])[0] or [0])[i]
                    results.append({
                        'title': meta.get('title', 'Article') if meta else 'Article',
                        'content': doc,
                        'score': round(1.0 - min(score, 1.0), 3),
                        'source': 'chroma',
                    })
            return results
        except Exception as e:
            logger.warning(f"ChromaDB search error: {e}")
            return []

    @property
    def count(self):
        col = self._get_collection()
        if col:
            try:
                return col.count()
            except Exception:
                pass
        return 0


# ──────────────────── Knowledge Base (orchestrateur) ────────────────────

class KnowledgeBase:
    """
    Moteur de connaissances Agrotech.

    Ordre de recherche :
      1. ChromaDB (si activee + deps installees)
      2. TF‑IDF  (toujours dispo avec scikit-learn)
      3. Wikipedia live (toujours dispo)
    """

    def __init__(self):
        self.wiki = WikipediaScraper()
        self.tfidf = TfidfEngine()
        self.chroma = ChromaEngine()

    def index_texts(self, texts, metadatas=None, ids=None):
        """Indexe des textes dans tous les moteurs disponibles."""
        if not texts:
            return

        # TF-IDF (toujours)
        self.tfidf.index(texts, metadatas)

        # ChromaDB (si disponible)
        if self.chroma.is_available():
            self.chroma.index(texts, metadatas, ids)

    def index_wikipedia_articles(self, articles):
        """Indexe les articles Wikipedia."""
        texts = []
        metadatas = []
        ids = []

        for i, article in enumerate(articles):
            content = article.get('content', '') or article.get('summary', '')
            if len(content) < 50:
                continue

            chunks = self._chunk_text(content, 500)
            for j, chunk in enumerate(chunks):
                texts.append(chunk)
                metadatas.append({
                    'title': article.get('title', 'Inconnu'),
                    'source': 'wikipedia',
                    'url': article.get('url', ''),
                })
                ids.append(f"wiki_{i}_{j}")

        self.index_texts(texts, metadatas, ids)
        logger.info(f"Wikipedia : {len(articles)} articles indexes ({len(texts)} chunks)")

    def search(self, query, top_k=5, min_score=0.1):
        """
        Recherche multi-niveaux :
        1. ChromaDB (embeddings vectoriels) — si installe + active
        2. TF‑IDF (documents indexes) — toujours dispo
        3. Wikipedia live — toujours dispo
        """
        results = []
        seen_titles = set()

        # Niveau 1 : ChromaDB (optionnel, performant)
        if self.chroma.is_available():
            chroma_results = self.chroma.search(query, top_k)
            for r in chroma_results:
                if r.get('title') not in seen_titles:
                    seen_titles.add(r['title'])
                    results.append(r)

        # Niveau 2 : TF‑IDF (moteur principal, toujours dispo)
        if self.tfidf.count > 0:
            tfidf_results = self.tfidf.search(query, top_k, min_score)
            for r in tfidf_results:
                if r.get('title') not in seen_titles:
                    seen_titles.add(r['title'])
                    results.append(r)

        # Niveau 3 : Wikipedia live (complement)
        try:
            wiki_results = self.wiki.search(query, results=top_k)
            for w in wiki_results:
                title = w.get('title', '')
                if title not in seen_titles:
                    seen_titles.add(title)
                    results.append({
                        'title': title,
                        'content': (w.get('summary', '') or w.get('content', ''))[:500],
                        'score': 0.3,
                        'source': 'wikipedia_live',
                        'url': w.get('url', ''),
                    })
        except Exception as e:
            logger.warning(f"Wikipedia live error: {e}")

        # Trier par score descendant
        results.sort(key=lambda x: x.get('score', 0), reverse=True)
        return results[:top_k]

    def search_plant_info(self, plant_name):
        """Informations sur une plante."""
        query = f"{plant_name} plante culture agricole"
        results = self.search(query, top_k=5)

        if not results or results[0].get('score', 0) < 0.2:
            try:
                wiki_results = self.wiki.search(f"{plant_name} plante", results=3)
                for w in wiki_results:
                    content = w.get('content', '') or w.get('summary', '')
                    if content and len(content) > 100:
                        results.insert(0, {
                            'title': w.get('title', plant_name),
                            'content': content[:1000],
                            'score': 0.5,
                            'source': 'wikipedia_live',
                            'url': w.get('url', ''),
                        })
            except Exception:
                pass

        return results

    def search_disease_treatment(self, disease_name, plant_name=""):
        """Traitement pour une maladie."""
        query = f"{disease_name} {plant_name} traitement maladie plante"
        return self.search(query, top_k=5)

    # ── Utilitaires ──

    @staticmethod
    def _chunk_text(text, chunk_size=500):
        words = text.split()
        chunks = []
        for i in range(0, len(words), chunk_size):
            chunk = ' '.join(words[i:i + chunk_size])
            if chunk.strip():
                chunks.append(chunk)
        return chunks if chunks else [text]

    def get_stats(self):
        """Statistiques de la base."""
        return {
            'tfidf_documents': self.tfidf.count,
            'chroma_connected': self.chroma.is_available(),
            'chroma_documents': self.chroma.count if self.chroma.is_available() else 0,
            'has_sklearn': HAS_SKLEARN,
            'has_wikipedia': HAS_WIKIPEDIA,
            'has_chroma': HAS_CHROMA,
            'has_transformers': HAS_TRANSFORMERS,
            'chroma_enabled': CHROMA_ENABLED,
            'mode': 'tfidf' if not self.chroma.is_available() else 'chroma',
        }
