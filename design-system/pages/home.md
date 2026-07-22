# Page: Home — Overrides

> **Règle :** Les règles de ce fichier surchargent MASTER.md pour la page d'accueil uniquement.

## Structure de la Hero Section

```
┌──────────────────────────────────────────────────┐
│  🌿 BioTech Intelligence Bénin (badge)           │
│                                                   │
│  L'Agriculture                                    │
│  Révolutionnée (gradient glow)                    │
│  par l'IA.                                        │
│                                                   │
│  [Rechercher avec Agrotech AI ████████]           │
│  🌿 Plantes anti-palu  🌽 Maïs  🍃 Neem          │
│                                                   │
│  [🚀 Lancer le Scan IA]  [📋 Voir l'Historique]  │
│                                                   │
│        12,400          5,000         50,000       │
│      Récoltes       Agriculteurs   Analyses IA    │
│       Sauvées                                      │
└──────────────────────────────────────────────────┘
         ↑ scroll indicator (mouse animation)
```

## Règles Spécifiques Home

- **Hero 3D** : Opacité 0.8 desktop, hidden mobile
- **Search pill** : Animation pulse lente (3s) sur la box-shadow
- **Stats cards** : Animation staggered au scroll (GSAP ScrollTrigger)
- **Feed** : max 3 posts, reactions popover au hover
- **CTA final** : Full-width glass card avec glow radial

## Variantes de Sections

| Section | Couleur de fond | Hauteur |
|---------|----------------|---------|
| Hero | `--bg-dark` avec blobs | 100vh |
| Stats | `transparent` | auto |
| Features | Section alternée | auto |
| Feed | `--bg-deep` | auto |
| Steps | Gradient subtil `#00E676` 5% | auto |
| CTA | Espacement large | auto |
