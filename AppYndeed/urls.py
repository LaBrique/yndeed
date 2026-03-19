from django.urls import path
from .views.index import index
from .views.auth import (
    signup_step1, 
    verify_code, 
    set_password, 
    login_view,
    login_passwordless_step1,
    login_passwordless_verify,
    logout_view, 
    profile
)

urlpatterns = [
    path('', index, name='index'),
    
    # Auth URLs - Inscription
    path('signup/', signup_step1, name='signup_step1'),
    path('verify-code/', verify_code, name='verify_code'),
    path('set-password/', set_password, name='set_password'),
    
    # Auth URLs - Connexion classique (email + mot de passe)
    path('login/', login_view, name='login'),
    
    # Auth URLs - Connexion sans mot de passe (email + code)
    path('login/email/', login_passwordless_step1, name='login_passwordless'),
    path('login/email/verify/', login_passwordless_verify, name='login_passwordless_verify'),
    
    # Auth URLs - Déconnexion & Profil
    path('logout/', logout_view, name='logout'),
    path('profile/', profile, name='profile'),
]
