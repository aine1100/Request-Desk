from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Count

from desk.errors import DomainError
from desk.models import DatasetRequest, Role, User
from desk.normalize import normalize_task
from desk.services.locking import locked


def visible_requests(user):
    queryset = DatasetRequest.objects.select_related("client").annotate(
        assigned_count=Count("assignments")
    )
    if user.role == Role.CLIENT:
        queryset = queryset.filter(client=user)
    return queryset


def get_visible_request(user, pk, *, detailed=False):
    queryset = visible_requests(user)
    if detailed:
        queryset = queryset.prefetch_related(
            "assignments__episode", "events__actor"
        )
    try:
        return queryset.get(pk=pk)
    except DatasetRequest.DoesNotExist:
        raise DomainError("Not found.", status=404)


def create_request(user, *, task_name, episodes_requested, deadline, notes=""):
    if user.role != Role.CLIENT:
        raise DomainError("Only clients can create requests.", status=403)
    task_name = normalize_task(task_name)
    if not task_name:
        raise DomainError("task_name is required.")
    from desk.models import RequestStatus, StatusEvent

    request_obj = DatasetRequest.objects.create(
        client=user,
        task_name=task_name,
        episodes_requested=episodes_requested,
        deadline=deadline,
        notes=(notes or "").strip(),
        status=RequestStatus.SUBMITTED,
    )
    StatusEvent.objects.create(
        request=request_obj,
        from_status="",
        to_status=RequestStatus.SUBMITTED,
        actor=user,
    )
    return request_obj


TRANSITIONS = {
    "submitted": {"in_progress": {"operator", "admin"}},
    "in_progress": {"delivered": {"operator", "admin"}},
    "delivered": {
        "accepted": {"client"},
        "rejected": {"client"},
    },
    "rejected": {"in_progress": {"operator", "admin"}},
}


def transition(request_obj, user, to_status):
    from django.db import transaction

    from desk.models import RequestStatus, StatusEvent

    if to_status not in RequestStatus.values:
        raise DomainError("Unknown status.")
    allowed_for_role = TRANSITIONS.get(request_obj.status, {})
    if to_status not in allowed_for_role:
        raise DomainError(
            f"Cannot move from {request_obj.status} to {to_status}."
        )
    if user.role not in allowed_for_role[to_status]:
        raise DomainError("You cannot perform this status change.", status=403)
    if user.role == Role.CLIENT and request_obj.client_id != user.id:
        raise DomainError("Not found.", status=404)

    with transaction.atomic():
        locked_request = locked(
            DatasetRequest.objects.filter(pk=request_obj.pk)
        ).get()
        if locked_request.status != request_obj.status:
            raise DomainError("Status changed. Refresh and try again.", status=409)
        if to_status == RequestStatus.DELIVERED:
            assigned = locked_request.assignments.count()
            if assigned < locked_request.episodes_requested:
                raise DomainError(
                    f"Need {locked_request.episodes_requested} assigned episodes "
                    f"before delivery; {assigned} assigned."
                )
        previous = locked_request.status
        locked_request.status = to_status
        locked_request.save(update_fields=["status", "updated_at"])
        StatusEvent.objects.create(
            request=locked_request,
            from_status=previous,
            to_status=to_status,
            actor=user,
        )
    return locked_request


def assign_episode(request_obj, user, episode_id):
    from django.db import IntegrityError, transaction

    from desk.models import Assignment, Episode, Quality, RequestStatus

    if user.role not in (Role.OPERATOR, Role.ADMIN):
        raise DomainError("Only operators can assign episodes.", status=403)
    episode_id = (episode_id or "").strip().upper()
    if not episode_id:
        raise DomainError("episode_id is required.")

    with transaction.atomic():
        locked_request = locked(
            DatasetRequest.objects.filter(pk=request_obj.pk)
        ).get()
        if locked_request.status != RequestStatus.IN_PROGRESS:
            raise DomainError(
                "Episodes can only be assigned while the request is in progress."
            )
        try:
            episode = locked(Episode.objects.filter(episode_id=episode_id)).get()
        except Episode.DoesNotExist:
            raise DomainError("Episode not found.", status=404)
        if episode.quality not in (Quality.GOOD, Quality.USABLE):
            raise DomainError("Only good or usable episodes can be assigned.")
        existing = (
            Assignment.objects.filter(episode=episode).select_related("request").first()
        )
        if existing:
            if existing.request_id == locked_request.id:
                raise DomainError(
                    "Episode is already assigned to this request.", status=409
                )
            raise DomainError(
                f"Episode is already assigned to request {existing.request_id}.",
                status=409,
            )
        try:
            Assignment.objects.create(
                request=locked_request, episode=episode, assigned_by=user
            )
        except IntegrityError:
            raise DomainError("Episode is already assigned to a request.", status=409)
    return locked_request


def unassign_episode(request_obj, user, episode_id):
    from django.db import transaction

    from desk.models import Assignment, RequestStatus

    if user.role not in (Role.OPERATOR, Role.ADMIN):
        raise DomainError("Only operators can unassign episodes.", status=403)
    episode_id = (episode_id or "").strip().upper()

    with transaction.atomic():
        locked_request = locked(
            DatasetRequest.objects.filter(pk=request_obj.pk)
        ).get()
        if locked_request.status != RequestStatus.IN_PROGRESS:
            raise DomainError(
                "Episodes can only be removed while the request is in progress."
            )
        deleted, _ = Assignment.objects.filter(
            request=locked_request, episode__episode_id=episode_id
        ).delete()
        if not deleted:
            raise DomainError("Assignment not found.", status=404)
    return locked_request


def create_user_account(*, email, password, name, role, organisation=""):
    email = email.strip().lower()
    if User.objects.filter(email=email).exists():
        raise DomainError("A user with this email already exists.", status=409)
    if role not in Role.values:
        raise DomainError("Unknown role.")
    user = User(
        email=email,
        name=name.strip(),
        role=role,
        organisation=(organisation or "").strip(),
        is_active=True,
    )
    try:
        validate_password(password, user=user)
    except DjangoValidationError as exc:
        raise DomainError(" ".join(exc.messages))
    user.set_password(password)
    user.save()
    return user


def update_user(actor, user, changes):
    new_role = changes.get("role", user.role)
    new_active = changes.get("is_active", user.is_active)
    if "is_active" in changes and changes["is_active"] is False and actor.pk == user.pk:
        raise DomainError("You cannot deactivate your own account.")
    losing_admin = user.role == Role.ADMIN and (
        new_role != Role.ADMIN or not new_active
    )
    if losing_admin:
        another_admin = (
            User.objects.filter(role=Role.ADMIN, is_active=True)
            .exclude(pk=user.pk)
            .exists()
        )
        if not another_admin:
            raise DomainError("Cannot deactivate or demote the last active admin.")
    if "name" in changes:
        name = changes["name"].strip()
        if not name:
            raise DomainError("name is required.")
        user.name = name
    if "organisation" in changes:
        user.organisation = changes["organisation"].strip()
    if "role" in changes:
        if changes["role"] not in Role.values:
            raise DomainError("Unknown role.")
        user.role = changes["role"]
    if "is_active" in changes:
        user.is_active = changes["is_active"]
    if changes.get("password"):
        try:
            validate_password(changes["password"], user=user)
        except DjangoValidationError as exc:
            raise DomainError(" ".join(exc.messages))
        user.set_password(changes["password"])
    user.save()
    return user
