# Page: Diagnostic — Overrides

> **Règle :** Les règles de ce fichier surchargent MASTER.md pour la page de diagnostic IA.

## Structure

```
┌──────────────────────────────────────────────────┐
│  🔬 Diagnostic IA — Section Principale            │
│                                                    │
│  ┌──────────┐  ┌──────────────────────────────┐   │
│  │          │  │  Résultat Analyse             │   │
│  │  Upload  │  │  Maladie: Mildiou (85%)       │   │
│  │  Image   │  │  ─────────────────────        │   │
│  │  Plant   │  │  Traitement recommandé :      │   │
│  │          │  │  Bouillie bordelaise...       │   │
│  │  [📸]   │  │  [Voir traitement complet]     │   │
│  └──────────┘  └──────────────────────────────┘   │
│                                                    │
│  Plantes récemment scannées :                      │
│  [Maïs][Tomate][Manioc][Igname]                    │
└──────────────────────────────────────────────────┘
```

## Règles Spécifiques

- **Upload zone** : Bordure en tiretés `--border-active`, glow au drag
- **Confidence score** : Badge coloré (vert >70%, orange 40-70%, rouge <40%)
- **History chips** : Badges quick-access
- **Loading state** : Skeleton shimmer + spinner
- **Error state** : Message centré avec icône warning
