"""
knowledge_base.py — Moteur de recherche agricole 100% live
========================================================

Concu pour Vercel (serverless) : aucune dependance lourde (que requests).

Sources live (API directes) :
  1. Wikipedia → articles encyclopediques (API MediaWiki)
  2. Wikidata  → donnees structurees plantes
  3. OpenAlex  → publications scientifiques
  4. Trefle    → base botanique (clef API)

Usage :
  >>> from ai_engine.knowledge_base import KnowledgeBase
  >>> kb = KnowledgeBase()
  >>> kb.search("comment cultiver le maïs")
  [{"title": "Maïs", "content": "...", "score": 0.3}, ...]
"""

import os
import re
import json
import logging
import html
from pathlib import Path

logger = logging.getLogger(__name__)


# ──────────────────── Mapping symptomes → plantes medicinales ─────

REMEDIES = {
    # Rhume, refroidissement
    'rhume': ['gingembre', 'eucalyptus', 'menthe', 'thym', 'camomille',
              'tilleul', 'ail', 'oignon', 'citron', 'sureau'],
    'refroidissement': ['gingembre', 'eucalyptus', 'menthe', 'thym', 'camomille',
                        'tilleul', 'ail', 'oignon', 'citron', 'sureau'],
    # Toux
    'toux': ['thym', 'eucalyptus', 'coquelicot', 'guimauve', 'tussilage',
             'lierre', 'plantain', 'mauve'],
    # Fièvre
    'fievre': ['sureau', 'quinquina', 'menthe', 'camomille', 'tilleul',
               'saule', 'reine-des-pres'],
    'fièvre': ['sureau', 'quinquina', 'menthe', 'camomille', 'tilleul',
               'saule', 'reine-des-pres'],
    # Maux de tête
    'migraine': ['camomille', 'menthe poivree', 'grande camomille',
                 'tilleul', 'lavande', 'saule'],
    'mal de tete': ['camomille', 'menthe poivree', 'grande camomille',
                    'tilleul', 'lavande', 'saule'],
    # Maux de ventre / digestion
    'ventre': ['menthe', 'camomille', 'gingembre', 'fenouil', 'anis',
               'curcuma', 'aloes'],
    'digestion': ['menthe', 'camomille', 'gingembre', 'fenouil', 'anis',
                  'curcuma', 'artichaut', 'romarin'],
    'diarrhee': ['riz', 'carotte', 'coing', 'myrtille', 'mauve'],
    'constipation': ['sene', 'rhubarbe', 'lin', 'psyllium', 'pruneau'],
    # Paludisme
    'paludisme': ['quinquina', 'artemisia', 'neem', 'morinda'],
    'palu': ['quinquina', 'artemisia', 'neem', 'morinda'],
    # Vers intestinaux
    'vers': ['ail', 'absinthe', 'neem', 'tanaisie', 'semen-contra'],
    # Insomnie, stress
    'insomnie': ['camomille', 'tilleul', 'valeriane', 'passiflore',
                 'lavande', 'melisse'],
    'stress': ['camomille', 'tilleul', 'valeriane', 'passiflore',
               'lavande', 'melisse', 'millepertuis'],
    # Plaies, blessures
    'plaie': ['aloes', 'calendula', 'arnica', 'millepertuis', 'plantain',
              'consoude'],
    'blessure': ['aloes', 'calendula', 'arnica', 'millepertuis', 'plantain',
                 'consoude'],
    'coupure': ['aloes', 'calendula', 'arnica', 'plantain'],
    # Inflammation
    'inflammation': ['curcuma', 'camomille', 'consoude', 'arnica',
                     'reine-des-pres', 'harpagophytum'],
    'gonflement': ['curcuma', 'camomille', 'consoude', 'arnica'],
    # Problèmes de peau
    'peau': ['aloes', 'calendula', 'lavande', 'tea tree', 'camomille',
             'bourrache'],
    'acne': ['aloes', 'tea tree', 'calendula', 'lavande', 'camomille'],
    # Infections urinaires
    'urinaire': ['cranberry', 'prele', 'pissenlit', 'orthosiphon',
                 'queues de cerise'],
    # Anémie, fatigue
    'anemie': ['ortie', 'cresson', 'epinard', 'persil'],
    'fatigue': ['gingembre', 'ginseng', 'ortie', 'romarin', 'guarana',
                'moringa'],
}

# Termes qui indiquent une recherche de plante médicinale
HEALTH_KEYWORDS = {
    'guerir', 'guérir', 'soigner', 'traiter', 'soulager',
    'medicinal', 'médicinal', 'medecine', 'médecine', 'remède',
    'remede', 'plante medicinale', 'plante médicinale',
    'bienfait', 'bienfaits', 'vertu', 'vertus', 'propriete',
    'propriétés', 'proprietes', 'therapeutique', 'thérapeutique',
    'naturel', 'naturelle', 'naturels', 'traditionnel',
    'traditionnelle', 'africain', 'tradition',
}


# ──────────────────── Correcteur orthographique flou ─────────────

def _build_vocab():
    """Construit le vocabulaire connu (plantes, symptomes, mots-cles)."""
    words = set()
    # Plantes SPECIFIC_PLANTS
    plants_raw = [
        "neem", "moringa", "aloe vera", "gingembre", "curcuma",
        "cotonnier", "mais", "riz", "manioc", "igname", "arachide",
        "niebe", "sorgho", "millet", "tomate", "oignon", "piment",
        "aubergine", "gombo", "chou", "laitue", "carotte",
        "haricot", "soja", "palmier a huile", "cacaoyer", "cafier",
        "anacardier", "agrume", "manguier", "bananier", "ananas",
        "patate douce", "taro", "fonio",
    ]
    for p in plants_raw:
        for w in p.split():
            if len(w) > 3:
                words.add(w.lower())
    # Plantes des REMEDIES
    for plant_list in REMEDIES.values():
        for p in plant_list:
            for w in p.split():
                if len(w) > 3:
                    words.add(w.lower())
    # Symptomes
    for s in REMEDIES:
        for w in s.split():
            if len(w) > 3:
                words.add(w.lower())
    # Mots-cles agricoles
    agri_words = [
        "plante", "culture", "agricole", "agriculture", "cultiver",
        "recolte", "sol", "engrais", "irrigation", "pesticide",
        "maladie", "traitement", "phytotherapie", "medicinal",
        "remède", "remede", "naturel", "bienfait", "propriete",
        "guerir", "soigner", "soulager", "therapeutique",
        "plante", "feuille", "fleur", "fruit", "graine", "racine",
        "plantation", "semer", "arroser", "recolter", "fertiliser",
        "variete", "espece", "botanique", "jardin", "potager",
        "champ", "champs", "verger", "pépinière", "pépiniere",
        "application", "pulverisation", "lutte", "biologique",
        "insecte", "parasite", "ravageur", "phytopathologie",
    ]
    for w in agri_words:
        if len(w) > 3:
            words.add(w.lower())
    return words


_VOCAB = _build_vocab()


def _levenshtein(a, b):
    """Distance de Levenshtein entre deux chaines."""
    if len(a) < len(b):
        a, b = b, a
    if not b:
        return len(a)
    prev = range(len(b) + 1)
    for i, ca in enumerate(a):
        curr = [i + 1]
        for j, cb in enumerate(b):
            cost = 0 if ca == cb else 1
            curr.append(min(curr[j] + 1, prev[j + 1] + 1, prev[j] + cost))
        prev = curr
    return prev[-1]


def _correct_spelling(query, max_dist=2):
    """
    Corrige les fautes de frappe dans la requete en utilisant
    la distance de Levenshtein sur le vocabulaire connu.

    Exemples :
      "gingembre" (deja correct)  → "gingembre"
      "ginjembre" (faute)         → "gingembre"
      "origan"                    → "origan" (reste tel quel si inconnu)
    """
    words = query.lower().split()
    corrected = []
    for w in words:
        if len(w) <= 3 or w in _VOCAB:
            # Mot court ou deja connu → inchangé
            corrected.append(w)
            continue
        # Chercher le plus proche dans le vocabulaire
        best = None
        best_dist = max_dist + 1
        for v in _VOCAB:
            if abs(len(v) - len(w)) > max_dist:
                continue  # economie : les mots de taille tres differente
            d = _levenshtein(w, v)
            if d < best_dist:
                best_dist = d
                best = v
        if best and best_dist <= max_dist:
            corrected.append(best)
        else:
            corrected.append(w)
    result = ' '.join(corrected)
    if result != query.lower():
        logger.info(f"🔤 Correction orthographique : '{query}' → '{result}'")
    return result


# ──────────────────── Dependances optionnelles ────────────────────

HAS_WIKIPEDIA = False

try:
    import wikipedia
    HAS_WIKIPEDIA = True
except ImportError:
    try:
        import wikipediaapi
        HAS_WIKIPEDIA = True
    except ImportError:
        pass


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

    @staticmethod
    def _clean_query_static(query):
        """Version statique du nettoyage de requete (utilisable par WikidataScraper)."""
        words = query.lower().split()
        meaningful = [w for w in words
                      if w not in WikipediaScraper.STOPWORDS_FR
                      and w not in WikipediaScraper.ACTION_VERBS
                      and len(w) > 2]
        if meaningful:
            return meaningful
        fallback = [w for w in words if w not in WikipediaScraper.STOPWORDS_FR and len(w) > 2]
        if fallback:
            return fallback
        return [w for w in words if len(w) > 2]

    def _clean_query(self, query):
        """Extrait les mots-cles pertinents d'une question agricole.

        Garde les mots-porteurs de sens (noms de plantes, maladies, etc.),
        supprime les verbes d'action generiques et les mots interrogatifs.
        """
        return self._clean_query_static(query)

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

        # 4. Si la requete concerne un probleme de sante → plantes medicinales
        q_lower = query.lower()
        is_health_query = any(hk in q_lower for hk in HEALTH_KEYWORDS)
        if not is_health_query and keywords:
            is_health_query = any(kw in HEALTH_KEYWORDS for kw in keywords)
        # Verifier si un mot-cle ou la requete entiere contient un symptome connu
        has_symptom = any(kw.lower() in REMEDIES for kw in keywords) if keywords else False
        has_symptom = has_symptom or any(symptom in q_lower for symptom in REMEDIES)
        if is_health_query or has_symptom:
            # Chercher les plantes medicinales pour chaque symptome
            for symptom, plants in REMEDIES.items():
                if symptom in q_lower or symptom in keywords:
                    queries.append(f"plante medicinale {symptom}")
                    queries.append(f"plante pour soigner le {symptom}")
                    for plant in plants[:3]:  # top 3 plantes
                        queries.append(f"{plant} plante medicinale")
            # Fallback generique
            if not any(kw.lower() in REMEDIES for kw in keywords):
                queries.append("plante medicinale")
                if keywords:
                    queries.append(f"plante medicinale {keywords[0]}")

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

        # Extraire les mots-cles pour le filtrage de pertinence
        clean_keywords = self._clean_query(query)

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

                    # Filtre de pertinence : verifier que le contenu est agricole
                    check_text = (full_content or summary)[:300].lower()
                    has_title_match = any(
                        re.search(r'\b' + re.escape(kw.lower()) + r'\b', title.lower())
                        for kw in clean_keywords
                    )
                    is_relevant = (
                        has_title_match
                        or self._is_agricultural(check_text, keywords=clean_keywords)
                    )
                    if not is_relevant and len(entries) >= 1:
                        continue

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

    def _is_agricultural(self, text, keywords=None):
        """Verifie si un texte est pertinent pour l'agriculture ou la phytotherapie."""
        if not text:
            return False
        text_lower = text.lower()

        # Verifier si les mots-cles apparaissent comme mots entiers
        if keywords:
            for kw in keywords:
                if re.search(r'\b' + re.escape(kw.lower()) + r'\b', text_lower):
                    return True

        # Mots-cles agricoles generaux + plantes medicinales (fallback)
        AGRI_SIGNALS = {
            'céréale', 'cereale', 'plante', 'agriculture', 'agricole',
            'culture', 'cultivé', 'cultive', 'cultiver', 'cultivée',
            'récolte', 'recolte', 'récolté', 'recolter', 'grain',
            'graine', 'champ', 'champs', 'plantation', 'sol', 'terre',
            'engrais', 'irrigation', 'pesticide', 'variété', 'variete',
            'aliment', 'alimentaire', 'fourrage', 'céréalière',
            'cerealiere', 'maraîcher', 'maraicher', 'potager',
            'botanique', 'botany', 'agricultural', 'crop', 'plant',
            'farming', 'cultivation', 'harvest', 'fertiliser',
            'maladie', 'ravageur', 'traitement', 'phytopathologie',
            # Plantes medicinales
            'medicinal', 'médicinal', 'médicinale', 'medicinale',
            'therapeutique', 'thérapeutique', 'phytotherapie',
            'phytothérapie', 'remède', 'remede', 'guérison',
            'guerison', 'soulager', 'soigner', 'bienfait',
            'propriete', 'propriété', 'proprietes', 'propriétés',
            'vertu', 'vertus', 'afeection', 'maladie', 'symptome',
            'symptôme', 'traiter', 'infusion', 'tisane', 'decoction',
            'décoction', 'cataplasme', 'huile essentielle',
            'rhume', 'toux', 'fievre', 'fièvre', 'grippe',
            'digestion', 'migraine', 'insomnie', 'stress',
            'inflammation', 'infection', 'douleur',
        }
        return any(signal in text_lower for signal in AGRI_SIGNALS)


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
        self._session = None

    def _get_session(self):
        if self._session is None:
            import requests as req
            self._session = req.Session()
            self._session.headers.update({
                'User-Agent': 'AgrotechAI/1.0 (agriculture bot; contact@agrotech.bj)'
            })
        return self._session

    def search(self, query, results=3):
        """Recherche une plante dans Wikidata et retourne ses propriétés."""
        import requests as req
        session = self._get_session()

        # Nettoyer la requete : extraire les mots-cles significatifs
        clean = WikipediaScraper._clean_query_static(query)
        if not clean:
            return []
        search_words = ' '.join(clean[:3])  # max 3 mots

        # 1. Chercher les entités Wikidata correspondant au nom
        try:
            resp = session.get(self.api_base, params={
                'action': 'wbsearchentities',
                'search': search_words,
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

        # Mots-cles nettoyes pour le filtrage (respecte les diacritiques)
        clean_lower = [w.lower() for w in clean]

        entries = []
        for entity in entities:
            entity_id = entity.get('id', '')
            search_label = entity.get('label', query) or ''
            description = entity.get('description', '')

            # 2. Récupérer les propriétés + labels FR de l'entité
            try:
                resp = session.get(self.api_base, params={
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

            # Extraire le label en français depuis la réponse complète
            try:
                labels = entity_data['entities'][entity_id].get('labels', {})
                fr_label = labels.get(self.lang, {}).get('value', '') or ''
            except (KeyError, IndexError, AttributeError):
                fr_label = search_label

            # Filtre par label français (avec limites de mot)
            # Ex: "maïs" → garder "Maïs", rejeter "maison"
            # "tomates" → garder "Tomate" (singular)
            def _match_kw(kw_, lbl_):
                lbl_lower = lbl_.lower()
                # Mot entier
                if re.search(r'\b' + re.escape(kw_.lower()) + r'\b', lbl_lower):
                    return True
                # Variante singuliere (si mot pluriel)
                if kw_.endswith('s') and len(kw_) > 3:
                    sing = kw_[:-1]
                    if re.search(r'\b' + re.escape(sing) + r'\b', lbl_lower):
                        return True
                return False
            if not any(_match_kw(kw, fr_label) for kw in clean):
                continue

            # Utiliser le label FR pour l'affichage
            label = fr_label or search_label

            claims = {}
            try:
                claims = entity_data['entities'][entity_id].get('claims', {})
            except (KeyError, IndexError):
                pass

            # Récupérer la description française
            try:
                fr_desc = entity_data['entities'][entity_id].get('descriptions', {}).get(self.lang, {}).get('value', '')
                if fr_desc:
                    description = fr_desc
            except (KeyError, IndexError, AttributeError):
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
                'title': label,
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
                'title': title,
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


# ──────────────────── Trefle scraper ─────────────────────

class TrefleScraper:
    """Recherche Trefle.io pour des donnees botaniques detaillees.

    API specialisee dans les plantes (besoin d'une clef gratuite).
    https://trefle.io

    Pour obtenir une clef : https://trefle.io/signup
    Puis definissez TREFLE_API_KEY dans les variables d'environnement Vercel.
    """

    def __init__(self):
        self.api_key = os.getenv('TREFLE_API_KEY', '')
        self.base_url = "https://trefle.io/api/v1"

    @property
    def enabled(self):
        return bool(self.api_key)

    def search(self, query, results=5):
        """Recherche des plantes dans Trefle."""
        if not self.enabled:
            logger.info("Trefle desactive : definir TREFLE_API_KEY")
            return []

        import requests as req

        try:
            resp = req.get(
                f"{self.base_url}/plants/search",
                params={
                    'q': query,
                    'token': self.api_key,
                    'limit': results,
                },
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.warning(f"Trefle search error: {e}")
            return []

        entries = []
        for plant in data.get('data', [])[:results]:
            try:
                common_name = plant.get('common_name', '')
                scientific_name = plant.get('scientific_name', '')
                family = plant.get('family', '')
                year = plant.get('year', '')
                image_url = plant.get('image_url', '')

                # Donnees de croissance
                growth = plant.get('growth', {}) or {}
                specifications = plant.get('specifications', {}) or {}

                parts = [f"**{common_name or scientific_name}**"]
                if scientific_name:
                    parts.append(f"_{scientific_name}_")
                if family:
                    parts.append(f"Famille: {family}")
                if growth:
                    for key in ['days_to_harvest', 'growth_months', 'bloom_months', 'row_spacing', 'spread']:
                        val = growth.get(key)
                        if val:
                            parts.append(f"• {key.replace('_', ' ')}: {val}")
                if specifications:
                    for key in ['ligneous_type', 'growth_form', 'growth_rate', 'average_height']:
                        val = specifications.get(key)
                        if val:
                            parts.append(f"• {key.replace('_', ' ')}: {val}")

                entries.append({
                    'title': common_name or scientific_name,
                    'summary': '\n'.join(parts[:3]),
                    'content': '\n'.join(parts),
                    'url': f"https://trefle.io/plants/{plant.get('id', '')}",
                    'source': 'trefle',
                    'score': 0.25,
                })
            except Exception as e:
                logger.warning(f"Trefle parse error: {e}")
                continue

        return entries


# ──────────────────── Knowledge Base (orchestrateur live) ────────────────────

class KnowledgeBase:
    """
    Moteur de recherche agricole 100% live.

    Sources (APIs directes) :
      1. Wikipedia → articles encyclopediques (API MediaWiki)
      2. Wikidata  → donnees structurees des plantes
      3. OpenAlex  → publications scientifiques agricoles
      4. Trefle    → base botanique detaillee (clef API requise)
    """

    def __init__(self):
        self.wiki = WikipediaScraper()
        self.wikidata = WikidataScraper()
        self.openalex = OpenAlexScraper()
        self.trefle = TrefleScraper()

    def search(self, query, top_k=5, min_score=0.1):
        """
        Recherche live multi-sources :
        1. Wikipedia → articles encyclopediques
        2. Wikidata  → donnees structurees
        3. OpenAlex  → publications scientifiques
        4. Trefle    → base botanique
        """
        # Correction orthographique (fautes de frappe)
        query = _correct_spelling(query)

        results = []
        seen_titles = set()

        # ── Sources live (API externes) ──
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

        # Niveau 6 : Trefle (botanique detaillee)
        if self.trefle.enabled:
            try:
                for tr in self.trefle.search(query, results=3):
                    title = tr.get('title', '')
                    if title not in seen_titles:
                        seen_titles.add(title)
                        results.append({
                            'title': title,
                            'content': (tr.get('summary', '') or tr.get('content', ''))[:500],
                            'score': 0.25,
                            'source': 'trefle',
                            'url': tr.get('url', ''),
                        })
            except Exception as e:
                logger.warning(f"Trefle error: {e}")
        else:
            logger.info("Trefle desactive (TREFLE_API_KEY non definie)")

        # ── Sources live additionnelles : plantes medicinales ──
        # Quand la requete concerne un probleme de sante, chercher
        # les plantes medicinales specifiques qui le traitent.
        q_lower = query.lower()
        is_health = any(hk in q_lower for hk in HEALTH_KEYWORDS)
        matched_symptoms = [s for s in REMEDIES if s in q_lower]
        if is_health or matched_symptoms:
            plants_to_search = set()
            if matched_symptoms:
                for s in matched_symptoms:
                    for p in REMEDIES[s]:
                        plants_to_search.add(p)
            # Si aucun symptome specifique mais que c'est une requete sante,
            # chercher le mot-cle principal + plante medicinale
            if not plants_to_search:
                keywords = self.wiki._clean_query(query)
                if keywords:
                    plants_to_search.add(keywords[0])

            for plant in plants_to_search:
                if len(results) >= top_k * 2:  # ne pas saturer
                    break
                try:
                    for w in self.wiki.search(plant, results=2):
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
                    logger.warning(f"Plante medicinale '{plant}' error: {e}")

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

    def get_stats(self):
        """Statistiques de la base (100% live)."""
        return {
            'sources_wikipedia': True,
            'sources_wikidata': True,
            'sources_openalex': True,
            'sources_trefle': self.trefle.enabled,
            'mode': 'live_apis',
        }
