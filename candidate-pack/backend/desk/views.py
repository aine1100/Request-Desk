from django.db.models import F
from django.http import JsonResponse
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.generics import GenericAPIView
from rest_framework_simplejwt.tokens import RefreshToken

from desk.errors import DomainError
from desk.models import Episode, Quality, RequestStatus, User
from desk.normalize import normalize_task
from desk.permissions import IsAdmin, IsOperatorOrAdmin
from desk.serializers import (
    AssignmentCreateSerializer,
    DatasetRequestDetailSerializer,
    DatasetRequestListSerializer,
    EpisodeSerializer,
    RequestCreateSerializer,
    TransitionSerializer,
    UserCreateSerializer,
    UserPatchSerializer,
    UserSerializer,
)
from desk.services.analytics import analytics_for_range
from desk.services.importing import import_uploaded
from desk.services.workflow import (
    assign_episode,
    create_request,
    create_user_account,
    get_visible_request,
    transition,
    unassign_episode,
    update_user,
    visible_requests,
)


class DeskAPIView(GenericAPIView):
    def handle_exception(self, exc):
        if isinstance(exc, DomainError):
            return Response({"detail": exc.message}, status=exc.status)
        return super().handle_exception(exc)


def health(_request):
    return JsonResponse({"status": "ok"})


class LoginView(DeskAPIView):
    permission_classes = [AllowAny]

    def post(self, request):
        from django.contrib.auth import authenticate

        email = (request.data.get("email") or "").strip().lower()
        password = request.data.get("password") or ""
        user = authenticate(request, username=email, password=password)
        if user is None:
            return Response({"detail": "Invalid email or password."}, status=401)
        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": UserSerializer(user).data,
            }
        )


class MeView(DeskAPIView):
    def get(self, request):
        return Response(UserSerializer(request.user).data)


class UserListCreateView(DeskAPIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        users = User.objects.order_by("email")
        return Response(UserSerializer(users, many=True).data)

    def post(self, request):
        serializer = UserCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = create_user_account(**serializer.validated_data)
        return Response(UserSerializer(user).data, status=201)


class UserDetailView(DeskAPIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def patch(self, request, pk):
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            raise DomainError("Not found.", status=404)
        serializer = UserPatchSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        update_user(request.user, user, serializer.validated_data)
        user.refresh_from_db()
        return Response(UserSerializer(user).data)


class EpisodeListView(DeskAPIView):
    permission_classes = [IsAuthenticated, IsOperatorOrAdmin]

    def get(self, request):
        queryset = Episode.objects.annotate(
            assigned_request_id=F("assignment__request_id")
        )
        task_name = request.query_params.get("task_name", "")
        if task_name.strip():
            queryset = queryset.filter(task_name__icontains=normalize_task(task_name))
        quality = request.query_params.get("quality", "").strip().lower()
        if quality:
            if quality not in Quality.values:
                raise DomainError("quality must be good, usable, or bad.")
            queryset = queryset.filter(quality=quality)
        available = request.query_params.get("available", "").strip().lower()
        if available in {"1", "true", "yes"}:
            queryset = queryset.filter(assignment__isnull=True)
        queryset = queryset.order_by("-recorded_at", "episode_id")
        page = self.paginate_queryset(queryset)
        if page is not None:
            return self.get_paginated_response(EpisodeSerializer(page, many=True).data)
        return Response(EpisodeSerializer(queryset, many=True).data)


class EpisodeImportView(DeskAPIView):
    permission_classes = [IsAuthenticated, IsOperatorOrAdmin]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        uploaded = request.FILES.get("file")
        if uploaded is None:
            raise DomainError("file is required.")
        if uploaded.size > 50 * 1024 * 1024:
            raise DomainError("File is larger than 50MB. Use the import command for bigger exports.")
        return Response(import_uploaded(uploaded))


class RequestListCreateView(DeskAPIView):
    def get(self, request):
        queryset = visible_requests(request.user).order_by("-created_at")
        status = request.query_params.get("status", "").strip()
        if status:
            if status not in RequestStatus.values:
                raise DomainError("Unknown status.")
            queryset = queryset.filter(status=status)
        page = self.paginate_queryset(queryset)
        serializer = DatasetRequestListSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = RequestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        created = create_request(request.user, **serializer.validated_data)
        obj = get_visible_request(request.user, created.pk)
        return Response(DatasetRequestListSerializer(obj).data, status=201)


class RequestDetailView(DeskAPIView):
    def get(self, request, pk):
        obj = get_visible_request(request.user, pk, detailed=True)
        return Response(DatasetRequestDetailSerializer(obj).data)


class RequestTransitionView(DeskAPIView):
    def post(self, request, pk):
        obj = get_visible_request(request.user, pk)
        serializer = TransitionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        transition(obj, request.user, serializer.validated_data["to_status"])
        updated = get_visible_request(request.user, pk, detailed=True)
        return Response(DatasetRequestDetailSerializer(updated).data)


class AssignmentCreateView(DeskAPIView):
    permission_classes = [IsAuthenticated, IsOperatorOrAdmin]

    def post(self, request, pk):
        obj = get_visible_request(request.user, pk)
        serializer = AssignmentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        assign_episode(obj, request.user, serializer.validated_data["episode_id"])
        updated = get_visible_request(request.user, pk, detailed=True)
        return Response(DatasetRequestDetailSerializer(updated).data, status=201)


class AssignmentDeleteView(DeskAPIView):
    permission_classes = [IsAuthenticated, IsOperatorOrAdmin]

    def delete(self, request, pk, episode_id):
        obj = get_visible_request(request.user, pk)
        unassign_episode(obj, request.user, episode_id)
        updated = get_visible_request(request.user, pk, detailed=True)
        return Response(DatasetRequestDetailSerializer(updated).data)


class AnalyticsView(DeskAPIView):
    permission_classes = [IsAuthenticated, IsOperatorOrAdmin]

    def get(self, request):
        payload = analytics_for_range(
            request.query_params.get("start"),
            request.query_params.get("end"),
        )
        return Response(payload)
