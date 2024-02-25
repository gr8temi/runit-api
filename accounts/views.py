from django.db import transaction, IntegrityError
from django.contrib.auth import authenticate
from django.utils import timezone
from map_clients.map_clients import MapClientsManager
from map_clients.supabase_query import SupabaseTransactions
from .tokens import create_jwt_pair_for_user
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.serializers import ValidationError
from rest_framework import generics, status
from .serializers import *
from .models import *
from .utils import (
    DistanceCalculator,
    send_verification_email,
    str_to_bool,
)
import logging


logger = logging.getLogger(__name__)

map_clients_manager = MapClientsManager()
supabase = SupabaseTransactions()


class BaseRegistrationView(generics.CreateAPIView):
    serializer_class = None
    user_model = None

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        # Log the request data
        logger.debug(f"Request_data: {request.data}")

        # Extract the user data from the request
        user_data = request.data

        # Validate the user data using the UserSerializer
        user_serializer = UserSerializer(data=user_data)

        if user_serializer.is_valid():
            # Access the validated data after validation
            user_data = user_serializer.validated_data

            if user_data:
                try:
                    with transaction.atomic():
                        # Save the user and create a user object
                        user = user_serializer.save()

                        # Create the Rider or Customer object
                        self.user_model.objects.create(
                            user=user,
                            vehicle_registration_number=request.data[
                                "vehicle_registration_number"
                            ],
                            min_capacity=request.data["min_capacity"],
                            max_capacity=request.data["max_capacity"],
                            fragile_item_allowed=request.data["fragile_item_allowed"],
                            charge_per_km=request.data["charge_per_km"],
                        )

                        # Serialize the user object
                        user_obj_serializer = self.serializer_class(
                            {"user": user, **request.data}
                        ).data

                        if user_obj_serializer:
                            # Send a welcome email or perform any additional actions
                            send_verification_email(user, "registration")

                            # Return a response with the serialized user object and a success message
                            return Response(
                                {
                                    "data": user_obj_serializer,
                                    "message": f"{self.user_model.__name__} registration successful",
                                },
                                status=status.HTTP_201_CREATED,
                            )
                        else:
                            # Raise a validation error if the user object serialization fails
                            raise ValidationError(detail=user_obj_serializer.errors)
                except IntegrityError as e:
                    # Handle integrity errors
                    logger.error(f"Integrity error: {e}")
                    return Response(
                        {
                            "detail": "Integrity error. Please ensure the data is unique."
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                except Exception as e:
                    # Handle unexpected errors
                    logger.error(f"An unexpected error occurred: {e}")
                    return Response(
                        {"detail": "An unexpected error occurred."},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    )
        else:
            # Raise a validation error if the user serializer is not valid
            raise ValidationError(detail=user_serializer.errors)


class RiderRegistrationView(BaseRegistrationView):
    serializer_class = RiderSerializer
    user_model = Rider


class CustomerRegistrationView(BaseRegistrationView):
    serializer_class = CustomerSerializer
    user_model = Customer


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

        # Check if user_verification exists and the email_otp has not expired
        if user_verification and (
            not user_verification.has_expired and not user_verification.user.is_verified
        ):
            # Mark the user as verified
            user = user_verification.user
            user.is_verified = True
            user.save()

            # Invalidate the OTP token
            user_verification.used = True
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
            user_verification = UserVerification.objects.get(otp=otp_code, used=False)
        except UserVerification.DoesNotExist:
            return Response(
                {"detail": "User not found or verification record missing"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if user_verification.has_expired:
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

        user_verification.used = True
        user_verification.save()

        return Response(
            {"detail": "Password reset successfully"}, status=status.HTTP_200_OK
        )


class GetAvailableRidersView(APIView):
    permission_classes = [IsAuthenticated]
    SEARCH_RADIUS_KM = 5

    def validate_parameters(
        self, origin_lat, origin_long, item_capacity, is_fragile, customer_email, price_offer
    ):
        """Validate input parameters."""
        try:
            origin_lat = float(origin_lat)
            origin_long = float(origin_long)
            item_capacity = float(item_capacity)
            price_offer = float(price_offer)
            is_fragile = str_to_bool(is_fragile)
        except ValueError:
            return False, "Invalid or missing parameters"

        if (
            not all(
                isinstance(param, (float, int))
                for param in [origin_lat, origin_long, item_capacity, price_offer]
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

    def get(self, request, *args, **kwargs):
        origin_long = float(request.GET.get("origin_long"))
        origin_lat = float(request.GET.get("origin_lat"))
        item_capacity = request.GET.get("item_capacity")
        is_fragile = request.GET.get("is_fragile")
        customer_email = request.GET.get("customer_email")
        price_offer = request.GET.get("price")

        is_valid, validation_message = self.validate_parameters(
            origin_lat, origin_long, item_capacity, is_fragile, customer_email, price_offer
        )
        if not is_valid:
            return Response(
                {"status": "error", "message": validation_message}, status=400
            )

        origin = f"{origin_long},{origin_lat}"
        fields = ["rider_email", "current_lat", "current_long"]
        riders_location_data = supabase.get_supabase_riders(fields=fields)

        if riders_location_data and origin:
            calculator = DistanceCalculator(origin)
            location_within_radius = calculator.destinations_within_radius(
                riders_location_data, self.SEARCH_RADIUS_KM
            )
            if not location_within_radius:
                supabase.send_customer_notification(
                    customer=customer_email, message="No rider around you"
                )
            else:
                try:
                    results = self.get_matrix_results(origin, location_within_radius)

                except Exception as e:
                    logger.error(f"Error processing API request: {str(e)}")
                    map_clients_manager.switch_client()
                    results = self.get_matrix_results(origin, location_within_radius)

            supabase.send_customer_notification(
                customer=customer_email, message="Notifying riders close to you"
            )

            supabase.send_riders_notification(results, price_offer)

        return Response(
            {"status": "success", "message": "Notification sent successfully"}
        )

    def get_matrix_results(self, origin, destinations):
        """Get results from Matrix API."""
        map_client = map_clients_manager.get_client()
        results = map_client.get_distances_duration(origin, destinations)
        return results
