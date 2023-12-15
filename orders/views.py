from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Order
from .serializers import OrderSerializer, OrderDetailSerializer
from django.shortcuts import get_object_or_404


class OrderCreateView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = OrderSerializer(data=request.data)

        if serializer.is_valid():
            quantity = serializer.validated_data['quantity']
            pickup_location = serializer.validated_data['pickup_location']
            delivery_location = serializer.validated_data['delivery_location']

            order = Order.objects.create(
                product_id=product_id,
                quantity=quantity,
                pickup_location=pickup_location,
                delivery_location=delivery_location,
            )

            return Response({'detail': 'Order created successfully'}, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class OrderDetailView(APIView):
    def get(self, request, order_id, *args, **kwargs):
        order = get_object_or_404(Order, id=order_id)
        serializer = OrderDetailSerializer(order)
        return Response(serializer.data, status=status.HTTP_200_OK)
