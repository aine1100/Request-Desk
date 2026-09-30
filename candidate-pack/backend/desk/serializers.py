from rest_framework import serializers

from desk.models import (
    Assignment,
    DatasetRequest,
    Episode,
    Quality,
    RequestStatus,
    Role,
    StatusEvent,
    User,
)
from desk.normalize import normalize_task


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "name", "role", "organisation", "is_active"]


class UserCreateSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(min_length=8, write_only=True)
    name = serializers.CharField(max_length=200)
    role = serializers.ChoiceField(choices=Role.choices)
    organisation = serializers.CharField(max_length=200, allow_blank=True, required=False)


class UserPatchSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200, required=False)
    role = serializers.ChoiceField(choices=Role.choices, required=False)
    organisation = serializers.CharField(max_length=200, allow_blank=True, required=False)
    is_active = serializers.BooleanField(required=False)
    password = serializers.CharField(min_length=8, write_only=True, required=False)


class EpisodeSerializer(serializers.ModelSerializer):
    assigned_request_id = serializers.IntegerField(read_only=True, allow_null=True)

    class Meta:
        model = Episode
        fields = [
            "episode_id",
            "robot_id",
            "task_name",
            "recorded_at",
            "duration_seconds",
            "operator_name",
            "quality",
            "assigned_request_id",
        ]


class AssignmentSerializer(serializers.ModelSerializer):
    episode_id = serializers.CharField(source="episode.episode_id", read_only=True)
    task_name = serializers.CharField(source="episode.task_name", read_only=True)
    quality = serializers.CharField(source="episode.quality", read_only=True)
    robot_id = serializers.CharField(source="episode.robot_id", read_only=True)
    duration_seconds = serializers.IntegerField(
        source="episode.duration_seconds", read_only=True
    )

    class Meta:
        model = Assignment
        fields = [
            "episode_id",
            "task_name",
            "quality",
            "robot_id",
            "duration_seconds",
            "assigned_at",
        ]


class StatusEventSerializer(serializers.ModelSerializer):
    actor_email = serializers.EmailField(source="actor.email", read_only=True)
    actor_name = serializers.CharField(source="actor.name", read_only=True)

    class Meta:
        model = StatusEvent
        fields = [
            "from_status",
            "to_status",
            "actor_email",
            "actor_name",
            "created_at",
        ]


class DatasetRequestListSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source="client.name", read_only=True)
    client_email = serializers.EmailField(source="client.email", read_only=True)
    assigned_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = DatasetRequest
        fields = [
            "id",
            "client_name",
            "client_email",
            "task_name",
            "episodes_requested",
            "assigned_count",
            "deadline",
            "notes",
            "status",
            "created_at",
            "updated_at",
        ]


class DatasetRequestDetailSerializer(DatasetRequestListSerializer):
    assignments = AssignmentSerializer(many=True, read_only=True)
    events = StatusEventSerializer(many=True, read_only=True)

    class Meta(DatasetRequestListSerializer.Meta):
        fields = DatasetRequestListSerializer.Meta.fields + ["assignments", "events"]


class RequestCreateSerializer(serializers.Serializer):
    task_name = serializers.CharField(max_length=200)
    episodes_requested = serializers.IntegerField(min_value=1, max_value=100000)
    deadline = serializers.DateField()
    notes = serializers.CharField(allow_blank=True, required=False, max_length=5000)

    def validate_task_name(self, value):
        task_name = normalize_task(value)
        if not task_name:
            raise serializers.ValidationError("task_name is required.")
        return task_name


class TransitionSerializer(serializers.Serializer):
    to_status = serializers.ChoiceField(choices=RequestStatus.choices)


class AssignmentCreateSerializer(serializers.Serializer):
    episode_id = serializers.CharField(max_length=32)


class EpisodeFilterSerializer(serializers.Serializer):
    quality = serializers.ChoiceField(choices=Quality.choices, required=False)
