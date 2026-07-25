"""
knowledge_base.py — Moteur de connaissances Agrotech
===================================================

Concu pour Vercel (serverless) : zero dependance lourde.

Moteurs de recherche (5 sources) :
  1. TF‑IDF + Wikipedia indexe     → scikit-learn (leger, 25MB)
  2. Wikipedia live search          → API MediaWiki directe
  3. Wikidata                       → donnees structurees plantes
  4. OpenAlex                       → publications scientifiques
  5. ChromaDB + embeddings          → optionnel (requirements-advanced.txt)

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
    """Scraper Wikipedia pour le contenu agricole (zero dependance lourde)."""

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

    # Mots interrogatifs et verbes a ignorer dans les requetes
    STOPWORDS_FR = {
        'comment', 'pourquoi', 'quel', 'quelle', 'quels', 'quelles',
        'est', 'ce', 'que', 'qui', 'ou', 'dans', 'avec', 'pour',
        'sur', 'les', 'des', 'une', 'mon', 'ton', 'son', 'ma', 'ta', 'sa',
        'je', 'tu', 'il', 'elle', 'nous', 'vous', 'ils', 'elles',
        'au', 'aux', 'du', 'de', 'la', 'le', 'et', 'en', 'par',
        'pas', 'plus', 'tres', 'peu', 'beaucoup',
        'comment', 'faire', 'cultiver', 'planter', 'traiter', 'soigner',
        'recolter', 'arroser', 'fertiliser', 'nourrir',
        'peut', 'peux', 'veux', 'veut', 'vais', 'va', 'vas', 'vont',
        'donne', 'donner', 'avoir', 'etre', 'sont', 'suis',
    }

    def __init__(self, lang='fr'):
        self.lang = lang
        self._api = None

    # Mots generiques (action) vs mots porteurs de sens (noms)
    ACTION_VERBS = {
        'faire', 'cultiver', 'planter', 'traiter', 'soigner',
        'recolter', 'arroser', 'fertiliser', 'nourrir', 'preparer',
        'obtenir', 'ameliorer', 'augmenter', 'reduire', 'eliminer',
        'proteger', 'lutter', 'combattre', 'controler', 'gerer',
        'utiliser', 'appliquer', 'pulveriser', 'semer', 'repiquer',
        'taille', 'bouturer', 'greffer',
    }

    def _clean_query(self, query):
        """Extrait les mots-cles pertinents d'une question agricole.

        Garde les mots-porteurs de sens (noms de plantes, maladies, etc.),
        supprime les verbes d'action generiques et les mots interrogatifs.
        """
        words = query.lower().split()
        # Garder les mots qui ne sont ni stopwords ni verbes d'action
        meaningful = [w for w in words
                      if w not in self.STOPWORDS_FR
                      and w not in self.ACTION_VERBS
                      and len(w) > 2]

        # Si on a des mots porteurs de sens, les utiliser dans l'ordre
        if meaningful:
            return meaningful

        # Sinon, garder les mots les plus longs (sauf stopwords purs)
        fallback = [w for w in words if w not in self.STOPWORDS_FR and len(w) > 2]
        if fallback:
            return fallback

        # Dernier recours : juste enlever les stopwords courts
        return [w for w in words if len(w) > 2]

    def _try_queries(self, query):
        """Genere plusieurs formulations de recherche, de la plus specifique a la plus generale."""
        keywords = self._clean_query(query)

        queries = []
        # 1. Original (utile pour les questions precises)
        queries.append(query)

        # 2. Mots significatifs dans l'ordre original
        if keywords:
            q = ' '.join(keywords)
            if q != query:
                queries.append(q)

        # 3. Le premier mot-cle + contexte agricole
        #    (le premier mot-cle est le sujet principal apres nettoyage)
        if keywords:
            queries.append(f"{keywords[0]} agriculture")
            if len(keywords) >= 2:
                queries.append(f"{keywords[0]} {keywords[1]}")
            else:
                # Mot unique : essayer avec des contextes agricoles
                queries.append(f"culture {keywords[0]}")
                queries.append(f"plante {keywords[0]}")

        # Deduplicater (garde l'ordre)
        seen = set()
        unique = []
        for q in queries:
            ql = q.lower()
            if ql not in seen:
                seen.add(ql)
                unique.append(q)
        return unique

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
        """Recherche des articles Wikipedia via l'API MediaWiki directement."""
        return self._api_search(query, results)

    def _api_search(self, query, results=5):
        """Requete directe a l'API MediaWiki (evite les bugs du package wikipedia)."""
        import requests as req

        seen_titles = set()
        entries = []
        search_queries = self._try_queries(query)

        api_base = f"https://{self.lang}.wikipedia.org/w/api.php"

        session = req.Session()
        session.headers.update({
            'User-Agent': 'AgrotechAI/1.0 (agriculture bot; contact@agrotech.bj)'
        })

        for search_q in search_queries:
            if len(entries) >= results:
                break

            # 1. Opensearch : recherche de titres
            try:
                resp = session.get(api_base, params={
                    'action': 'opensearch',
                    'search': search_q,
                    'limit': results,
                    'namespace': 0,
                    'format': 'json',
                }, timeout=15)
                resp.raise_for_status()
                data = resp.json()
                titles = data[1] if len(data) > 1 else []
            except Exception as e:
                logger.warning(f"Wiki opensearch error for '{search_q}': {e}")
                continue

            if not titles:
                continue

            # 2. Pour chaque titre : recuperer le resume + contenu
            for title in titles:
                if title in seen_titles or len(entries) >= results:
                    continue
                seen_titles.add(title)

                try:
                    # Resumé + metadata
                    page_resp = session.get(api_base, params={
                        'action': 'query',
                        'titles': title,
                        'prop': 'extracts|info',
                        'exintro': 1,
                        'explaintext': 1,
                        'exsentences': 3,
                        'inprop': 'url',
                        'format': 'json',
                    }, timeout=15)
                    page_resp.raise_for_status()
                    page_data = page_resp.json()

                    pages = page_data.get('query', {}).get('pages', {})
                    page_id = next(iter(pages)) if pages else None
                    if not page_id or page_id == '-1' or not pages:
                        continue

                    page_info = pages[page_id]
                    summary = page_info.get('extract', '') or ''
                    page_url = page_info.get('fullurl', f"https://{self.lang}.wikipedia.org/wiki/{title.replace(' ', '_')}")

                    # Contenu complet
                    full_resp = session.get(api_base, params={
                        'action': 'query',
                        'titles': title,
                        'prop': 'extracts',
                        'explaintext': 1,
                        'format': 'json',
                    }, timeout=15)
                    full_resp.raise_for_status()
                    full_data = full_resp.json()
                    full_pages = full_data.get('query', {}).get('pages', {})
                    full_page_id = next(iter(full_pages)) if full_pages else None
                    full_content = ''
                    if full_page_id and full_page_id != '-1':
                        full_content = full_pages[full_page_id].get('extract', '') or ''

                    entries.append({
                        'title': page_info.get('title', title),
                        'summary': summary[:500],
                        'url': page_url,
                        'content': full_content,
                        'categories': [],
                    })
                except Exception as e:
                    logger.warning(f"Wiki page error for '{title}': {e}")
                    continue

        session.close()
        return entries


# ──────────────────── Wikidata scraper ────────────────────

class WikidataScraper:
    """Recherche Wikidata pour des informations structurées sur les plantes.

    Appels API directs (gratuits, sans clef) à l'API Wikidata.
    """

    PLANT_PROPERTIES = {
        'P225': 'Nom scientifique',
        'P171': 'Classification',
        'P185': 'Port de la plante',
        'P3518': 'Cycle de vie',
        'P3529': 'Hauteur',
        'P1576': 'Maladies / Ravageurs',
        'P1672': 'Produits dérivés',
        'P780': 'Traitements possibles',
    }

    def __init__(self, lang='fr'):
        self.lang = lang
        self.api_base = "https://www.wikidata.org/w/api.php"

    def search(self, query, results=3):
        """Recherche une plante dans Wikidata et retourne ses propriétés."""
        import requests as req

        # 1. Chercher les entités Wikidata correspondant au nom
        try:
            resp = req.get(self.api_base, params={
                'action': 'wbsearchentities',
                'search': query,
                'language': self.lang,
                'limit': results,
                'format': 'json',
            }, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            entities = data.get('search', [])
        except Exception as e:
            logger.warning(f"Wikidata search error: {e}")
            return []

        if not entities:
            return []

        entries = []
        for entity in entities:
            entity_id = entity.get('id', '')
            label = entity.get('label', query)
            description = entity.get('description', '')

            # 2. Récupérer toutes les propriétés de l'entité
            try:
                resp = req.get(self.api_base, params={
                    'action': 'wbgetentities',
                    'ids': entity_id,
                    'props': 'claims|descriptions|labels',
                    'languages': self.lang,
                    'format': 'json',
                }, timeout=10)
                resp.raise_for_status()
                entity_data = resp.json()
            except Exception:
                continue

            claims = {}
            try:
                claims = entity_data['entities'][entity_id].get('claims', {})
            except (KeyError, IndexError):
                pass

            # 3. Extraire les propriétés pertinentes pour l'agriculture
            found_props = {}
            for prop_id, prop_label in self.PLANT_PROPERTIES.items():
                if prop_id in claims:
                    values = []
                    for claim in claims[prop_id]:
                        try:
                            mainsnak = claim.get('mainsnak', {})
                            if mainsnak.get('snaktype') == 'value':
                                datavalue = mainsnak.get('datavalue', {})
                                value = datavalue.get('value', {})
                                if isinstance(value, dict):
                                    if 'text' in value:
                                        values.append(value['text'])
                                    elif 'id' in value:
                                        values.append(value['id'])
                                    else:
                                        values.append(str(value.get('amount', value)))
                                else:
                                    values.append(str(value))
                        except Exception:
                            continue
                    if values:
                        found_props[prop_label] = '; '.join(values[:3])

            # Construire le contenu
            parts = [f"**{label}**"]
            if description:
                parts.append(f"_{description}_")
            for prop_label, value in found_props.items():
                parts.append(f"• {prop_label}: {value}")

            entries.append({
                'title': f"📊 {label}",
                'summary': '\n'.join(parts[:3]),
                'content': '\n'.join(parts),
                'url': f"https://www.wikidata.org/wiki/{entity_id}",
                'source': 'wikidata',
                'score': 0.35,
            })

        return entries


# ──────────────────── OpenAlex scraper ────────────────────

class OpenAlexScraper:
    """Recherche OpenAlex pour des publications scientifiques agricoles.

    API gratuite, sans clef. Couvre 250M+ publications dont l'agriculture.
    """

    def __init__(self):
        self.base_url = "https://api.openalex.org"

    def search(self, query, results=5):
        """Recherche des articles scientifiques sur OpenAlex."""
        import requests as req

        try:
            resp = req.get(
                f"{self.base_url}/works",
                params={
                    'search': query,
                    'per_page': results,
                    'sort': 'relevance_score:desc',
                    'filter': 'is_paratext:false',
                },
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.warning(f"OpenAlex search error: {e}")
            return []

        entries = []
        for work in data.get('results', []):
            title = work.get('title', '')
            if not title:
                continue

            # Résumé (OpenAlex utilise un index inversé)
            abstract_idx = work.get('abstract_inverted_index', {})
            abstract = self._decode_abstract(abstract_idx) if abstract_idx else ''

            # Auteurs
            authorships = work.get('authorships', [])
            authors = [a.get('author', {}).get('display_name', '')
                       for a in authorships[:3] if a.get('author')]

            # Métadonnées
            pub_year = work.get('publication_year', '')
            doi = work.get('doi', '')
            url = (
                work.get('primary_location', {}).get('landing_page_url', '')
                or doi or ''
            )
            cited_by = work.get('cited_by_count', 0)

            # Domaines scientifiques
            concepts = [c.get('display_name', '')
                        for c in work.get('concepts', [])[:3]]

            content = f"{title}.\n"
            if abstract:
                content += abstract[:400] + '\n'
            if authors:
                content += f"Auteurs: {', '.join(authors)}\n"
            if concepts:
                content += f"Domaines: {', '.join(concepts)}\n"
            if pub_year:
                content += f"Année: {pub_year} | Cité {cited_by} fois"

            entries.append({
                'title': f"📄 {title}",
                'summary': abstract[:300] or title,
                'content': content,
                'url': url,
                'source': 'openalex',
                'score': 0.28,
            })

        return entries

    @staticmethod
    def _decode_abstract(inverted_index):
        """Decode un index inversé OpenAlex en texte lisible."""
        if not inverted_index:
            return ''
        try:
            pairs = []
            for word, positions in inverted_index.items():
                for pos in positions:
                    pairs.append((pos, word))
            pairs.sort(key=lambda x: x[0])
            return ' '.join(word for _, word in pairs)
        except Exception:
            return ''


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

    Sources (en parallele) :
      1. ChromaDB     → embeddings vectoriels (optionnel)
      2. TF‑IDF       → documents indexes (toujours)
      3. Wikipedia    → articles encyclopediques (direct API)
      4. Wikidata     → donnees structurees des plantes (nom scientifique, maladies...)
      5. OpenAlex     → publications scientifiques agricoles
    """

    def __init__(self):
        self.wiki = WikipediaScraper()
        self.wikidata = WikidataScraper()
        self.openalex = OpenAlexScraper()
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
        Recherche multi-sources :
        1. ChromaDB       → embeddings vectoriels
        2. TF‑IDF         → corpus local indexe
        3. Wikipedia      → articles encyclopediques
        4. Wikidata       → donnees structurees (noms scientifiques, maladies...)
        5. OpenAlex       → publications scientifiques
        """
        results = []
        seen_titles = set()

        # ── Sources locales (rapides) ──

        # Niveau 1 : ChromaDB (optionnel)
        if self.chroma.is_available():
            try:
                for r in self.chroma.search(query, top_k):
                    t = r.get('title', '')
                    if t not in seen_titles:
                        seen_titles.add(t)
                        results.append(r)
            except Exception as e:
                logger.warning(f"ChromaDB error: {e}")

        # Niveau 2 : TF‑IDF (corpus local)
        if self.tfidf.count > 0:
            try:
                for r in self.tfidf.search(query, top_k, min_score):
                    t = r.get('title', '')
                    if t not in seen_titles:
                        seen_titles.add(t)
                        results.append(r)
            except Exception as e:
                logger.warning(f"TF-IDF error: {e}")

        # ── Sources live (API externes, court timeout) ──

        # Niveau 3 : Wikipedia live
        try:
            for w in self.wiki.search(query, results=top_k):
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
            logger.warning(f"Wikipedia error: {e}")

        # Niveau 4 : Wikidata (donnees structurees des plantes)
        try:
            for wd in self.wikidata.search(query, results=3):
                title = wd.get('title', '')
                if title not in seen_titles:
                    seen_titles.add(title)
                    results.append({
                        'title': title,
                        'content': (wd.get('summary', '') or wd.get('content', ''))[:500],
                        'score': 0.35,
                        'source': 'wikidata',
                        'url': wd.get('url', ''),
                    })
        except Exception as e:
            logger.warning(f"Wikidata error: {e}")

        # Niveau 5 : OpenAlex (publications scientifiques)
        try:
            for oa in self.openalex.search(query, results=3):
                title = oa.get('title', '')
                if title not in seen_titles:
                    seen_titles.add(title)
                    results.append({
                        'title': title,
                        'content': (oa.get('summary', '') or oa.get('content', ''))[:500],
                        'score': 0.28,
                        'source': 'openalex',
                        'url': oa.get('url', ''),
                    })
        except Exception as e:
            logger.warning(f"OpenAlex error: {e}")

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
            'sources_wikidata': True,
            'sources_openalex': True,
            'mode': 'multi_sources' if not self.chroma.is_available() else 'chroma+multi',
        }
