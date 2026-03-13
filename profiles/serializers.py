from rest_framework import serializers
from .models import Profile
from .constants import PROFILE_COMPLETION_FIELDS


class ProfileReadSerializer(serializers.ModelSerializer):
    age = serializers.SerializerMethodField()
    bmi = serializers.SerializerMethodField()
    bmi_category = serializers.SerializerMethodField()
    tdee = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = "__all__"

    def get_age(self, obj):
        return obj.age

    def get_bmi(self, obj):
        return obj.bmi

    def get_bmi_category(self, obj):
        return obj.bmi_category

    def get_tdee(self, obj):
        return obj.tdee


class ProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        exclude = [
            "user",
            "poa_points",
            "day_streak",
            "profile_completed_awarded",
            "updated_at",
        ]


class ProfileCompletionStatusSerializer(serializers.Serializer):

    is_complete = serializers.BooleanField()
    missing_fields = serializers.ListField(child=serializers.CharField())
    completion_percentage = serializers.FloatField()