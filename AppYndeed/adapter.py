"""
Adaptateur personnalisé pour django-allauth
Permet de connecter les comptes OAuth (Google) avec le modèle CustomUser
"""

from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.auth import get_user_model

User = get_user_model()


class CustomAccountAdapter(DefaultAccountAdapter):
    """Adaptateur pour les comptes classiques"""
    
    def save_user(self, request, user, form, commit=True):
        """Sauvegarde un nouvel utilisateur"""
        user = super().save_user(request, user, form, commit=False)
        user.is_verified = True  # Vérifié par email si allauth le demande
        if commit:
            user.save()
        return user


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    """Adaptateur pour les comptes OAuth (Google, etc.)"""
    
    def pre_social_login(self, request, sociallogin):
        """
        Appelé après l'authentification OAuth mais avant la création/connexion du compte.
        Permet de lier un compte social à un compte existant.
        """
        # Si l'utilisateur n'est pas connecté et que l'email existe déjà
        if sociallogin.is_existing:
            return
        
        # Récupérer l'email du compte social
        email = sociallogin.account.extra_data.get('email')
        if not email:
            return
        
        # Vérifier si un utilisateur avec cet email existe déjà
        try:
            user = User.objects.get(email=email)
            # Connecter le compte social à l'utilisateur existant
            sociallogin.connect(request, user)
        except User.DoesNotExist:
            pass
    
    def save_user(self, request, sociallogin, form=None):
        """
        Sauvegarde un nouvel utilisateur créé via OAuth.
        Marque automatiquement le compte comme vérifié.
        """
        user = super().save_user(request, sociallogin, form)
        
        # Les comptes OAuth sont automatiquement vérifiés
        user.is_verified = True
        
        # Récupérer les infos depuis le provider
        extra_data = sociallogin.account.extra_data
        if 'given_name' in extra_data:
            user.first_name = extra_data.get('given_name', '')
        if 'family_name' in extra_data:
            user.last_name = extra_data.get('family_name', '')
        if 'picture' in extra_data:
            # Vous pouvez stocker l'URL de l'avatar si vous avez un champ pour ça
            pass
        
        user.save()
        return user
    
    def populate_user(self, request, sociallogin, data):
        """
        Remplit les données utilisateur depuis le provider OAuth.
        """
        user = super().populate_user(request, sociallogin, data)
        return user
