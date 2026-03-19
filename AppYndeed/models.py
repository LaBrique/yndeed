from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from datetime import timedelta
import secrets

class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)
    is_verified = models.BooleanField(default=False)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
    def __str__(self):
        return self.email


class VerificationCode(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='verification_code')
    code = models.CharField(max_length=6, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    
    def __str__(self):
        return f"Code for {self.user.email}"
    
    def is_valid(self):
        """Vérifie si le code est toujours valide et non utilisé"""
        return not self.is_used and timezone.now() < self.expires_at
    
    @staticmethod
    def generate_code():
        """Génère un code de 6 chiffres aléatoire"""
        return ''.join([str(secrets.randbelow(10)) for _ in range(6)])
    
    @classmethod
    def create_for_user(cls, user):
        """Crée ou met à jour un code de vérification pour un utilisateur"""
        code = cls.generate_code()
        expires_at = timezone.now() + timedelta(minutes=15)
        
        obj, created = cls.objects.update_or_create(
            user=user,
            defaults={
                'code': code,
                'expires_at': expires_at,
                'is_used': False
            }
        )
        return obj


class JobOffer(models.Model):
    title = models.CharField(max_length=255)
    company = models.CharField(max_length=255, null=True, blank=True)
    location = models.CharField(max_length=255, null=True, blank=True)
    job_url = models.URLField(unique=True) 
    description = models.TextField(null=True, blank=True)
    date_posted = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True) 

    def __str__(self):
        return f"{self.title} - {self.company}"
    
    class Meta:
        ordering = ['-date_posted', '-created_at']