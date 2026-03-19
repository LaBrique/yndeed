from django.urls import path
from .views.api import (
    # Auth endpoints
    RegisterAPIView,
    VerifyCodeAPIView,
    SetPasswordAPIView,
    LoginAPIView,
    LogoutAPIView,
    ProfileAPIView,
    ChangePasswordAPIView,
    # Job endpoints
    JobOfferListAPIView,
    JobOfferDetailAPIView,
    JobOfferSearchAPIView,
    # Stats & Locations
    api_stats,
    api_locations,
)

urlpatterns = [
    # ==================== Auth API ====================
    path('auth/register/', RegisterAPIView.as_view(), name='api_register'),
    path('auth/verify-code/', VerifyCodeAPIView.as_view(), name='api_verify_code'),
    path('auth/set-password/', SetPasswordAPIView.as_view(), name='api_set_password'),
    path('auth/login/', LoginAPIView.as_view(), name='api_login'),
    path('auth/logout/', LogoutAPIView.as_view(), name='api_logout'),
    path('auth/profile/', ProfileAPIView.as_view(), name='api_profile'),
    path('auth/change-password/', ChangePasswordAPIView.as_view(), name='api_change_password'),
    
    # ==================== Jobs API ====================
    path('jobs/', JobOfferListAPIView.as_view(), name='api_jobs_list'),
    path('jobs/<int:pk>/', JobOfferDetailAPIView.as_view(), name='api_job_detail'),
    path('jobs/search/', JobOfferSearchAPIView.as_view(), name='api_jobs_search'),
    
    # ==================== Stats & Locations API ====================
    path('stats/', api_stats, name='api_stats'),
    path('locations/', api_locations, name='api_locations'),
]
