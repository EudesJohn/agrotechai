"""
Supabase JWT Verification with HS256 (HMAC-SHA256).
Supabase signe ses tokens avec un secret symétrique, contrairement à Firebase
qui utilise des certificats RSA publics.

Configuration requise dans settings.py :
  SUPABASE_URL = 'https://xxxxx.supabase.co'
  SUPABASE_JWT_SECRET = '<the HMAC secret from Settings > API > JWT Settings>'
"""
import jwt
from django.conf import settings
from django.contrib.auth.models import User
from rest_framework import authentication, exceptions
from .models import UserProfile


class SupabaseAuthentication(authentication.BaseAuthentication):
    """
    Authentification via JWT Supabase.
    Vérifie les tokens HS256 avec le secret partagé.
    Crée automatiquement un profil Django si inexistant.
    """
    def authenticate(self, request):
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        if not auth_header:
            return None

        parts = auth_header.split(' ')
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            raise exceptions.AuthenticationFailed('En-tête Authorization invalide. Utilisez Bearer.')
        access_token = parts[1]

        supabase_jwt_secret = getattr(settings, 'SUPABASE_JWT_SECRET', None)
        if not supabase_jwt_secret:
            raise exceptions.AuthenticationFailed(
                'SUPABASE_JWT_SECRET non configuré sur le serveur.'
            )

        try:
            # Décoder et vérifier le JWT avec PyJWT
            # Supabase utilise HS256 (HMAC-SHA256)
            # L'audience est 'authenticated' (pas le project ID comme Firebase)
            # Le claim 'sub' contient l'UUID Supabase de l'utilisateur
            payload = jwt.decode(
                access_token,
                supabase_jwt_secret,
                algorithms=['HS256'],
                audience='authenticated',
                options={
                    'verify_exp': True,
                    'require': ['sub', 'exp', 'aud'],
                }
            )

            supabase_uid = payload.get('sub')
            if not supabase_uid:
                raise exceptions.AuthenticationFailed(
                    'Token Supabase invalide : aucun sub trouvé.'
                )

            email = payload.get('email', '')
            user_metadata = payload.get('user_metadata', {})

            # Sync Auto : créer le profil Django si inexistant
            try:
                profile = UserProfile.objects.get(firebase_uid=supabase_uid)
                user = profile.user
            except UserProfile.DoesNotExist:
                username = email.split('@')[0] if email else f"user_{supabase_uid[:8]}"
                if User.objects.filter(username=username).exists():
                    username = f"{username}_{supabase_uid[:4]}"

                name = user_metadata.get('full_name', '')
                picture = user_metadata.get('avatar_url', '')

                user = User.objects.create(
                    username=username,
                    email=email or f"{supabase_uid}@supabase-user.com",
                    first_name=name.split(' ')[0] if name else '',
                    last_name=' '.join(name.split(' ')[1:]) if name and ' ' in name else ''
                )
                profile = UserProfile.objects.create(
                    user=user,
                    firebase_uid=supabase_uid,
                    profile_picture=picture
                )
                print(f">>> [AUTO-SYNC] Nouveau profil créé : {user.email} (Supabase)")

            return (user, None)

        except jwt.ExpiredSignatureError:
            raise exceptions.AuthenticationFailed('Token expiré. Veuillez vous reconnecter.')
        except jwt.InvalidAudienceError:
            raise exceptions.AuthenticationFailed('Audience du token invalide.')
        except jwt.InvalidTokenError as e:
            raise exceptions.AuthenticationFailed(f'Token Supabase invalide : {str(e)}')
        except Exception as e:
            raise exceptions.AuthenticationFailed(f'Authentification échouée : {str(e)}')
