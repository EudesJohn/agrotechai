"""
Management command : importe les articles Wikipedia dans la base de connaissances.

Usage :
  python manage.py build_knowledge_base              # Importe les plantes par défaut
  python manage.py build_knowledge_base --all         # Tout (plantes + maladies + catégories)
  python manage.py build_knowledge_base --query "riz" # Recherche personnalisée
  python manage.py build_knowledge_base --stats       # Affiche les stats seulement
  python manage.py build_knowledge_base --lang en     # Changer la langue (défaut: fr)
"""

import time
import logging
from django.core.management.base import BaseCommand, CommandError
from ai_engine.knowledge_base import KnowledgeBase, WikipediaScraper

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Importe des articles Wikipedia dans la base de connaissances locale Agrotech"

    def add_arguments(self, parser):
        parser.add_argument(
            '--all', action='store_true',
            help="Importe toutes les catégories (plantes, maladies, sujets agricoles)"
        )
        parser.add_argument(
            '--query', type=str, default='',
            help="Recherche Wikipedia personnalisée"
        )
        parser.add_argument(
            '--lang', type=str, default='fr',
            help="Langue Wikipedia (fr, en, etc.)"
        )
        parser.add_argument(
            '--stats', action='store_true',
            help="Affiche les statistiques sans importer"
        )
        parser.add_argument(
            '--limit', type=int, default=5,
            help="Nombre max d'articles par recherche (défaut: 5)"
        )

    def handle(self, *args, **options):
        lang = options['lang']
        show_stats = options['stats']
        import_all = options['all']
        custom_query = options['query']
        limit = options['limit']

        kb = KnowledgeBase()
        wiki = WikipediaScraper(lang=lang)

        if show_stats:
            stats = kb.get_stats()
            self.stdout.write(self.style.NOTICE("📊 Statistiques de la base de connaissances :"))
            for key, value in stats.items():
                label = key.replace('_', ' ').title()
                icon = "✅" if value else "❌" if isinstance(value, bool) else ""
                self.stdout.write(f"  {icon} {label}: {value}")
            return

        self.stdout.write(self.style.NOTICE(f"🌍 Construction de la base de connaissances (lang: {lang})..."))
        start = time.time()
        total_articles = 0

        # 1. Recherche personnalisée
        if custom_query:
            self.stdout.write(f"🔍 Recherche : {custom_query}")
            articles = wiki.search(custom_query, results=limit)
            if articles:
                kb.index_wikipedia_articles(articles)
                total_articles += len(articles)
                self.stdout.write(self.style.SUCCESS(f"   ✓ {len(articles)} articles importés"))
            else:
                self.stdout.write(self.style.WARNING("   ⚠ Aucun résultat"))

        # 2. Plantes spécifiques
        if import_all or not custom_query:
            self.stdout.write("🌱 Importation des plantes...")
            for i, plant in enumerate(wiki.SPECIFIC_PLANTS):
                self.stdout.write(f"   [{i+1}/{len(wiki.SPECIFIC_PLANTS)}] {plant}...", ending=' ')
                self.stdout.flush()
                articles = wiki.search(plant, results=2)
                if articles:
                    kb.index_wikipedia_articles(articles)
                    total_articles += len(articles)
                    self.stdout.write(self.style.SUCCESS(f"✓ ({len(articles)})"))
                else:
                    self.stdout.write(self.style.WARNING("⚠ aucun résultat"))
                time.sleep(0.5)  # Politesse Wikipedia

        # 3. Catégories agricoles (si --all)
        if import_all:
            self.stdout.write("\n📚 Importation des catégories agricoles...")
            for i, topic in enumerate(wiki.AGRI_TOPICS):
                self.stdout.write(f"   [{i+1}/{len(wiki.AGRI_TOPICS)}] {topic}...", ending=' ')
                self.stdout.flush()
                articles = wiki.search(topic, results=3)
                if articles:
                    kb.index_wikipedia_articles(articles)
                    total_articles += len(articles)
                    self.stdout.write(self.style.SUCCESS(f"✓ ({len(articles)})"))
                else:
                    self.stdout.write(self.style.WARNING("⚠ aucun résultat"))
                time.sleep(0.5)

        elapsed = time.time() - start
        stats = kb.get_stats()

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            f"\n✅ Importation terminée en {elapsed:.1f}s"
        ))
        self.stdout.write(f"   Articles importés : {total_articles}")
        self.stdout.write(f"   Chunks indexés   : {stats.get('chroma_count', 'N/A')}")
        self.stdout.write(f"   Documents TF-IDF : {stats.get('documents_cached', 0)}")
