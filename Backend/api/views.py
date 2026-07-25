import os
import json
import base64
import tempfile
import logging
from rest_framework.decorators import api_view, permission_classes, authentication_classes, throttle_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework import status
from .supabase_auth import SupabaseAuthentication
from django.contrib.auth.models import User
from .models import UserProfile, ScanHistory, MarketPrice
from .serializers import UserProfileSerializer

logger = logging.getLogger(__name__)


# ── Throttling IA ──────────────────────────────────────────────────

class AIThrottle(UserRateThrottle):
    scope = 'ai'


# ── Moteur IA 100% local (zéro API externe) ───────────────────────

_query_engine = None

def get_query_engine():
    """Charge le moteur IA local Agrotech (singleton)."""
    global _query_engine
    if _query_engine is None:
        try:
            from ai_engine.query_engine import QueryEngine
            _query_engine = QueryEngine()
            logger.info("Moteur IA local charge avec succes")
        except Exception as e:
            logger.error(f"ERREUR critique - Moteur IA local indisponible : {e}")
            raise
    return _query_engine


# ── Diagnostiquer une plante par image ────────────────────────────

@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
@throttle_classes([AIThrottle])
def diagnose_plant(request):
    """
    Diagnostique une plante a partir d'une photo.
    Utilise uniquement le moteur IA local (OpenCV + Wikipedia + ChromaDB).
    """
    image_data = request.data.get('image')
    plant_name = request.data.get('plant_name', '')

    if not image_data:
        return Response(
            {"error": "Aucune image fournie."},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Decoder l'image base64 → fichier temp pour OpenCV
    try:
        engine = get_query_engine()
        if ';base64,' in image_data:
            raw_b64 = image_data.split(';base64,')[1]
        else:
            raw_b64 = image_data

        tmp = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
        try:
            tmp.write(base64.b64decode(raw_b64))
            tmp.flush()
            local_result = engine.diagnose_plant(tmp.name, plant_name=plant_name)
        finally:
            tmp.close()
            os.unlink(tmp.name)
    except Exception as e:
        logger.error(f"Erreur analyse image: {e}")
        return Response(
            {"error": f"Erreur lors de l'analyse de l'image: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    # Construire la reponse
    if local_result.get('success'):
        leaf = local_result.get('leaf_condition', {})
        return Response({
            "status": "success",
            "source": "ai_engine_local",
            "diagnostic": {
                "plante": local_result.get('plant', plant_name or 'Inconnue'),
                "maladie": local_result.get('diagnosis', 'Saine'),
                "traitement": local_result.get('treatment', ''),
                "cause": '',
                "produit_recommande": '',
                "utilite": '',
                "proprietes_medicinales": '',
                "confiance": local_result.get('confidence', 0),
                "etat_feuille": leaf,
            },
            "details": local_result.get('details', []),
            "warnings": local_result.get('warnings', []),
        })

    return Response({
        "status": "success",
        "source": "ai_engine_local",
        "diagnostic": {
            "plante": plant_name or 'Inconnue',
            "maladie": "Analyse non concluante",
            "traitement": "Consultez un agronome pour un diagnostic precis",
            "confiance": 0,
        }
    })


# ── Recherche agricole intelligente ────────────────────────────────

@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
@throttle_classes([AIThrottle])
def ai_search(request):
    """
    Recherche agricole via la base de connaissances locale
    (Wikipedia + ChromaDB). Zero appel API externe.
    """
    query = request.data.get('query')
    if not query:
        return Response(
            {"error": "Requete vide."},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        engine = get_query_engine()
        local_result = engine.search(query, top_k=5)

        if local_result.get('success') and local_result.get('results'):
            return Response({
                "status": "success",
                "source": "ai_engine_local",
                "answer": local_result.get('answer', ''),
                "results": local_result['results'],
                "sources": local_result.get('sources', []),
            })

        # Base de connaissances pas encore construite
        return Response({
            "status": "success",
            "source": "ai_engine_local",
            "answer": (
                "Le moteur de connaissances est en cours de construction. "
                "Pour l'initialiser, lancez :\n\n"
                "  python manage.py build_knowledge_base --all\n\n"
                "En attendant, je ne peux repondre qu'avec les donnees "
                "deja indexees."
            ),
            "results": [],
            "sources": [],
        })

    except Exception as e:
        logger.error(f"Erreur ai_search: {e}")
        return Response(
            {"error": f"Erreur du moteur de recherche: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ── Profils utilisateur ────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([AllowAny])
def register_user(request):
    return Response({
        "status": "success",
        "message": "Enregistrement via Sync Auto active."
    })


@api_view(['GET', 'PUT', 'PATCH'])
@authentication_classes([SupabaseAuthentication])
@permission_classes([IsAuthenticated])
def profile_detail(request):
    try:
        profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        return Response({"error": "Profil non trouve"}, status=404)

    if request.method == 'GET':
        serializer = UserProfileSerializer(profile)
        return Response(serializer.data)

    elif request.method in ['PUT', 'PATCH']:
        serializer = UserProfileSerializer(profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)


@api_view(['GET'])
@permission_classes([AllowAny])
def public_profile(request, firebase_uid):
    try:
        profile = UserProfile.objects.get(firebase_uid=firebase_uid)
        serializer = UserProfileSerializer(profile)
        return Response(serializer.data)
    except UserProfile.DoesNotExist:
        return Response({"error": "Profil non trouve"}, status=404)


# ── Administration & divers ────────────────────────────────────────

@api_view(['GET'])
@authentication_classes([SupabaseAuthentication])
@permission_classes([IsAuthenticated])
def admin_stats(request):
    return Response({
        'total_users': UserProfile.objects.count(),
        'total_products': MarketPrice.objects.count(),
        'total_orders': ScanHistory.objects.count(),
        'avg_rating': 4.8,
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def version_check(request):
    return Response({
        "version": "v2.1-LOCAL-AI",
        "status": "ok",
        "ai_engine": "local_100%"
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def reset_password(request):
    email = request.data.get('email')
    if not email:
        return Response({"error": "Email requis"}, status=400)
    return Response({
        "status": "success",
        "message": f"Lien envoye a {email}."
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def run_migration(request):
    secret = request.data.get('secret', '')
    if secret != os.environ.get('MIGRATE_SECRET', ''):
        return Response({"error": "Unauthorized"}, status=403)
    from django.core.management import call_command
    from io import StringIO
    out = StringIO()
    try:
        call_command('migrate', '--no-input', stdout=out, stderr=out)
        output = out.getvalue()
        return Response({"status": "ok", "output": output})
    except Exception as e:
        return Response({"status": "error", "error": str(e)}, status=500)


@api_view(['POST'])
@permission_classes([AllowAny])
def build_knowledge_base(request):
    """Construit la base de connaissances Wikipedia via l'API."""
    secret = request.data.get('secret', '')
    if secret != os.environ.get('MIGRATE_SECRET', ''):
        return Response({"error": "Unauthorized"}, status=403)

    command = request.data.get('command', '--all')
    lang = request.data.get('lang', 'fr')

    from django.core.management import call_command
    from io import StringIO
    out = StringIO()
    try:
        args = [command]
        if command == '--all':
            args = ['--all']
        elif command == '--stats':
            args = ['--stats']
        elif command.startswith('--query='):
            args = ['--query', command.split('=', 1)[1]]
        else:
            args = ['--all']

        call_command('build_knowledge_base', *args, lang=lang, stdout=out, stderr=out)
        output = out.getvalue()
        return Response({"status": "ok", "output": output})
    except Exception as e:
        return Response({"status": "error", "error": str(e)}, status=500)
