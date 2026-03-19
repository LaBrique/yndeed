from django.shortcuts import render, redirect
from django.contrib.auth import get_user_model, authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
import logging
from ..forms import EmailSignUpForm, VerificationCodeForm, PasswordSetForm, LoginForm
from ..models import VerificationCode

logger = logging.getLogger(__name__)
User = get_user_model()


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
        logger.info(f"[EMAIL] Tentative d'envoi d'email a {user.email}")
        logger.info(f"[EMAIL] Code de verification : {code}")
        
        result = send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )
        
        logger.info(f"[OK] Email envoye avec succes a {user.email} (resultat: {result})")
        return True
    except Exception as e:
        logger.error(f"[ERREUR] Erreur lors de l'envoi de l'email a {user.email} : {e}", exc_info=True)
        return False


def signup_step1(request):
    """Étape 1 : Entrée de l'email"""
    if request.user.is_authenticated:
        return redirect('index')
    
    if request.method == 'POST':
        form = EmailSignUpForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            logger.info(f"[SIGNUP] Tentative d'inscription avec l'email: {email}")
            
            try:
                # Vérifier si l'utilisateur existe déjà
                existing_user = User.objects.get(email=email)
                if existing_user.is_verified:
                    messages.error(request, "Cet email est déjà utilisé par un compte vérifié.")
                    logger.warning(f"[WARN] Email {email} existe deja et est verifie")
                else:
                    # Si l'utilisateur existe mais n'est pas vérifié, supprimer et recommencer
                    existing_user.delete()
                    logger.info(f"[DELETE] Utilisateur non verifie {email} supprime, nouvelle tentative")
                    # Continuer avec la création
                    raise User.DoesNotExist
            except User.DoesNotExist:
                # Créer un nouvel utilisateur non vérifié
                user = User.objects.create_user(
                    username=email.split('@')[0],
                    email=email,
                    is_active=False
                )
                logger.info(f"[OK] Nouvel utilisateur cree: {email}")
                
                # Créer et envoyer le code de vérification
                verification = VerificationCode.create_for_user(user)
                logger.info(f"[CODE] Code cree pour {email}: {verification.code}")
                
                if send_verification_email(user, verification.code):
                    messages.success(request, f"Code de vérification envoyé à {email}. Vérifiez votre console pour le code.")
                    request.session['pending_email'] = email
                    return redirect('verify_code')
                else:
                    messages.error(request, "Erreur lors de l'envoi du code. Veuillez réessayer.")
                    user.delete()
                    logger.error(f"[ERREUR] Impossible d'envoyer le code a {email}")
    else:
        form = EmailSignUpForm()
    
    return render(request, 'auth/signup_step1.html', {'form': form})


def verify_code(request):
    """Étape 2 : Vérification du code"""
    pending_email = request.session.get('pending_email')
    
    if not pending_email:
        messages.error(request, "Session expirée. Veuillez recommencer l'inscription.")
        return redirect('signup_step1')
    
    try:
        user = User.objects.get(email=pending_email)
    except User.DoesNotExist:
        messages.error(request, "Utilisateur introuvable. Veuillez recommencer l'inscription.")
        return redirect('signup_step1')
    
    if request.method == 'POST':
        form = VerificationCodeForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data['code']
            logger.info(f"[VERIFY] Verification du code {code} pour {pending_email}")
            
            try:
                verification = VerificationCode.objects.get(user=user, code=code)
                logger.info(f"[OK] Code trouve en base de donnees pour {pending_email}")
                
                if not verification.is_valid():
                    messages.error(request, "Le code est expiré ou déjà utilisé.")
                    logger.warning(f"[WARN] Code invalide pour {pending_email} (expire ou utilise)")
                else:
                    logger.info(f"[OK] Code valide pour {pending_email}, passage a set_password")
                    # Code valide, procéder à la définition du mot de passe
                    request.session['verified_email'] = pending_email
                    return redirect('set_password')
            except VerificationCode.DoesNotExist:
                messages.error(request, "Le code est incorrect.")
                logger.warning(f"[WARN] Code {code} introuvable pour {pending_email}")
    else:
        form = VerificationCodeForm()
    
    return render(request, 'auth/verify_code.html', {
        'form': form,
        'email': pending_email
    })


def set_password(request):
    """Étape 3 : Définition du mot de passe"""
    verified_email = request.session.get('verified_email')
    
    if not verified_email:
        messages.error(request, "Session expirée. Veuillez recommencer l'inscription.")
        return redirect('signup_step1')
    
    try:
        user = User.objects.get(email=verified_email)
    except User.DoesNotExist:
        messages.error(request, "Utilisateur introuvable. Veuillez recommencer l'inscription.")
        return redirect('signup_step1')
    
    if request.method == 'POST':
        form = PasswordSetForm(request.POST)
        if form.is_valid():
            password = form.cleaned_data['password']
            logger.info(f"[PASSWORD] Definition du mot de passe pour {verified_email}")
            
            # Définir le mot de passe et activer l'utilisateur
            user.set_password(password)
            user.is_active = True
            user.is_verified = True
            user.save()
            logger.info(f"[OK] Compte active et verifie pour {verified_email}")
            
            # Marquer le code comme utilisé
            try:
                verification = VerificationCode.objects.get(user=user)
                verification.is_used = True
                verification.save()
                logger.info(f"[OK] Code marque comme utilise pour {verified_email}")
            except VerificationCode.DoesNotExist:
                logger.warning(f"[WARN] Code introuvable pour {verified_email} (normal si deja supprime)")
            
            # Nettoyer la session
            if 'pending_email' in request.session:
                del request.session['pending_email']
            if 'verified_email' in request.session:
                del request.session['verified_email']
            
            messages.success(request, "Compte créé avec succès ! Vous pouvez maintenant vous connecter.")
            logger.info(f"[SUCCESS] Inscription complete pour {verified_email}")
            return redirect('login')
    else:
        form = PasswordSetForm()
    
    return render(request, 'auth/set_password.html', {
        'form': form,
        'email': verified_email
    })


def login_view(request):
    """Connexion avec mot de passe"""
    if request.user.is_authenticated:
        return redirect('index')
    
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            logger.info(f"[LOGIN] Tentative de connexion avec l'email: {email}")
            
            try:
                user_obj = User.objects.get(email=email)
                logger.info(f"[OK] Utilisateur trouve: {email}, is_active={user_obj.is_active}, is_verified={user_obj.is_verified}")
                
                # Utiliser le backend EmailBackend qui accepte l'email
                user = authenticate(request, username=email, password=password)
                
                if user is not None:
                    logger.info(f"[OK] Authentification reussie pour {email}")
                    if user.is_verified:
                        login(request, user)
                        messages.success(request, f"Bienvenue {user.email} !")
                        logger.info(f"[OK] Utilisateur {email} connecte avec succes")
                        return redirect('index')
                    else:
                        messages.error(request, "Votre compte n'est pas encore vérifié.")
                        logger.warning(f"[WARN] Compte non verifie pour {email}")
                else:
                    messages.error(request, "Email ou mot de passe incorrect.")
                    logger.warning(f"[WARN] Authentification echouee pour {email} (mauvais mot de passe)")
            except User.DoesNotExist:
                messages.error(request, "Email ou mot de passe incorrect.")
                logger.warning(f"[WARN] Email {email} introuvable en base de donnees")
    else:
        form = LoginForm()
    
    return render(request, 'auth/login.html', {'form': form})


def login_passwordless_step1(request):
    """Connexion sans mot de passe - Étape 1: Demander l'email"""
    if request.user.is_authenticated:
        return redirect('index')
    
    if request.method == 'POST':
        form = EmailSignUpForm(request.POST)
        # On ne vérifie pas si l'email existe déjà pour la connexion
        email = request.POST.get('email', '').strip()
        
        if email:
            try:
                user = User.objects.get(email=email, is_verified=True)
                
                # Créer et envoyer le code de vérification
                verification = VerificationCode.create_for_user(user)
                logger.info(f"[CODE] Code de connexion cree pour {email}: {verification.code}")
                
                if send_verification_email(user, verification.code):
                    messages.success(request, f"Code de connexion envoyé à {email}")
                    request.session['login_email'] = email
                    return redirect('login_passwordless_verify')
                else:
                    messages.error(request, "Erreur lors de l'envoi du code. Veuillez réessayer.")
            except User.DoesNotExist:
                # Pour la sécurité, on affiche le même message
                messages.error(request, "Si un compte existe avec cet email, un code a été envoyé.")
                logger.warning(f"[WARN] Tentative de connexion passwordless avec email inexistant: {email}")
    else:
        form = EmailSignUpForm()
    
    return render(request, 'auth/login_passwordless.html', {'form': form})


def login_passwordless_verify(request):
    """Connexion sans mot de passe - Étape 2: Vérifier le code"""
    login_email = request.session.get('login_email')
    
    if not login_email:
        messages.error(request, "Session expirée. Veuillez recommencer.")
        return redirect('login_passwordless')
    
    if request.method == 'POST':
        form = VerificationCodeForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data['code']
            logger.info(f"[VERIFY] Verification du code de connexion {code} pour {login_email}")
            
            try:
                user = User.objects.get(email=login_email)
                verification = VerificationCode.objects.get(user=user, code=code)
                
                if verification.is_valid():
                    # Marquer le code comme utilisé
                    verification.is_used = True
                    verification.save()
                    
                    # Connecter l'utilisateur
                    login(request, user, backend='AppYndeed.backends.EmailBackend')
                    
                    # Nettoyer la session
                    if 'login_email' in request.session:
                        del request.session['login_email']
                    
                    messages.success(request, f"Bienvenue {user.email} !")
                    logger.info(f"[OK] Connexion passwordless reussie pour {login_email}")
                    return redirect('index')
                else:
                    messages.error(request, "Le code est expiré ou déjà utilisé.")
                    logger.warning(f"[WARN] Code invalide pour {login_email}")
            except (User.DoesNotExist, VerificationCode.DoesNotExist):
                messages.error(request, "Le code est incorrect.")
                logger.warning(f"[WARN] Code {code} incorrect pour {login_email}")
    else:
        form = VerificationCodeForm()
    
    return render(request, 'auth/login_passwordless_verify.html', {
        'form': form,
        'email': login_email
    })


def logout_view(request):
    """Déconnexion"""
    logout(request)
    messages.success(request, "Vous avez été déconnecté.")
    return redirect('login')


@login_required(login_url='login')
def profile(request):
    """Profil utilisateur"""
    return render(request, 'auth/profile.html', {'user': request.user})
