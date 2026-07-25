"""
query_engine.py — Moteur de requêtes Agrotech (100% live)
=========================================================

Orchestre les modules internes :
  - knowledge_base.py  → recherche live multi-sources
  - image_analyzer.py  → analyse d'images locale (OpenCV)

Remplace complètement les appels à l'API Gemini pour :
  - diagnose_plant(image, query) → diagnostic + traitement
  - ai_search(query)             → recherche agricole intelligente

Caractéristiques :
  - Correction orthographique automatique des noms de plantes
  - Classification d'intention (traitement, culture, identification)
  - Réponses structurées et fluides (pas de contenu brut)
  - 4 sources live : Wikipedia, Wikidata, OpenAlex, Trefle

Usage :
  >>> from ai_engine.query_engine import QueryEngine
  >>> engine = QueryEngine()
  >>> engine.search("comment cultiver le maïs")
  >>> engine.search("guérir le rhume")
  >>> engine.search("c'est quoi le manioc ?")
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
    Moteur de requêtes intelligent 100% live.

    Combine :
    - Recherche live multi-sources (Wikipedia, Wikidata, OpenAlex, Trefle)
    - Analyse d'image locale (OpenCV → diagnostic)
    - Correction orthographique automatique
    - Génération de réponse structurée par intention
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

    # ─── Classification d'intention ─────────────────────────────────

    INTENT_TREATMENT = {
        'guerir', 'guérir', 'soigner', 'soulager', 'traiter',
        'remède', 'remede', 'traitement', 'maladie',
        'rhume', 'toux', 'fievre', 'fièvre', 'grippe',
        'douleur', 'infection', 'inflammation', 'médicinal',
        'medicinal', 'medecine', 'médecine', 'bienfait',
        'vertu', 'vertus', 'symptome', 'symptômes',
    }

    INTENT_CULTIVATION = {
        'cultiver', 'culture', 'plantation', 'planter', 'semer',
        'recolter', 'récolter', 'arroser', 'fertiliser',
        'croissance', 'pousse', 'entretien', 'comment faire',
    }

    INTENT_IDENTIFICATION = {
        'c est', "c'est", "qu'est", 'quest ce',
        'definition', 'définition', 'decrire', 'décrire',
        'presenter', 'présenter', 'c quoi',
        'qu est', 'qui est',
    }

    @classmethod
    def _classify_intent(cls, query):
        """Classifie l'intention de la requête utilisateur."""
        q = query.lower().strip()

        for word_set, intent in [
            (cls.INTENT_IDENTIFICATION, 'identification'),
            (cls.INTENT_TREATMENT, 'treatment'),
            (cls.INTENT_CULTIVATION, 'cultivation'),
        ]:
            if any(w in q for w in word_set):
                return intent

        return 'general'

    # ─── Synthèse par intention ──────────────────────────────────────

    def _synthesize_answer(self, query, results):
        """Génère une réponse fluide et structurée selon l'intention."""
        if not results:
            return "Je n'ai pas trouvé d'information sur cette requête."

        intent = self._classify_intent(query)

        if intent == 'treatment':
            return self._answer_treatment(query, results)
        elif intent == 'cultivation':
            return self._answer_cultivation(query, results)
        elif intent == 'identification':
            return self._answer_identification(query, results)
        else:
            return self._answer_general(query, results)

    def _answer_treatment(self, query, results):
        """Réponse structurée pour les questions de santé / remèdes."""
        lines = []
        lines.append("🌿 **Plantes médicinales — Remèdes naturels**\n")

        # Extraire les plantes des résultats
        plant_sections = []
        seen_titles = set()
        for r in results[:5]:
            title = r.get('title', '')
            if title in seen_titles:
                continue
            seen_titles.add(title)
            content = (r.get('content', '') or r.get('summary', ''))[:400]

            source = r.get('source', '')
            emoji = '📖' if source == 'wikipedia_live' else '📊' if source == 'wikidata' else '📄' if source == 'openalex' else '🌱'

            # Extraire les parties pertinentes (propriétés, utilisations)
            useful = self._extract_relevant_sentences(content, [
                'propriété', 'propriete', 'utilisé', 'utilise',
                'traiter', 'soigner', 'soulager', 'vertu',
                'infusion', 'tisane', 'décoction', 'decoction',
                'remède', 'remede', 'médicinal', 'medicinal',
                'guérir', 'guerir', 'contre', 'efficace',
                'feuille', 'racine', 'fleur', 'écorce', 'ecorce',
            ])

            if useful:
                plant_sections.append(f"{emoji} **{title}** — {useful}")
            else:
                plant_sections.append(f"{emoji} **{title}**\n{content[:200]}")

        lines.extend(plant_sections)

        # Mode d'emploi général si trouvé
        prep_tips = []
        for r in results:
            content = (r.get('content', '') or r.get('summary', ''))
            for sentence in re.split(r'[.!?]', content):
                if any(w in sentence.lower() for w in
                       ['infusion', 'tisane', 'décoction', 'decoction',
                        'cataplasme', 'appliquer', 'boire', 'prendre',
                        'cuillère', 'tasse', 'feuille', 'racine']):
                    s = sentence.strip()
                    if len(s) > 20:
                        prep_tips.append(s)
                    if len(prep_tips) >= 3:
                        break
            if len(prep_tips) >= 3:
                break

        if prep_tips:
            lines.append("\n**🧑‍🌾 Mode d'emploi traditionnel :**")
            for tip in prep_tips[:3]:
                lines.append(f"• {tip.strip().capitalize()}.")

        lines.append("\n_⚠️ Ces informations sont données à titre indicatif. "
                     "Consultez un professionnel de santé avant utilisation._")

        return '\n'.join(lines)

    def _answer_cultivation(self, query, results):
        """Réponse structurée pour les questions de culture."""
        lines = []
        lines.append("🌱 **Guide de culture**\n")

        all_content = ' '.join(
            (r.get('content', '') or r.get('summary', ''))
            for r in results[:3]
        )

        # Détection de la plante principale
        main_plant = results[0].get('title', '') if results else ''
        if main_plant:
            lines.append(f"**{main_plant}**\n")

        # Description
        desc = self._extract_relevant_sentences(all_content, [
            'est une', 'est un', 'espèce', 'espece', 'variété',
            'variete', 'plante', 'herbacée', 'herbacee',
            'originaire', 'culture', 'cultivé', 'cultive',
        ])
        if desc:
            lines.append(f"📝 **Description :** {desc}")

        # Période / saison
        season = self._extract_relevant_sentences(all_content, [
            'période', 'periode', 'plantation', 'semer', 'semis',
            'printemps', 'été', 'automne', 'hiver', 'saison',
            'mois', 'janvier', 'février', 'mars', 'avril', 'mai',
            'juin', 'juillet', 'août', 'septembre', 'octobre',
            'novembre', 'décembre',
        ])
        if season:
            lines.append(f"\n📅 **Période :** {season}")

        # Sol / exposition
        soil = self._extract_relevant_sentences(all_content, [
            'sol', 'terre', 'drainé', 'draine', 'humide',
            'sableux', 'argileux', 'exposition', 'soleil',
            'ombre', 'ensoleillé', 'ensoleille', 'climat',
            'chaud', 'tempéré', 'tempere', 'tropical',
        ])
        if soil:
            lines.append(f"\n🌍 **Sol et exposition :** {soil}")

        # Entretien
        care = self._extract_relevant_sentences(all_content, [
            'arrosage', 'arroser', 'engrais', 'fertiliser',
            'entretien', 'taille', 'bouture', 'greffe',
            'maladie', 'ravageur', 'pesticide', 'traitement',
        ])
        if care:
            lines.append(f"\n🧑‍🌾 **Entretien :** {care}")

        # Récolte
        harvest = self._extract_relevant_sentences(all_content, [
            'récolte', 'recolte', 'récolter', 'recolter',
            'rendement', 'production',
        ])
        if harvest:
            lines.append(f"\n🌾 **Récolte :** {harvest}")

        return '\n'.join(lines)

    def _answer_identification(self, query, results):
        """Réponse structurée pour les questions d'identification."""
        lines = []
        lines.append("🔍 **Fiche d'identité**\n")

        all_content = ' '.join(
            (r.get('content', '') or r.get('summary', ''))
            for r in results[:5]
        )

        main_plant = results[0].get('title', '') if results else ''
        if main_plant:
            lines.append(f"**{main_plant}**\n")

        # Description générale
        desc = self._extract_relevant_sentences(all_content, [
            'est une', 'est un', 'espèce', 'espece', 'plante',
            'herbacée', 'herbacee', 'originaire', 'appartient',
            'famille', 'genre', 'nom scientifique',
        ])
        if desc:
            lines.append(f"📝 **Description :** {desc}")

        # Utilisations
        uses = self._extract_relevant_sentences(all_content, [
            'utilisé', 'utilise', 'utilisée', 'utilisee',
            'employé', 'employe', 'consommé', 'consomme',
            'aliment', 'cuisine', 'médicinal', 'medicinal',
            'industrie', 'artisanat', 'fourrage',
        ])
        if uses:
            lines.append(f"\n💡 **Utilisations :** {uses}")

        # Propriétés nutritionnelles / médicinales
        props = self._extract_relevant_sentences(all_content, [
            'riche en', 'contient', 'nutritif', 'vitamine',
            'minéral', 'mineraux', 'protéine', 'proteine',
            'calcium', 'fer', 'phosphore', 'potassium',
            'bienfait', 'propriété', 'propriete', 'vertu',
        ])
        if props:
            lines.append(f"\n⚕️ **Propriétés :** {props}")

        # Sources
        lines.append("\n**📚 Sources :**")
        seen = set()
        for r in results[:3]:
            t = r.get('title', '')
            if t not in seen:
                seen.add(t)
                s = r.get('source', 'wiki').replace('_live', '').replace('_', ' ')
                lines.append(f"• {t} ({s})")

        return '\n'.join(lines)

    def _answer_general(self, query, results):
        """Réponse structurée pour les questions générales."""
        lines = []
        lines.append("📚 **Résultats de la recherche**\n")

        seen_titles = set()
        for r in results[:4]:
            title = r.get('title', '')
            if title in seen_titles:
                continue
            seen_titles.add(title)
            content = (r.get('content', '') or r.get('summary', ''))[:350]
            source = r.get('source', 'wiki')
            emoji = {'wikipedia_live': '📖', 'wikidata': '📊',
                     'openalex': '📄', 'trefle': '🌱'}.get(source, '📎')

            # Extraire le début pertinent
            useful = self._extract_relevant_sentences(content, [
                'est une', 'est un', 'est le', 'est la',
                'désigne', 'constitue', 'représente',
                'représente', 'se dit', 's agit',
            ])
            if useful:
                lines.append(f"{emoji} **{title}** — {useful}")
            else:
                lines.append(f"{emoji} **{title}**\n{content[:250]}")

        # Sources additionnelles
        total = len(results)
        if total > 4:
            sources_count = {}
            for r in results:
                s = r.get('source', '?').replace('_live', '').replace('_', ' ')
                sources_count[s] = sources_count.get(s, 0) + 1
            detail = ', '.join(f"{c}× {s}" for s, c in sources_count.items())
            lines.append(f"\n_🔍 {total} résultats — {detail}_")

        return '\n'.join(lines)

    @staticmethod
    def _extract_relevant_sentences(text, keywords, max_sentences=3):
        """Extrait les phrases contenant des mots-clés pertinents."""
        if not text:
            return ''
        sentences = re.split(r'(?<=[.!?])\s+', text)
        matches = []
        for s in sentences:
            s_lower = s.lower().strip()
            if any(kw in s_lower for kw in keywords) and len(s) > 30:
                matches.append(s.strip())
                if len(matches) >= max_sentences:
                    break
        if matches:
            result = ' '.join(matches)
            return result[:500]
        # Fallback : les premières phrases
        first = [s.strip() for s in sentences if len(s.strip()) > 30][:2]
        return ' '.join(first)[:300] if first else ''

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
