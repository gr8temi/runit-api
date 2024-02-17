from django.db import transaction
from django.contrib.auth import authenticate
from django.utils import timezone
from tom_tom_map_api.distance_matrix import TomTomDistanceMatrix
from .tokens import create_jwt_pair_for_user
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import generics, status
from .serializers import *
from .models import *
from .utils import (
    DistanceCalculator,
    retry,
    send_verification_email,
    str_to_bool,
)
from django.conf import settings
from mapbox_distance_matrix.distance_matrix import MapboxDistanceDuration
import logging
from supabase import create_client, Client

logger = logging.getLogger(__name__)

url: str = settings.SUPABASE_URL
key: str = settings.SUPABASE_KEY
supabase: Client = create_client(url, key)

riders_table = "riders"
customers_table = "customers"


class BaseRegistrationView(generics.CreateAPIView):
    serializer_class = None

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        try:
            serializer = self.serializer_class(data=request.data)
            serializer.is_valid(raise_exception=True)
            user = serializer.save()
            send_verification_email(user.user, "registration")
            success_message = f"{str(user)} registered successfully"
            data = {
                "message": success_message,
                "data": serializer.data,
            }
            return Response(data, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class RiderRegistrationView(BaseRegistrationView):
    serializer_class = RiderSerializer


class CustomerRegistrationView(BaseRegistrationView):
    serializer_class = CustomerSerializer


class VerifyEmailView(APIView):
    """
    API view to handle email verification.
    """

    def post(self, request, *args, **kwargs):
        """
        Handle POST requests to validate the verification token, mark the user's email as verified,
        and return a response with a success message or error message.
        """

        # Get the otp_token from the request data
        otp_token = request.data.get("otp_token")

        # Check if otp_token is missing
        if not otp_token:
            return Response(
                {"detail": "OTP token is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Query the UserVerification model for the given otp_token
            user_verification = UserVerification.objects.filter(
                otp__exact=otp_token
            ).first()
        except UserVerification.DoesNotExist:
            return Response(
                {"detail": "Invalid OTP token"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Check if user_verification exists and the email has not expired
        if user_verification and (
            user_verification.otp_expiration_time > timezone.now()
            and not user_verification.user.is_verified
        ):
            # Mark the user as verified
            user_verification.user.is_verified = True
            user_verification.user.save()

            # Invalidate the OTP token
            user_verification.otp = None
            user_verification.otp_expiration_time = None
            user_verification.save()

            return Response(
                {"detail": "Email verification successful"}, status=status.HTTP_200_OK
            )
        else:
            return Response(
                {"detail": "Invalid or expired OTP token"},
                status=status.HTTP_400_BAD_REQUEST,
            )


class ResendTokenView(APIView):
    def post(self, request, *args, **kwargs):
        email = request.data.get(
            "email"
        )  # Assuming the email is sent in the request data

        if not email:
            return Response(
                {"detail": "Email is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user_verification = UserVerification.objects.get(user__email=email)
        except UserVerification.DoesNotExist:
            return Response(
                {"detail": "User verification record not found"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if user_verification.is_email_verified():
            return Response(
                {"detail": "Email is already verified"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if user_verification.otp_expiration_time > timezone.now():
            # The previous OTP has not expired, no need to resend
            return Response(
                {"detail": "Previous OTP has not expired"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Send the new OTP via email
        send_verification_email(user_verification.user)

        return Response(
            {"detail": "New OTP has been sent to your email"}, status=status.HTTP_200_OK
        )


class LoginView(APIView):
    def post(self, request, *args, **kwargs):
        """
        Handle POST requests to the API endpoint.

        Args:
            request: The request object containing the data.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
            A response object with the appropriate tokens and status code.
        """
        # Get the email and password from the request data
        email = request.data.get("email")
        password = request.data.get("password")

        # Check if email or password is missing
        if not email or not password:
            return self.invalid_credentials_response()

        # Authenticate the user with the provided email and password
        user = authenticate(request, email=email, password=password)

        # Check if user is None (invalid credentials)
        if user is None:
            return self.invalid_credentials_response()

        # Check if user's email is not verified
        if not user.is_verified:
            return self.unverified_email_response()

        # Create JWT tokens for the authenticated user
        tokens = create_jwt_pair_for_user(user)

        # Return the tokens with a 200 OK status code
        return Response(tokens, status=status.HTTP_200_OK)

    def invalid_credentials_response(self):
        return Response(
            {"detail": "Invalid email or password."},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    def unverified_email_response(self):
        return Response(
            {"detail": "Email is not verified."},
            status=status.HTTP_401_UNAUTHORIZED,
        )


class UserPasswordResetView(APIView):
    def post(self, request, *args, **kwargs):
        new_password = request.data.get("password")
        confirm_password = request.data.get("confirm_password")
        otp_code = request.data.get("otp_code")

        if not new_password:
            return Response(
                {"detail": "New Password is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not otp_code:
            return Response(
                {"detail": "OTP is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user_verification = UserVerification.objects.get(
                user__email=email, email_otp=otp_code
            )
        except UserVerification.DoesNotExist:
            return Response(
                {"detail": "User not found or verification record missing"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if user_verification.expired:
            return Response(
                {"detail": "OTP has expired, request new OTP"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if new_password != confirm_password:
            return Response(
                {"detail": "New password and confirm password do not match"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = user_verification.user
        user.set_password(new_password)
        user.save()

        return Response(
            {"detail": "Password reset successfully"}, status=status.HTTP_200_OK
        )


class GetAvailableRidersView(APIView):
    permission_classes = [IsAuthenticated]
    SEARCH_RADIUS_KM = 5

    def get_matrix_client(self, client):
        """Initialize and return the Matrix API client."""
        api_key = (
            settings.MAPBOX_API_KEY if client == "mapbox" else settings.TOMTOM_API_KEY
        )
        return (
            MapboxDistanceDuration(api_key)
            if client == "mapbox"
            else TomTomDistanceMatrix(api_key)
        )

    def validate_parameters(
        self, origin_lat, origin_long, item_capacity, is_fragile, customer_email
    ):
        """Validate input parameters."""
        try:
            origin_lat = float(origin_lat)
            origin_long = float(origin_long)
            item_capacity = float(item_capacity)
            is_fragile = str_to_bool(is_fragile)
        except ValueError:
            return False, "Invalid or missing parameters"

        if (
            not all(
                isinstance(param, (float, int))
                for param in [origin_lat, origin_long, item_capacity]
            )
            or not isinstance(is_fragile, bool)
            or not isinstance(customer_email, str)
        ):
            return False, "Invalid or missing parameters"
        return True, ""

    def handle_matrix_api_error(self, e):
        """Handle Matrix API errors."""
        return Response(
            {"status": "error", "message": f"Matrix API error: {str(e)}"}, status=400
        )

    @retry(Exception, tries=3, delay=1, backoff=2, logger=logger)
    def call_matrix_api(self, origin, destinations, client, method_name):
        """Call Matrix API with retry logic."""
        matrix_client = self.get_matrix_client(client)
        matrix_origin = f"{origin[1]},{origin[0]}"
        method_to_call = getattr(matrix_client, method_name)
        return method_to_call(matrix_origin, destinations)

    def get(self, request, *args, **kwargs):
        origin_long = float(request.GET.get("origin_long"))
        origin_lat = float(request.GET.get("origin_lat"))
        item_capacity = request.GET.get("item_capacity")
        is_fragile = request.GET.get("is_fragile")
        customer_email = request.GET.get("customer_email")

        is_valid, validation_message = self.validate_parameters(
            origin_lat, origin_long, item_capacity, is_fragile, customer_email
        )
        if not is_valid:
            return Response(
                {"status": "error", "message": validation_message}, status=400
            )

        origin = (origin_lat, origin_long)
        riders_location_data = self.get_supabase_rider()

        if riders_location_data and origin:
            calculator = DistanceCalculator(origin)
            location_within_radius = calculator.destinations_within_radius(
                riders_location_data, self.SEARCH_RADIUS_KM
            )
            try:
                results = self.call_matrix_api(
                    origin,
                    location_within_radius,
                    client="tomtom",
                    method_name="get_async_response",
                )
                self.send_customer_notification(
                    customer=customer_email, message="Notifying riders close to you"
                )
                self.send_riders_notification(results)
            except Exception as e:
                logger.error(f"Error processing API request: {str(e)}")
                try:
                    # Fallback mechanism: Use Mapbox API as an alternative
                    results = self.call_matrix_api(
                        origin,
                        location_within_radius,
                        client="mapbox",
                        method_name="get_distance_duration",
                    )
                    self.send_customer_notification(
                        customer=customer_email, message="Notifying riders close to you"
                    )
                    self.send_riders_notification(results)
                except Exception as e:
                    logger.error(f"Error in Mapbox API call: {str(e)}")
                    return self.handle_matrix_api_error(e)

        return Response(
            {"status": "success", "message": "Notification sent successfully"}
        )

    def get_supabase_rider(self):
        # Fetch all riders locations
        try:
            response = (
                supabase.table(riders_table)
                .select("rider_email", "current_lat", "current_long")
                .execute()
            )
            return [
                {
                    "email": rider["rider_email"],
                    "location": (rider["current_lat"], rider["current_long"]),
                }
                for rider in response.data
            ]
        except Exception as e:
            logger.error(f"Supabase API error: {str(e)}")
            return

    def send_riders_notification(self, riders):
        try:
            for rider in riders:
                rider_email = rider.get("email")
                distance = rider.get("distance")
                duration = rider.get("duration")
                if all([rider_email, distance is not None, duration is not None]):
                    message = f"New Delivery Request: Order is {distance} m and {duration} away"
                    supabase.table(riders_table).update(
                        {"broadcast_message": message}
                    ).eq("rider_email", rider_email).execute()
                else:
                    logger.warning(
                        "Invalid rider data: email, distance, or duration missing."
                    )
        except Exception as e:
            logger.error(f"Supabase API error: {str(e)}")

    def send_customer_notification(self, customer, message):
        try:
            supabase.table(customers_table).update({"notification": message}).eq(
                "email", customer
            ).execute()
        except Exception as e:
            logger.error(f"Supabase API error: {str(e)}")
