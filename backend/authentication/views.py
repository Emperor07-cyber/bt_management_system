from django.utils import timezone

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import User
from .serializers import (
    LoginSerializer,
    UserSerializer,
)


class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer

    def post(self, request, *args, **kwargs):
        response = super().post(
            request,
            *args,
            **kwargs,
        )

        if response.status_code == status.HTTP_200_OK:
            username = request.data.get("username")

            try:
                user = User.objects.get(
                    username=username
                )

                user.last_login_at = timezone.now()

                user.save(
                    update_fields=["last_login_at"]
                )

            except User.DoesNotExist:
                pass

        return response


class MeView(APIView):

    def get(self, request):
        serializer = UserSerializer(
            request.user
        )

        return Response(serializer.data)