"""
query_engine.py — Moteur de requêtes Agrotech (remplace Gemini)
===========================================================

Orchestre les modules internes :
  - knowledge_base.py  → recherche Wikipedia + vector store
  - image_analyzer.py  → analyse d'images locale (OpenCV)

Remplace complètement les appels à l'API Gemini pour :
  - diagnose_plant(image, query) → diagnostic + traitement
  - ai_search(query)             → recherche agricole

Usage :
  >>> from ai_engine.query_engine import QueryEngine
  >>> engine = QueryEngine()
  >>> engine.diagnose_plant("https://exemple.com/feuille.jpg", "tomate")
  >>> engine.search("comment traiter le mildiou")
"""

import os
import re
import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Import des modules locaux (avec fallback silencieux)
try:
    from ai_engine.knowledge_base import KnowledgeBase
    HAS_KB = True
except ImportError:
    HAS_KB = False
    KnowledgeBase = None

try:
    from ai_engine.image_analyzer import ImageAnalyzer
    HAS_IMAGE = True
except ImportError:
    HAS_IMAGE = False
    ImageAnalyzer = None


class QueryEngine:
    """
    Moteur de requêtes intelligent qui combine :
    - Analyse d'image locale (OpenCV → diagnostic)
    - Base de connaissances (Wikipedia + ChromaDB)
    - Génération de réponse structurée sans API externe
    """

    def __init__(self):
        self.kb = KnowledgeBase() if HAS_KB and KnowledgeBase else None
        self.img = ImageAnalyzer() if HAS_IMAGE and ImageAnalyzer else None
        logger.info(
            "🧠 Moteur IA local initialisé "
            f"(KB={'✅' if self.kb else '❌'}, "
            f"Image={'✅' if self.img else '❌'})"
        )

    # ─── Diagnostiquer une plante par image ───────────────────────

    def diagnose_plant(self, image_url, plant_name=None):
        """
        Diagnostique une plante à partir d'une image.

        1. Analyse l'image (OpenCV → taches, couleurs, texture)
        2. Recherche la plante dans la base de connaissances
        3. Croise le diagnostic visuel avec les données Wikipedia
        4. Retourne un rapport structuré avec traitement recommandé

        Args:
            image_url: URL ou chemin de l'image
            plant_name: Nom de la plante (optionnel, pour enrichir)

        Retourne:
            dict avec diagnostic, traitement, sources
        """
        result = {
            'success': False,
            'plant': plant_name or 'Plante inconnue',
            'diagnosis': '',
            'details': [],
            'treatment': '',
            'treatment_steps': [],
            'sources': [],
            'confidence': 0,
        }

        # Étape 1 : Analyse d'image
        image_diagnosis = None
        if self.img:
            try:
                image_diagnosis = self.img.diagnose_plant(image_url, plant_name or '')
                logger.info(f"📸 Analyse d'image terminée : {image_diagnosis.get('status', '?')}")
            except Exception as e:
                logger.warning(f"⚠️ Analyse d'image échouée : {e}")

        # Étape 2 : Recherche dans la base de connaissances
        kb_results = []
        if self.kb:
            try:
                # Chercher la plante
                if plant_name:
                    kb_results = self.kb.search_plant_info(plant_name)

                # Chercher la maladie détectée
                if image_diagnosis and image_diagnosis.get('diagnosis'):
                    disease = image_diagnosis['diagnosis']
                    kb_disease = self.kb.search_disease_treatment(disease, plant_name or '')
                    kb_results.extend(kb_disease)
            except Exception as e:
                logger.warning(f"⚠️ Recherche KB échouée : {e}")

        # Étape 3 : Fusionner les résultats
        if image_diagnosis and image_diagnosis.get('success'):
            result['success'] = True
            result['status'] = image_diagnosis.get('status', 'indéterminé')
            result['diagnosis'] = image_diagnosis.get('diagnosis', '')
            result['confidence'] = image_diagnosis.get('confidence', 0)
            result['details'] = image_diagnosis.get('details', [])
            result['leaf_condition'] = image_diagnosis.get('leaf_condition', {})
            result['warnings'] = image_diagnosis.get('warnings', [])

            # Traitement prioritaire : de la KB si dispo, sinon de l'image
            if kb_results:
                # Extraire le traitement depuis les résultats KB
                treatments = self._extract_treatments(kb_results, result['diagnosis'])
                if treatments:
                    result['treatment'] = treatments[0]
                    result['treatment_steps'] = treatments
                else:
                    result['treatment'] = image_diagnosis.get('treatment', '')
            else:
                result['treatment'] = image_diagnosis.get('treatment', '')

            # Sources
            result['sources'] = [
                {
                    'title': r.get('title', ''),
                    'score': r.get('score', 0),
                    'source': r.get('source', ''),
                    'url': r.get('url', ''),
                }
                for r in kb_results[:5] if r.get('score', 0) > 0.1
            ]

        else:
            # Pas d'image → se fier à la KB uniquement
            if kb_results:
                result['success'] = True
                result['diagnosis'] = self._synthesize_from_kb(kb_results, plant_name)
                result['treatment'] = self._extract_first_treatment(kb_results)
                result['sources'] = [
                    {'title': r.get('title', ''), 'score': r.get('score', 0)}
                    for r in kb_results[:5]
                ]

        return result

    # ─── Recherche agricole textuelle ──────────────────────────────

    def search(self, query, top_k=5):
        """
        Recherche agricole en direct (APIs live).

        Interroge toutes les sources en temps reel :
          - Wikipedia (articles encyclopediques)
          - Wikidata (donnees structurees)
          - OpenAlex (publications scientifiques)
          - Trefle (botanique)

        Args:
            query: Question agricole (ex: "comment cultiver le maïs")
            top_k: Nombre de résultats

        Retourne:
            dict avec résultats, réponse synthétisée
        """
        result = {
            'success': False,
            'query': query,
            'results': [],
            'answer': '',
            'sources': [],
        }

        # Recherche live (Wikipedia + Wikidata + OpenAlex + Trefle)
        kb_results = []
        if self.kb:
            try:
                kb_results = self.kb.search(query, top_k=top_k)
                logger.info(f"🔍 Recherche live : {len(kb_results)} résultats")
            except Exception as e:
                logger.warning(f"⚠️ Recherche live échouée : {e}")

        # Toujours retourner les resultats (memes vides)
        result['success'] = True
        result['results'] = kb_results

        if kb_results:
            # Synthétiser une réponse
            result['answer'] = self._synthesize_answer(query, kb_results)
            result['sources'] = [
                {
                    'title': r.get('title', ''),
                    'score': round(r.get('score', 0), 3),
                    'source': r.get('source', ''),
                    'url': r.get('url', ''),
                }
                for r in kb_results if r.get('score', 0) > 0.1
            ]
        else:
            result['answer'] = "Je n'ai pas trouvé de résultat pour cette requête."

        return result

    # ─── Utilitaires ───────────────────────────────────────────────

    def _extract_treatments(self, kb_results, disease_name):
        """Extrait les traitements depuis les résultats KB."""
        treatments = []
        disease_lower = disease_name.lower()

        for r in kb_results:
            content = r.get('content', '')
            if not content:
                continue

            # Chercher les sections "traitement" ou "prévention"
            lines = content.split('\n')
            in_treatment = False
            for line in lines:
                line_lower = line.lower().strip()
                if any(word in line_lower for word in
                       ['traitement', 'remède', 'solution', 'prévention',
                        'treatment', 'cure', 'control', 'management']):
                    in_treatment = True
                    continue
                if in_treatment:
                    if line_lower and len(line) > 20:
                        treatments.append(line.strip())
                    if len(treatments) >= 3:
                        break

        return treatments[:3]

    def _extract_first_treatment(self, kb_results):
        """Extrait le premier traitement trouvé."""
        treatments = self._extract_treatments(kb_results, '')
        return treatments[0] if treatments else (
            "Consulter un agronome local pour un diagnostic précis"
        )

    def _synthesize_from_kb(self, kb_results, plant_name):
        """Synthétise un diagnostic à partir des résultats KB."""
        if not kb_results:
            return "Information non disponible"

        top = kb_results[0]
        title = top.get('title', '')
        content = top.get('content', '')[:300]

        return f"D'après {title} : {content}"

    def _synthesize_answer(self, query, results):
        """Génère une réponse lisible à partir des résultats (multi-sources)."""
        if not results:
            return "Je n'ai pas trouvé d'information sur cette requête."

        seen_titles = set()
        parts = []
        for r in results[:3]:
            title = r.get('title', '')
            if title in seen_titles:
                continue
            seen_titles.add(title)
            content = r.get('content', '')[:300]
            source = r.get('source', 'wikipedia')

            # Émoji selon la source
            emoji = {'wikipedia_live': '📖', 'wikidata': '📊', 'openalex': '📄', 'trefle': '🌱'}.get(source, '📎')
            parts.append(f"{emoji} **{title}**\n{content}\n")

        # Ajouter le nombre total de sources
        total = len(results)
        if total > 3:
            sources_count = {}
            for r in results:
                s = r.get('source', '?')
                sources_count[s] = sources_count.get(s, 0) + 1
            detail = ', '.join(f"{c} {s.replace('_live', '').replace('_', ' ')}" for s, c in sources_count.items())
            parts.append(f"\n_🔍 {total} résultats trouvés : {detail}_")

        return '\n'.join(parts)

    # ─── Stats ─────────────────────────────────────────────────────

    def get_stats(self):
        """Retourne les statistiques du moteur."""
        stats = {
            'has_knowledge_base': self.kb is not None,
            'has_image_analyzer': self.img is not None,
            'mode': 'local',
        }
        if self.kb:
            stats['kb_stats'] = self.kb.get_stats()
        return stats
