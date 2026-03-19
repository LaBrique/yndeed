from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination
from django.contrib.auth import get_user_model, authenticate, login, logout
from django.db.models import Q, Case, When, IntegerField, Value
from django.core.mail import send_mail
from django.conf import settings
import logging

from ..models import JobOffer, VerificationCode
from ..serializers import (
    UserSerializer,
    UserRegistrationSerializer,
    VerificationCodeSerializer,
    SetPasswordSerializer,
    LoginSerializer,
    ChangePasswordSerializer,
    JobOfferSerializer,
    JobOfferListSerializer,
)

logger = logging.getLogger(__name__)
User = get_user_model()


# ==================== Pagination ====================

class JobOfferPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


# ==================== Helper Functions ====================

def send_verification_email(user, code):
    """Envoie un email avec le code de vérification"""
    subject = "Code de vérification Yndeed"
    message = f"""
    Bienvenue sur Yndeed !
    
    Votre code de vérification est : {code}
    
    Ce code expire dans 15 minutes.
    
    Si vous n'avez pas demandé ce code, ignorez ce message.
    """
    
    try:
        logger.info(f"[API][EMAIL] Tentative d'envoi d'email a {user.email}")
        result = send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )
        logger.info(f"[API][OK] Email envoye avec succes a {user.email}")
        return True
    except Exception as e:
        logger.error(f"[API][ERREUR] Erreur envoi email a {user.email}: {e}")
        return False


# ==================== Auth API Views ====================

class RegisterAPIView(APIView):
    """
    API Inscription - Étape 1 : Envoi de l'email
    
    POST /api/auth/register/
    Body: {"email": "user@example.com"}
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        email = serializer.validated_data['email']
        logger.info(f"[API][SIGNUP] Tentative d'inscription: {email}")
        
        # Supprimer les utilisateurs non vérifiés avec cet email
        User.objects.filter(email=email, is_verified=False).delete()
        
        # Créer un nouvel utilisateur non vérifié
        user = User.objects.create_user(
            username=email.split('@')[0],
            email=email,
            is_active=False
        )
        logger.info(f"[API][OK] Utilisateur cree: {email}")
        
        # Créer et envoyer le code de vérification
        verification = VerificationCode.create_for_user(user)
        
        if send_verification_email(user, verification.code):
            return Response({
                "message": f"Code de vérification envoyé à {email}",
                "email": email
            }, status=status.HTTP_201_CREATED)
        else:
            user.delete()
            return Response({
                "error": "Erreur lors de l'envoi du code. Veuillez réessayer."
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class VerifyCodeAPIView(APIView):
    """
    API Vérification du code - Étape 2
    
    POST /api/auth/verify-code/
    Body: {"email": "user@example.com", "code": "123456"}
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = VerificationCodeSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        email = serializer.validated_data['email']
        code = serializer.validated_data['code']
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({
                "error": "Utilisateur introuvable."
            }, status=status.HTTP_404_NOT_FOUND)
        
        try:
            verification = VerificationCode.objects.get(user=user, code=code)
            
            if not verification.is_valid():
                return Response({
                    "error": "Le code est expiré ou déjà utilisé."
                }, status=status.HTTP_400_BAD_REQUEST)
            
            return Response({
                "message": "Code vérifié avec succès.",
                "email": email,
                "verified": True
            }, status=status.HTTP_200_OK)
            
        except VerificationCode.DoesNotExist:
            return Response({
                "error": "Le code est incorrect."
            }, status=status.HTTP_400_BAD_REQUEST)


class SetPasswordAPIView(APIView):
    """
    API Définition du mot de passe - Étape 3
    
    POST /api/auth/set-password/
    Body: {"email": "...", "code": "123456", "password": "...", "password_confirm": "..."}
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = SetPasswordSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        email = serializer.validated_data['email']
        code = serializer.validated_data['code']
        password = serializer.validated_data['password']
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({
                "error": "Utilisateur introuvable."
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Vérifier le code une dernière fois
        try:
            verification = VerificationCode.objects.get(user=user, code=code)
            if not verification.is_valid():
                return Response({
                    "error": "Le code est expiré ou déjà utilisé."
                }, status=status.HTTP_400_BAD_REQUEST)
        except VerificationCode.DoesNotExist:
            return Response({
                "error": "Le code est incorrect."
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Définir le mot de passe et activer l'utilisateur
        user.set_password(password)
        user.is_active = True
        user.is_verified = True
        user.save()
        
        # Marquer le code comme utilisé
        verification.is_used = True
        verification.save()
        
        logger.info(f"[API][SUCCESS] Inscription complete pour {email}")
        
        return Response({
            "message": "Compte créé avec succès !",
            "user": UserSerializer(user).data
        }, status=status.HTTP_201_CREATED)


class LoginAPIView(APIView):
    """
    API Connexion
    
    POST /api/auth/login/
    Body: {"email": "user@example.com", "password": "..."}
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        email = serializer.validated_data['email']
        password = serializer.validated_data['password']
        
        user = authenticate(request, username=email, password=password)
        
        if user is not None:
            if user.is_verified:
                login(request, user)
                logger.info(f"[API][OK] Connexion reussie: {email}")
                return Response({
                    "message": f"Bienvenue {user.email} !",
                    "user": UserSerializer(user).data
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    "error": "Votre compte n'est pas encore vérifié."
                }, status=status.HTTP_403_FORBIDDEN)
        else:
            return Response({
                "error": "Email ou mot de passe incorrect."
            }, status=status.HTTP_401_UNAUTHORIZED)


class LogoutAPIView(APIView):
    """
    API Déconnexion
    
    POST /api/auth/logout/
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        logout(request)
        return Response({
            "message": "Déconnexion réussie."
        }, status=status.HTTP_200_OK)


class ProfileAPIView(APIView):
    """
    API Profil utilisateur
    
    GET /api/auth/profile/ - Récupérer le profil
    PUT /api/auth/profile/ - Mettre à jour le profil
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)
    
    def put(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ChangePasswordAPIView(APIView):
    """
    API Changement de mot de passe
    
    POST /api/auth/change-password/
    Body: {"old_password": "...", "new_password": "...", "new_password_confirm": "..."}
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        user = request.user
        old_password = serializer.validated_data['old_password']
        new_password = serializer.validated_data['new_password']
        
        if not user.check_password(old_password):
            return Response({
                "error": "Ancien mot de passe incorrect."
            }, status=status.HTTP_400_BAD_REQUEST)
        
        user.set_password(new_password)
        user.save()
        
        return Response({
            "message": "Mot de passe modifié avec succès."
        }, status=status.HTTP_200_OK)


# ==================== Job Offers API Views ====================

class JobOfferListAPIView(generics.ListAPIView):
    """
    API Liste des offres d'emploi avec recherche et pagination
    Les offres de développeur sont privilégiées (affichées en premier)
    
    GET /api/jobs/
    Query params: ?keywords=python&location=paris&page=1
    """
    serializer_class = JobOfferListSerializer
    pagination_class = JobOfferPagination
    permission_classes = [AllowAny]
    
    # Mots-clés pour identifier les offres de développeur (priorité haute)
    DEV_KEYWORDS = [
        'développeur', 'developpeur', 'developer', 'dev ', 
        'software engineer', 'ingénieur logiciel', 'programmeur',
        'full stack', 'fullstack', 'frontend', 'front-end', 'backend', 'back-end',
        'python', 'java', 'javascript', 'react', 'angular', 'vue',
        'php', 'node', 'django', 'flask', 'spring',
    ]
    
    def get_queryset(self):
        queryset = JobOffer.objects.all()
        
        keywords = self.request.query_params.get('keywords', '')
        location = self.request.query_params.get('location', '')
        
        if keywords:
            queryset = queryset.filter(
                Q(title__icontains=keywords) | 
                Q(description__icontains=keywords)
            )
        
        if location:
            queryset = queryset.filter(location__icontains=location)
        
        # Créer une annotation pour prioriser les offres de développeur
        # Priority 0 = développeur (affiché en premier), 1 = autres
        dev_conditions = Q()
        for keyword in self.DEV_KEYWORDS:
            dev_conditions |= Q(title__icontains=keyword)
        
        queryset = queryset.annotate(
            is_dev_job=Case(
                When(dev_conditions, then=Value(0)),
                default=Value(1),
                output_field=IntegerField()
            )
        ).order_by('is_dev_job', '-date_posted', '-created_at')
        
        return queryset


class JobOfferDetailAPIView(generics.RetrieveAPIView):
    """
    API Détail d'une offre d'emploi
    
    GET /api/jobs/<id>/
    """
    queryset = JobOffer.objects.all()
    serializer_class = JobOfferSerializer
    permission_classes = [AllowAny]


class JobOfferSearchAPIView(APIView):
    """
    API Recherche avancée d'offres d'emploi
    
    POST /api/jobs/search/
    Body: {"keywords": "python", "location": "paris", "company": "google"}
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        keywords = request.data.get('keywords', '')
        location = request.data.get('location', '')
        company = request.data.get('company', '')
        
        queryset = JobOffer.objects.all()
        
        if keywords:
            queryset = queryset.filter(
                Q(title__icontains=keywords) | 
                Q(description__icontains=keywords)
            )
        
        if location:
            queryset = queryset.filter(location__icontains=location)
        
        if company:
            queryset = queryset.filter(company__icontains=company)
        
        # Pagination manuelle
        page_size = int(request.data.get('page_size', 10))
        page = int(request.data.get('page', 1))
        start = (page - 1) * page_size
        end = start + page_size
        
        total_count = queryset.count()
        jobs = queryset[start:end]
        
        serializer = JobOfferListSerializer(jobs, many=True)
        
        return Response({
            "count": total_count,
            "page": page,
            "page_size": page_size,
            "total_pages": (total_count + page_size - 1) // page_size,
            "results": serializer.data
        })


# ==================== Stats API ====================

@api_view(['GET'])
@permission_classes([AllowAny])
def api_stats(request):
    """
    API Statistiques globales
    
    GET /api/stats/
    """
    return Response({
        "total_jobs": JobOffer.objects.count(),
        "total_users": User.objects.filter(is_verified=True).count(),
        "total_companies": JobOffer.objects.values('company').distinct().count(),
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def api_locations(request):
    """
    API Liste des villes disponibles pour l'autocomplete
    
    GET /api/locations/?q=par
    Retourne les villes qui commencent par "par" (ex: Paris, Paray-le-Monial...)
    """
    query = request.query_params.get('q', '').strip()
    
    # Récupérer les locations uniques non nulles
    locations = JobOffer.objects.exclude(
        location__isnull=True
    ).exclude(
        location__exact=''
    ).values_list('location', flat=True).distinct()
    
    # Extraire les villes (souvent format "Ville, Région" ou "Ville")
    cities = set()
    for loc in locations:
        if loc:
            # Prendre la première partie (avant la virgule) comme ville principale
            city = loc.split(',')[0].strip()
            if city:
                cities.add(city)
    
    # Filtrer par la recherche si fournie
    if query:
        cities = [c for c in cities if query.lower() in c.lower()]
    
    # Trier alphabétiquement et limiter à 15 résultats
    sorted_cities = sorted(cities, key=str.lower)[:15]
    
    return Response({
        "locations": sorted_cities
    })
