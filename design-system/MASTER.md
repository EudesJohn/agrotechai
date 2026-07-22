# 🌿 Agrotech AI — Design System Master

> **Style :** Green-Tech Organic — Design organique & high-tech africain  
> **Cible :** Agriculteurs, experts agronomes, commerçants, Bénin / Afrique de l'Ouest  
> **Stack :** Vue 3 + Vite + Firebase

---

## 1. Concept & Direction Artistique

```
Green-Tech Organic
└── Terre nourricière × Intelligence artificielle
    ├── Courbes organiques (pas d'arêtes brutales)
    ├── Lueur verte néon (tech) sur fond forestier profond (nature)
    ├── Glassmorphism 2.0 (reflet, transparence, sophistication)
    └── Touches africaines subtiles (terracotta, or, motifs)
```

**Personnalité de la marque :**
- **Professionnel** — pas un jeu, un outil sérieux pour l'agriculture
- **Bienveillant** — la tech au service du cultivateur
- **Premium accessible** — luxe sobre, pas ostentatoire
- **Enraciné** — connecté à la terre béninoise, pas une copie硅谷

---

## 2. Palette de Couleurs

### 2.1 Couleurs Principales

| Rôle | Hex | Usage | WCAG |
|------|-----|-------|------|
| **Primary** | `#00E676` | CTA, liens, icônes actives, glow | 4.6:1 sur bg |
| **Primary Hover** | `#00C853` | Hover des boutons primaires | |
| **Primary Deep** | `#1B5E20` | Badges, surlignages subtils | |
| **Secondary** | `#8BC34A` | Accents secondaires, tags | |
| **Accent Cyan** | `#00E5FF` | Highlights tech, AI badge, data viz | |
| **Terra** | `#D4A574` | Warm accent africain, avatars | |

### 2.2 Palette de Fond

| Rôle | Hex | Usage |
|------|-----|-------|
| `--bg-deep` | `#010402` | Fond global le plus profond |
| `--bg-dark` | `#020804` | Fond principal actuel |
| `--bg-surface` | `#0A190A` | Cartes, panneaux (remplace bg-card) |
| `--bg-elevated` | `#122012` | Éléments survolés, dropdowns |
| `--bg-glass` | `rgba(10, 25, 10, 0.6)` | Glassmorphism actuel |

### 2.3 Texte

| Rôle | Hex | Usage |
|------|-----|-------|
| `--text-primary` | `#F8FFF9` | Titres, texte principal (blanc cassé) |
| `--text-body` | `#D0E8D2` | Corps de texte (vert très clair) |
| `--text-muted` | `#6B9E76` | Secondaire, métadonnées (⚠️ actuel `#A5D6A7` trop clair pour du muted) |
| `--text-dim` | `#3D5A42` | Placeholder, labels discrets |

### 2.4 Sémantique

| Rôle | Hex | Contexte |
|------|-----|----------|
| `--success` | `#66BB6A` | Validation, guérison plante |
| `--warning` | `#FFB300` | Attention, alerte modérée |
| `--danger` | `#FF5252` | Erreur, maladie critique |
| `--info` | `#42A5F5` | Information, guide |

### 2.5 Bordures & États

| Rôle | Hex |
|------|-----|
| `--border-default` | `rgba(255, 255, 255, 0.08)` |
| `--border-hover` | `rgba(0, 230, 118, 0.25)` |
| `--border-active` | `rgba(0, 230, 118, 0.5)` |
| `--border-subtle` | `rgba(255, 255, 255, 0.04)` |

### 2.6 Glow Effects

| Rôle | Valeur |
|------|--------|
| `--primary-glow` | `rgba(0, 230, 118, 0.4)` |
| `--accent-glow` | `rgba(0, 229, 255, 0.25)` |
| `--aura-glow` | `rgba(0, 230, 118, 0.08)` |

---

## 3. Typographie

### 3.1 Hiérarchie

| Élément | Font | Weight | Size (clamp) | Line Height | Tracking |
|---------|------|--------|--------------|-------------|----------|
| **H1 Hero** | `Syne` | 800 | `clamp(2.2rem, 6vw, 4rem)` | 1.1 | -0.03em |
| **H2 Section** | `Syne` | 800 | `clamp(1.6rem, 4vw, 2.5rem)` | 1.15 | -0.02em |
| **H3 Card** | `Syne` | 700 | `clamp(1.2rem, 3vw, 1.6rem)` | 1.2 | -0.01em |
| **H4** | `Outfit` | 700 | `1.1rem` | 1.3 | |
| **Body Large** | `Outfit` | 400 | `1.1rem` | 1.6 | |
| **Body** | `Outfit` | 400 | `1rem` | 1.5 | |
| **Body Small** | `Outfit` | 400 | `0.85rem` | 1.5 | |
| **Caption/Meta** | `Outfit` | 600 | `0.75rem` | 1.4 | +0.05em |
| **Monospace** | `JetBrains Mono` | 400 | `0.9rem` | 1.5 | |
| **Button** | `Outfit` | 800 | `0.95rem` | | +0.03em |

### 3.2 Font Stack

```css
/* Déjà importé — parfait */
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700;900&family=Syne:wght@700;800&display=swap');

/* À ajouter pour les données techniques */
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&display=swap');
```

### 3.3 Règles Typographiques

- **Line-length** : max 75 caractères par ligne pour le corps
- **Heading gradient** : réserver uniquement pour H1 hero et titres de section majeurs
- **Body text** : jamais de gradient, toujours en `--text-body` uni
- **Liens dans le texte** : couleur primary + underline au hover seulement

---

## 4. Espacement & Grille

### 4.1 Échelle d'espacement

```
2 | 4 | 8 | 12 | 16 | 20 | 24 | 32 | 40 | 48 | 64 | 80 | 120
```

### 4.2 Container

```css
--container-max: 1400px;
--container-narrow: 960px;  /* Pour pages texte */
--container-padding: 24px;  /* → 15px sur mobile */
```

### 4.3 Breakpoints

| Nom | Largeur |
|-----|---------|
| Mobile S | `375px` |
| Mobile L | `480px` |
| Tablet | `768px` |
| Desktop | `1024px` |
| Wide | `1400px` |

---

## 5. Composants

### 5.1 Boutons

#### Primary Button
```css
.btn-primary {
  height: 56px;
  padding: 0 40px;
  background: linear-gradient(135deg, #00E676 0%, #00C853 100%);
  border-radius: 18px;
  color: #010402;
  font-weight: 800;
  font-size: 1.05rem;
  letter-spacing: 0.03em;
  box-shadow: 0 8px 25px rgba(0, 230, 118, 0.4);
  transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
  cursor: pointer;
}
.btn-primary:hover {
  transform: translateY(-4px) scale(1.02);
  box-shadow: 0 15px 35px rgba(0, 230, 118, 0.5);
}
.btn-primary:active {
  transform: translateY(-1px) scale(0.99);
}
.btn-primary:disabled {
  opacity: 0.4;
  transform: none;
  cursor: not-allowed;
}
```

#### Secondary Button
```css
.btn-secondary {
  height: 56px;
  padding: 0 36px;
  background: rgba(255, 255, 255, 0.05);
  border: 1.5px solid rgba(255, 255, 255, 0.1);
  border-radius: 18px;
  color: #F8FFF9;
  font-weight: 700;
  font-size: 1rem;
  cursor: pointer;
  backdrop-filter: blur(10px);
  transition: all 0.3s ease;
}
.btn-secondary:hover {
  background: rgba(255, 255, 255, 0.1);
  border-color: #00E676;
  transform: translateY(-2px);
}
```

#### Ghost Button
```css
.btn-ghost {
  background: transparent;
  border: none;
  color: var(--text-body);
  font-weight: 700;
  cursor: pointer;
  padding: 8px 16px;
  border-radius: 10px;
  transition: all 0.3s ease;
}
.btn-ghost:hover {
  color: #00E676;
  background: rgba(0, 230, 118, 0.08);
}
```

#### Sizes
```css
.btn-sm  { height: 40px; padding: 0 20px; font-size: 0.85rem; border-radius: 12px; }
.btn-lg  { height: 64px; padding: 0 48px; font-size: 1.15rem; }
.btn-icon { width: 44px; height: 44px; padding: 0; border-radius: 12px; } /* touch target 44x44 */
```

### 5.2 Cartes (Glassmorphism)

```css
.glass-panel {
  background: rgba(10, 25, 10, 0.6);
  backdrop-filter: blur(24px) saturate(180%);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 24px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
  transition: border-color 0.3s ease, box-shadow 0.3s ease;
}
.glass-panel:hover {
  border-color: rgba(0, 230, 118, 0.25);
  box-shadow: 0 8px 40px rgba(0, 230, 118, 0.08);
}
```

**Variantes :**
- `glass-panel-sm` → border-radius: 16px, padding: 20px
- `glass-panel-lg` → border-radius: 32px, padding: 48px

### 5.3 Champs de Formulaire

```css
.form-input {
  width: 100%;
  padding: 14px 18px;
  background: rgba(255, 255, 255, 0.03);
  border: 1.5px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  color: #F8FFF9;
  font-size: 1rem;
  font-family: 'Outfit', sans-serif;
  outline: none;
  transition: all 0.3s ease;
}
.form-input:focus {
  border-color: #00E676;
  background: rgba(255, 255, 255, 0.06);
  box-shadow: 0 0 0 3px rgba(0, 230, 118, 0.15);
}
.form-input::placeholder {
  color: #3D5A42;
}
.form-input.error {
  border-color: #FF5252;
  box-shadow: 0 0 0 3px rgba(255, 82, 82, 0.15);
}
.form-label {
  font-size: 0.75rem;
  font-weight: 700;
  color: #6B9E76;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 8px;
  display: block;
}
```

### 5.4 Badges & Tags

```css
.badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 12px;
  border-radius: 100px;
  font-size: 0.7rem;
  font-weight: 800;
  letter-spacing: 0.5px;
  text-transform: uppercase;
}
.badge-primary {
  background: rgba(0, 230, 118, 0.15);
  color: #00E676;
  border: 1px solid rgba(0, 230, 118, 0.3);
}
.badge-ai {
  background: linear-gradient(135deg, rgba(0, 230, 118, 0.2), rgba(0, 229, 255, 0.15));
  color: #00E5FF;
  border: 1px solid rgba(0, 229, 255, 0.3);
}
```

### 5.5 Navigation

- **Fixed navbar** : hauteur 90px desktop, 75px mobile
- **Floating** : margin top `8px`, border-radius en bas `24px`
- **Nav item actif** : underline glow vert
- **Mobile** : hamburger → slide-in panel droite, backdrop blur

### 5.6 Modal / Dialog

```css
.modal-overlay {
  background: rgba(0, 0, 0, 0.85);
  backdrop-filter: blur(15px);
  z-index: 2000;
}
.modal-card {
  max-width: 480px; /* ou 720px pour register */
  padding: 48px;
  border-radius: 24px;
}
```

### 5.7 Loaders

```css
/* Spinner circulaire */
.spinner {
  width: 24px; height: 24px;
  border: 3px solid rgba(0, 230, 118, 0.2);
  border-top-color: #00E676;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

/* Skeleton screen */
.skeleton {
  background: linear-gradient(90deg, 
    rgba(255,255,255,0.03) 25%, 
    rgba(255,255,255,0.06) 50%, 
    rgba(255,255,255,0.03) 75%
  );
  background-size: 200% 100%;
  animation: shimmer 1.5s ease-in-out infinite;
  border-radius: 8px;
}
```

---

## 6. Ombres & Élévations

| Niveau | Box-shadow | Usage |
|--------|------------|-------|
| 1 | `0 2px 8px rgba(0,0,0,0.3)` | Éléments subtils |
| 2 | `0 8px 32px rgba(0,0,0,0.5)` | Cartes glassmorphism |
| 3 | `0 20px 60px rgba(0,0,0,0.6)` | Modals, dropdowns |
| 4 | `0 40px 80px rgba(0,0,0,0.8)` | Plein écran, overlay |

---

## 7. Animations

| Micro-interaction | Durée | Easing |
|-------------------|-------|--------|
| Hover général | `200ms` | `ease` |
| Entrée de carte | `800ms` | `power2.out` (GSAP) |
| Modal open | `300ms` | `cubic-bezier(0.34, 1.56, 0.64, 1)` |
| Mobile menu | `400ms` | `cubic-bezier(0.175, 0.885, 0.32, 1.275)` |
| Scroll reveal | `800ms` | `cubic-bezier(0.2, 1, 0.3, 1)` |

**Règle d'or :** 
- `prefers-reduced-motion: reduce` → désactiver toutes les animations non-essentielles
- Toujours utiliser `transform` + `opacity`, jamais `width`, `height`, `top`, `left`

---

## 8. Anti-Patterns (à éviter)

| ❌ À ne pas faire | ✅ À faire |
|-------------------|-----------|
| Utiliser des emojis comme icônes UI | SVG icons (Lucide, Heroicons) |
| `#A5D6A7` pour du texte muted (trop clair) | `#6B9E76` — contraste suffisant |
| Scale transform sur hover des cartes dans une grille | Color/opacity/shadow transitions |
| `var(--primary)` dans `rgba()` qui casse | Utiliser la valeur hex `#00E676` dans `rgba()` |
| Bordures `white/10` invisibles en light mode | Ajuster l'opacité selon le mode |
| Body text en gradient | Body toujours en couleur unie |
| `alert()` pour les erreurs | Toast/notification in-app |
| Glassmorphism avec `bg-white/10` en light mode | `bg-white/80` minimum en light |

---

## 9. Règles d'Accessibilité

- **Contraste minimum** : 4.5:1 texte normal, 3:1 texte large (18px+ bold)
- **Focus visible** : `outline: 2px solid #00E676; outline-offset: 2px` sur tous les éléments interactifs
- **Touch targets** : minimum 44×44px (boutons, icônes cliquables)
- **Alt text** : toutes les images fonctionnelles/meaningful
- **Aria-labels** : boutons icon-only
- **Tab order** : ordre visuel = ordre tab
- **`cursor: pointer`** : tous les éléments cliquables

---

## 10. Format des Icônes

**Règle stricte :** Pas d'emojis comme icônes UI.

| Usage | Source | Taille |
|-------|--------|--------|
| Navigation | SVG inline | 24×24 |
| Features | SVG inline | 48×48 |
| Actions | SVG inline | 20×20 |
| Social/Avatars | SVG inline | 16×16 |

Exporter les SVG depuis **Lucide** ou **Heroicons** — cohérents, scalable, accessibles.

---

## 11. Directives Responsive

| Breakpoint | Comportement |
|------------|-------------|
| > 1024px | Layout desktop complet, animations riches, 3D visible |
| 768-1024px | Navigation desktop réduite, grilles 2 colonnes |
| 480-768px | Navigation mobile (hamburger), grilles 1 colonne, 3D caché |
| < 480px | Typo réduite, padding 15px, pleine largeur |

---

## 12. Checklist Qualité (avant chaque livraison)

- [ ] Pas d'emojis comme icônes (utiliser des SVG)
- [ ] Tous les boutons cliquables ont `cursor: pointer`
- [ ] Les hover states ne causent pas de layout shift
- [ ] `prefers-reduced-motion` respecté
- [ ] Contraste 4.5:1 minimum vérifié
- [ ] Boutons désactivés visuellement distincts
- [ ] Formulaires avec `<label>` explicite
- [ ] Testé à 375px, 768px, 1024px, 1440px
- [ ] Pas de scroll horizontal mobile
- [ ] Transitions < 300ms pour micro-interactions

---

*Généré avec UI/UX Pro Max — Design Intelligence*
