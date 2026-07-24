from django.db import models

class WikipediaEntry(models.Model):
    """Stocke les articles Wikipedia importés pour la base de connaissances locale."""
    title = models.CharField(max_length=500, db_index=True)
    summary = models.TextField(blank=True)
    full_text = models.TextField()
    categories = models.CharField(max_length=1000, blank=True, help_text="Catégories Wikipedia")
    url = models.URLField(max_length=1000, blank=True)
    language = models.CharField(max_length=10, default='fr')
    imported_at = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    search_count = models.IntegerField(default=0, help_text="Nombre de fois utilisé")

    class Meta:
        verbose_name = "Article Wikipedia"
        verbose_name_plural = "Articles Wikipedia"

    def __str__(self):
        return self.title

class PlantKnowledge(models.Model):
    """Connaissances structurées sur les plantes extraites de Wikipedia."""
    name = models.CharField(max_length=300, db_index=True)
    scientific_name = models.CharField(max_length=500, blank=True)
    family = models.CharField(max_length=200, blank=True)

    # Caractéristiques
    description = models.TextField(blank=True)
    usage = models.TextField(blank=True, help_text="Utilisations")
    medicinal_properties = models.TextField(blank=True, help_text="Propriétés médicinales")

    # Culture
    growing_conditions = models.TextField(blank=True, help_text="Conditions de croissance")
    diseases = models.TextField(blank=True, help_text="Maladies courantes")

    # Liens
    wikipedia_url = models.URLField(max_length=1000, blank=True)
    image_url = models.URLField(max_length=1000, blank=True)
    common_diseases = models.ManyToManyField('DiseaseKnowledge', blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Connaissance Plante"
        verbose_name_plural = "Connaissances Plantes"

    def __str__(self):
        return f"{self.name} ({self.scientific_name})" if self.scientific_name else self.name

class DiseaseKnowledge(models.Model):
    """Connaissances sur les maladies des plantes."""
    name = models.CharField(max_length=300, db_index=True)
    common_name = models.CharField(max_length=300, blank=True)
    description = models.TextField(blank=True)
    causes = models.TextField(blank=True)
    symptoms = models.TextField(blank=True, help_text="Symptômes visuels")
    treatment = models.TextField(blank=True, help_text="Traitements recommandés")
    prevention = models.TextField(blank=True)

    # Plantes hôtes courantes
    host_plants = models.CharField(max_length=1000, blank=True, help_text="Plantes affectées")

    wikipedia_url = models.URLField(max_length=1000, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Connaissance Maladie"
        verbose_name_plural = "Connaissances Maladies"

    def __str__(self):
        return self.name

class KnowledgeChunk(models.Model):
    """Morceaux de texte avec embeddings vectoriels pour la recherche sémantique."""
    content = models.TextField()
    source_title = models.CharField(max_length=500)
    source_type = models.CharField(max_length=50, choices=[
        ('wikipedia', 'Wikipedia'),
        ('plant', 'Fiche Plante'),
        ('disease', 'Fiche Maladie'),
    ], default='wikipedia')
    source_id = models.IntegerField(null=True, blank=True)
    embedding_id = models.CharField(max_length=200, blank=True, help_text="ID dans ChromaDB")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Fragment de connaissance"
        verbose_name_plural = "Fragments de connaissance"
        indexes = [
            models.Index(fields=['source_type']),
        ]

    def __str__(self):
        return f"[{self.source_type}] {self.source_title[:50]}"
