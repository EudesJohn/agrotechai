"""
Management command (obsolete) : les recherches sont 100% live.

Les recherches utilisent desormais les APIs en direct (Wikipedia + Wikidata +
OpenAlex + Trefle). L'indexation locale (TF-IDF / ChromaDB) n'est plus
necessaire. Cette commande ne fait rien — elle existe pour la retrocompatibilite.

Voir : ai_engine.knowledge_base.KnowledgeBase.search()
"""

import logging
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "OBSOLETE — Les recherches sont 100% live (plus d'indexation locale)"

    def add_arguments(self, parser):
        parser.add_argument(
            '--all', action='store_true', help='Ignore (obsolète)'
        )
        parser.add_argument(
            '--query', type=str, default='', help='Ignore (obsolète)'
        )
        parser.add_argument(
            '--lang', type=str, default='fr', help='Ignore (obsolète)'
        )
        parser.add_argument(
            '--stats', action='store_true', help='Affiche les stats live'
        )
        parser.add_argument(
            '--limit', type=int, default=5, help='Ignore (obsolète)'
        )

    def handle(self, *args, **options):
        show_stats = options['stats']

        if show_stats:
            from ai_engine.knowledge_base import KnowledgeBase
            kb = KnowledgeBase()
            stats = kb.get_stats()
            self.stdout.write(self.style.NOTICE("📊 Statistiques 100% live :"))
            for key, value in stats.items():
                icon = "✅" if value else "❌" if isinstance(value, bool) else ""
                self.stdout.write(f"  {icon} {key.replace('_', ' ').title()}: {value}")
            return

        self.stdout.write(self.style.WARNING(
            "\n⚠ L'indexation locale n'est plus necessaire.\n"
            "  Les recherches sont 100% live via les APIs :\n"
            "    - Wikipedia (articles encyclopediques)\n"
            "    - Wikidata (donnees structurees)\n"
            "    - OpenAlex (publications scientifiques)\n"
            "    - Trefle (botanique detaillee)\n"
            "\n  Utilisez directement :\n"
            "    from ai_engine.knowledge_base import KnowledgeBase\n"
            "    kb = KnowledgeBase()\n"
            "    kb.search('comment cultiver le mais')\n"
        ))
