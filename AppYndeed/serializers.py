from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import JobOffer

User = get_user_model()


# ==================== User Serializers ====================

class UserSerializer(serializers.ModelSerializer):
    """Serializer pour afficher les informations utilisateur"""
    class Meta:
        model = User
        fields = ['id', 'email', 'username', 'is_verified', 'date_joined']
        read_only_fields = ['id', 'is_verified', 'date_joined']


class UserRegistrationSerializer(serializers.Serializer):
    """Serializer pour l'inscription - Étape 1 : Email"""
    email = serializers.EmailField()
    
    def validate_email(self, value):
        # Vérifie seulement si un utilisateur VÉRIFIÉ avec cet email existe
        if User.objects.filter(email=value, is_verified=True).exists():
            raise serializers.ValidationError("Un utilisateur avec cet email existe déjà.")
        return value


class VerificationCodeSerializer(serializers.Serializer):
    """Serializer pour la vérification du code - Étape 2"""
    email = serializers.EmailField()
    code = serializers.CharField(min_length=6, max_length=6)
    
    def validate_code(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("Le code doit contenir uniquement des chiffres.")
        return value


class SetPasswordSerializer(serializers.Serializer):
    """Serializer pour définir le mot de passe - Étape 3"""
    email = serializers.EmailField()
    code = serializers.CharField(min_length=6, max_length=6)
    password = serializers.CharField(min_length=8, write_only=True)
    password_confirm = serializers.CharField(min_length=8, write_only=True)
    
    def validate(self, data):
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError({"password_confirm": "Les mots de passe ne correspondent pas."})
        return data


class LoginSerializer(serializers.Serializer):
    """Serializer pour la connexion"""
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer pour changer le mot de passe"""
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(min_length=8, write_only=True)
    new_password_confirm = serializers.CharField(min_length=8, write_only=True)
    
    def validate(self, data):
        if data['new_password'] != data['new_password_confirm']:
            raise serializers.ValidationError({"new_password_confirm": "Les mots de passe ne correspondent pas."})
        return data


# ==================== Job Offer Serializers ====================

class JobOfferSerializer(serializers.ModelSerializer):
    """Serializer pour les offres d'emploi"""
    class Meta:
        model = JobOffer
        fields = ['id', 'title', 'company', 'location', 'job_url', 'description', 'date_posted', 'created_at']
        read_only_fields = ['id', 'created_at']


class JobOfferListSerializer(serializers.ModelSerializer):
    """Serializer allégé pour la liste des offres d'emploi"""
    class Meta:
        model = JobOffer
        fields = ['id', 'title', 'company', 'location', 'job_url', 'date_posted']
