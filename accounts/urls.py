from . import views
from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView
)

urlpatterns = [
    path('api/token/create', TokenObtainPairView.as_view(),
         name='token_obtain_pair'),
    path('api/token/refresh', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/token/verify', TokenVerifyView.as_view(), name='token_verify'),
    path(
        "register_customer/", RegisterCustomerView.as_view(), name="register_customer"
    ),
    path('riders/register/', RiderRegistrationView.as_view(), name='rider-registration'),
    path("verify-email/", VerifyEmailView.as_view(), name="verify-email"),
]
