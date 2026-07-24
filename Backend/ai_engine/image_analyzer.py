"""
image_analyzer.py — Analyse d'images agricoles (Vercel-ready)
=============================================================

Moteur principal : Pillow (leger, toujours dispo)
Moteur avance    : OpenCV (optionnel, debloquer dans requirements-advanced.txt)

Analyse :
  - Couleurs dominantes (Pillow)
  - Proportions HSV (Pillow + numpy)
  - Detection de taches (Pillow + numpy)
  - Texture GLCM (scikit-image, optionnel)
  - Diagnostic par regles expertes

Usage :
  >>> from ai_engine.image_analyzer import ImageAnalyzer
  >>> a = ImageAnalyzer()
  >>> a.diagnose_plant("https://exemple.com/feuille.jpg", "tomate")
  {"status": "malade", "diagnosis": "Mildiou", "confidence": 0.78, ...}
"""

import os
import io
import re
import json
import logging
import urllib.request
import tempfile
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)


# ─── Dependances optionnelles ─────────────────────────────────────

HAS_CV2 = False
HAS_PIL = False
HAS_SKIMAGE = False

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    pass

try:
    from PIL import Image, ImageStat, ExifTags
    HAS_PIL = True
except ImportError:
    pass

try:
    from skimage.feature import graycomatrix, graycoprops
    HAS_SKIMAGE = True
except ImportError:
    pass


# ─── Seuils de diagnostic ─────────────────────────────────────────

HEALTHY_GREEN_HSV = ((35, 40, 40), (85, 255, 255))
YELLOW_HSV = ((20, 50, 50), (35, 255, 255))
BROWN_HSV = ((0, 50, 20), (20, 255, 200))
DARK_HSV = ((0, 0, 0), (180, 255, 80))

MIN_SPOT_AREA = 50

# Signatures de maladies (regles expertes)
DISEASE_SIGNATURES = [
    {
        'name': 'Mildiou',
        'fr': 'Mildiou',
        'symptoms': 'Taches jaunes/huileuses sur les feuilles, puis brunes',
        'treatment': 'Bouillie bordelaise, infusions de prele',
        'indicators': {'yellow': (0.05, 0.5), 'brown': (0.02, 0.3), 'spot_count': (3, 100)},
    },
    {
        'name': 'Oidium',
        'fr': 'Oidium (blanc)',
        'symptoms': 'Poudre blanche sur les feuilles',
        'treatment': 'Soufre, lait dilue (1/10), bicarbonate de soude',
        'indicators': {'powdery': (0.05, 0.6)},
    },
    {
        'name': 'Rouille',
        'fr': 'Rouille',
        'symptoms': 'Pustules oranges/brunes sous les feuilles',
        'treatment': 'Bouillie bordelaise, purin d\'ortie',
        'indicators': {'brown': (0.03, 0.4)},
    },
    {
        'name': 'Carence azotee',
        'fr': 'Carence en azote',
        'symptoms': 'Jaunissement uniforme des vieilles feuilles',
        'treatment': 'Fumier composte, engrais vert (legumineuses)',
        'indicators': {'yellow': (0.15, 0.8), 'healthy_green': (0, 0.4), 'spot_count': (0, 5)},
    },
    {
        'name': 'Taches bacteriennes',
        'fr': 'Maladie bacterienne',
        'symptoms': 'Taches sombres anguleuses avec halo jaune',
        'treatment': 'Arracher les plants infectes, rotation des cultures',
        'indicators': {'dark': (0.02, 0.4), 'spot_count': (5, 100)},
    },
]


# ─── Chargement d'image ───────────────────────────────────────────

def load_image(source, max_size=(800, 800)):
    """
    Charge une image depuis une URL, un chemin, ou des bytes.
    Retourne un numpy array RGB ou None.
    """
    if isinstance(source, np.ndarray):
        return source

    try:
        if source.startswith(('http://', 'https://')):
            req = urllib.request.Request(
                source, headers={'User-Agent': 'AgrotechAI/1.0'}
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                img = Image.open(io.BytesIO(resp.read()))
        else:
            img = Image.open(source)
    except Exception as e:
        logger.warning(f"Impossible de charger l'image: {e}")
        return None

    if HAS_PIL:
        img.thumbnail(max_size, Image.LANCZOS)
    return np.array(img.convert('RGB'))


# ─── Analyse couleur (Pillow + numpy, zéro OpenCV) ────────────────

def extract_hsv_proportions_pil(img_rgb):
    """
    Calcule les proportions HSV sans OpenCV.
    Conversion RGB → HSV manuelle + masques numpy.
    """
    # Conversion RGB → HSV (formule standard)
    r, g, b = img_rgb[:, :, 0] / 255.0, img_rgb[:, :, 1] / 255.0, img_rgb[:, :, 2] / 255.0
    cmax, cmin = np.max(img_rgb, axis=2) / 255.0, np.min(img_rgb, axis=2) / 255.0
    diff = cmax - cmin

    # Hue
    h = np.zeros_like(cmax)
    mask = diff > 0.001
    rc = (g - b) / (diff + 1e-10)
    gc = (b - r) / (diff + 1e-10)
    bc = (r - g) / (diff + 1e-10)
    h = np.where((cmax == r) & mask, (60 * (rc % 6)), h)
    h = np.where((cmax == g) & mask, 60 * (gc + 2), h)
    h = np.where((cmax == b) & mask, 60 * (bc + 4), h)
    h = (h + 360) % 360

    # Saturation
    s = np.where(cmax > 0, diff / (cmax + 1e-10), 0)

    # Value
    v = cmax

    total = img_rgb.shape[0] * img_rgb.shape[1]
    if total == 0:
        return {'healthy_green': 0, 'yellow': 0, 'brown': 0, 'powdery': 0, 'dark': 0}

    # Definitions des plages (H: 0-360, S: 0-1, V: 0-1)
    def proportion(h_low, h_high, s_low, s_high, v_low, v_high):
        mask = (
            (h >= h_low) & (h <= h_high) &
            (s >= s_low) & (s <= s_high) &
            (v >= v_low) & (v <= v_high)
        )
        return int(np.sum(mask)) / total

    return {
        'healthy_green': proportion(70, 170, 0.15, 1.0, 0.15, 1.0),
        'yellow': proportion(40, 70, 0.2, 1.0, 0.2, 1.0),
        'brown': proportion(0, 40, 0.2, 1.0, 0.08, 0.8),
        'powdery': proportion(0, 360, 0, 0.12, 0.7, 1.0),
        'dark': proportion(0, 360, 0, 1.0, 0, 0.3),
    }


def extract_color_stats(img_rgb):
    """Moyenne et ecart-type par canal RGB."""
    return {
        'mean_r': float(np.mean(img_rgb[:, :, 0])),
        'mean_g': float(np.mean(img_rgb[:, :, 1])),
        'mean_b': float(np.mean(img_rgb[:, :, 2])),
        'std_r': float(np.std(img_rgb[:, :, 0])),
        'std_g': float(np.std(img_rgb[:, :, 1])),
        'std_b': float(np.std(img_rgb[:, :, 2])),
    }


# ─── Detection de taches (Pillow + numpy) ─────────────────────────

def _label_connected_components(binary, min_area=MIN_SPOT_AREA):
    """
    Labelisation de composantes connexes en pur numpy (2-pass).
    Remplace scipy.ndimage.label (zero dep).
    """
    h, w = binary.shape
    labeled = np.zeros((h, w), dtype=np.int32)
    current_label = 0
    equivalences = {}

    # 1er passage : assigner des labels provisoires
    for y in range(h):
        for x in range(w):
            if binary[y, x] == 0:
                continue
            top = labeled[y-1, x] if y > 0 else 0
            left = labeled[y, x-1] if x > 0 else 0

            if top == 0 and left == 0:
                current_label += 1
                labeled[y, x] = current_label
            elif top > 0 and left == 0:
                labeled[y, x] = top
            elif left > 0 and top == 0:
                labeled[y, x] = left
            elif top == left:
                labeled[y, x] = top
            else:
                # Conflit : les deux labels sont equivalents
                labeled[y, x] = min(top, left)
                if top != left:
                    equivalences[max(top, left)] = min(top, left)

    # Resoudre les equivalences
    for y in range(h):
        for x in range(w):
            label = labeled[y, x]
            if label > 0:
                while label in equivalences:
                    label = equivalences[label]
                labeled[y, x] = label

    # Compter les aires et filtrer
    unique_labels, counts = np.unique(labeled[labeled > 0], return_counts=True)
    valid_labels = set(unique_labels[counts >= min_area])

    return labeled, valid_labels


def detect_spots_pil(img_rgb, min_area=MIN_SPOT_AREA):
    """
    Detection de taches sans OpenCV (pur numpy).
    """
    gray = np.mean(img_rgb, axis=2).astype(np.uint8)
    mean_val = np.mean(gray)
    binary = (gray < mean_val * 0.7).astype(np.uint8)

    labeled, valid_labels = _label_connected_components(binary, min_area)

    spots = []
    for label in valid_labels:
        mask = labeled == label
        area = int(np.sum(mask))
        coords = np.where(mask)
        y_min, y_max = int(coords[0].min()), int(coords[0].max())
        x_min, x_max = int(coords[1].min()), int(coords[1].max())

        mean_color = img_rgb[mask].mean(axis=0).astype(int)
        perimeter = 2 * ((y_max - y_min) + (x_max - x_min))
        circularity = 4 * np.pi * area / (perimeter * perimeter) if perimeter > 0 else 0

        spots.append({
            'area': area,
            'circularity': round(float(circularity), 3),
            'bbox': [int(x_min), int(y_min), int(x_max - x_min), int(y_max - y_min)],
            'mean_color': mean_color.tolist(),
        })

    return spots


def detect_spots_opencv(img_rgb, min_area=MIN_SPOT_AREA):
    """Detection de taches via OpenCV (plus precise)."""
    if not HAS_CV2:
        return detect_spots_pil(img_rgb, min_area)

    gray = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    thresh = cv2.adaptiveThreshold(
        blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV, 11, 2
    )
    kernel = np.ones((3, 3), np.uint8)
    cleaned = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=2)
    cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_CLOSE, kernel, iterations=1)

    contours, _ = cv2.findContours(cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    spots = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < min_area:
            continue
        perimeter = cv2.arcLength(cnt, True) or 0.01
        circularity = 4 * np.pi * area / (perimeter * perimeter)
        x, y, w, h = cv2.boundingRect(cnt)

        mask = np.zeros(img_rgb.shape[:2], dtype=np.uint8)
        cv2.drawContours(mask, [cnt], -1, 255, -1)
        mean_color = cv2.mean(img_rgb, mask=mask)[:3]

        spots.append({
            'area': int(area),
            'perimeter': float(perimeter),
            'circularity': float(circularity),
            'bbox': [int(x), int(y), int(w), int(h)],
            'mean_color': [int(c) for c in mean_color],
        })

    return spots


def estimate_leaf_area(img_rgb):
    """Estime la surface de la feuille."""
    hsv_props = extract_hsv_proportions_pil(img_rgb)
    leaf_ratio = (
        hsv_props['healthy_green'] +
        hsv_props['yellow'] +
        hsv_props['brown']
    )
    total = img_rgb.shape[0] * img_rgb.shape[1]
    return {
        'leaf_pixels': int(leaf_ratio * total),
        'total_pixels': int(total),
        'leaf_ratio': round(leaf_ratio, 4),
    }


# ─── Texture GLCM (scikit-image, optionnel) ───────────────────────

def extract_texture(img_rgb):
    """Analyse de texture via GLCM (scikit-image)."""
    if not HAS_SKIMAGE:
        return {}

    gray = np.mean(img_rgb, axis=2).astype(np.uint8)
    try:
        glcm = graycomatrix(gray, distances=[1],
                            angles=[0, np.pi/4, np.pi/2, 3*np.pi/4],
                            levels=256, symmetric=True, normed=True)
        features = {}
        labels = {0: '0', 1: '45', 2: '90', 3: '135'}
        for angle_idx, label in labels.items():
            features[f'contrast_{label}'] = float(graycoprops(glcm, 'contrast')[0, angle_idx])
            features[f'homogeneity_{label}'] = float(graycoprops(glcm, 'homogeneity')[0, angle_idx])
            features[f'energy_{label}'] = float(graycoprops(glcm, 'energy')[0, angle_idx])
        return features
    except Exception:
        return {}


# ─── Diagnostic ───────────────────────────────────────────────────

def diagnose(hsv_props, spots):
    """
    Diagnostique les maladies a partir des proportions HSV et des taches.
    Regles expertes (zero ML).
    """
    diagnoses = []

    for disease in DISEASE_SIGNATURES:
        score = 0.0
        matched = 0
        total = max(len(disease['indicators']), 1)

        for indicator, (low, high) in disease['indicators'].items():
            if indicator == 'spot_count':
                val = len(spots)
            else:
                val = hsv_props.get(indicator, 0)

            if low <= val <= high:
                center = (low + high) / 2
                if high > low:
                    proximity = 1 - abs(val - center) / ((high - low) / 2)
                    score += max(0, proximity)
                matched += 1

        if matched > 0:
            confidence = (score / total) * (matched / total)
            if confidence > 0.15:
                diagnoses.append({
                    'maladie': disease['fr'],
                    'maladie_en': disease['name'],
                    'confiance': round(confidence, 3),
                    'symptomes': disease['symptoms'],
                    'traitement': disease['treatment'],
                })

    diagnoses.sort(key=lambda x: x['confiance'], reverse=True)

    if not diagnoses:
        green = hsv_props.get('healthy_green', 0)
        if green > 0.3:
            diagnoses.append({
                'maladie': 'Feuille saine',
                'maladie_en': 'Healthy',
                'confiance': round(green, 3),
                'symptomes': 'Aucun symptome visible',
                'traitement': 'Continuer les bons soins',
            })

    return diagnoses


# ─── Analyseur principal ──────────────────────────────────────────

class ImageAnalyzer:
    """
    Analyseur d'images agricoles.

    Moteur couleur : Pillow + numpy (toujours dispo)
    Moteur taches  : OpenCV (si installe) sinon Pillow + scipy
    Texture        : scikit-image (optionnel)
    """

    def analyze(self, image_source):
        """Analyse complete d'une image de plante."""
        if isinstance(image_source, np.ndarray):
            img_rgb = image_source
        elif isinstance(image_source, str):
            img_rgb = load_image(image_source)
        else:
            return {'error': "Type d'entree non supporte"}

        if img_rgb is None:
            return {'error': "Impossible de charger l'image"}

        result = {
            'image_size': {'width': img_rgb.shape[1], 'height': img_rgb.shape[0]},
        }

        # Couleurs (toujours dispo)
        hsv = extract_hsv_proportions_pil(img_rgb)
        result['features'] = {
            **extract_color_stats(img_rgb),
            **hsv,
        }

        # Taches
        spots = detect_spots_opencv(img_rgb) if HAS_CV2 else detect_spots_pil(img_rgb)
        leaf = estimate_leaf_area(img_rgb)
        result['spots'] = {
            'count': len(spots),
            'details': spots[:15],
            'leaf_coverage': round(
                sum(s['area'] for s in spots) / max(leaf['leaf_pixels'], 1), 4
            ) if spots else 0,
        }
        result['leaf_area'] = leaf

        # Texture (optionnel)
        texture = extract_texture(img_rgb)
        if texture:
            result['features'].update(texture)

        # Diagnostic
        diagnoses = diagnose(hsv, spots)
        result['diagnosis'] = diagnoses

        # Synthese
        if diagnoses:
            top = diagnoses[0]
            result['summary'] = {
                'status': 'malade' if top['maladie'] != 'Feuille saine' else 'sain',
                'confidence': top['confiance'],
                'primary_diagnosis': top['maladie'],
                'treatment': top['traitement'],
            }
        else:
            result['summary'] = {
                'status': 'inde termine',
                'confidence': 0,
                'primary_diagnosis': 'Analyse non concluante',
                'treatment': '',
            }

        # Warning si beaucoup de taches
        if result['spots']['leaf_coverage'] > 0.02:
            result['warnings'] = [
                f"{result['spots']['count']} taches detectees "
                f"couvrant {round(result['spots']['leaf_coverage']*100, 1)}% de la surface"
            ]
        else:
            result['warnings'] = []

        return result

    def diagnose_plant(self, image_source, plant_name=""):
        """Diagnostic plante (compatible API)."""
        analysis = self.analyze(image_source)
        if 'error' in analysis:
            return analysis

        summary = analysis.get('summary', {})
        return {
            'success': True,
            'plant': plant_name or 'Inconnue',
            'status': summary.get('status', 'inde termine'),
            'diagnosis': summary.get('primary_diagnosis', ''),
            'confidence': summary.get('confidence', 0),
            'details': analysis['diagnosis'],
            'treatment': summary.get('treatment', ''),
            'spots': analysis['spots']['count'],
            'leaf_condition': {
                'healthy_green': round(analysis['features'].get('healthy_green', 0) * 100, 1),
                'yellow': round(analysis['features'].get('yellow', 0) * 100, 1),
                'brown': round(analysis['features'].get('brown', 0) * 100, 1),
            },
            'warnings': analysis.get('warnings', []),
        }
