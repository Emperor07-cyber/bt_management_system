from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import User


class LoginSerializer(TokenObtainPairSerializer):

    username_field = "username"

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        token["username"] = user.username
        token["user_id"] = user.id
        token["employee_id"] = user.employee_id

        return token


class UserSerializer(serializers.ModelSerializer):

    employee_name = serializers.SerializerMethodField()
    roles = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "status",
            "employee",
            "employee_name",
            "last_login_at",
            "roles",
        ]

    def get_employee_name(self, obj):
        if not obj.employee:
            return None

        return f"{obj.employee.first_name} {obj.employee.last_name}"
    def get_roles(self, obj):
        return list(
        obj.user_roles.values_list("role__name", flat=True)
    )