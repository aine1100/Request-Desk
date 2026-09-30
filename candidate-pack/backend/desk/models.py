from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class Role(models.TextChoices):
    CLIENT = "client", "Client"
    OPERATOR = "operator", "Operator"
    ADMIN = "admin", "Admin"


class Quality(models.TextChoices):
    GOOD = "good", "Good"
    USABLE = "usable", "Usable"
    BAD = "bad", "Bad"


class RequestStatus(models.TextChoices):
    SUBMITTED = "submitted", "Submitted"
    IN_PROGRESS = "in_progress", "In progress"
    DELIVERED = "delivered", "Delivered"
    ACCEPTED = "accepted", "Accepted"
    REJECTED = "rejected", "Rejected"


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra):
        if not email:
            raise ValueError("Email is required.")
        email = self.normalize_email(email).lower()
        user = self.model(email=email, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra):
        extra.setdefault("role", Role.ADMIN)
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra)


class User(AbstractUser):
    username = None
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=200)
    role = models.CharField(max_length=20, choices=Role.choices)
    organisation = models.CharField(max_length=200, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.email


class Episode(models.Model):
    episode_id = models.CharField(max_length=32, unique=True)
    robot_id = models.CharField(max_length=32)
    task_name = models.CharField(max_length=200)
    recorded_at = models.DateTimeField()
    duration_seconds = models.PositiveIntegerField()
    operator_name = models.CharField(max_length=200)
    quality = models.CharField(max_length=16, choices=Quality.choices)

    class Meta:
        indexes = [
            models.Index(fields=["recorded_at", "robot_id"]),
            models.Index(fields=["quality", "task_name"]),
            models.Index(fields=["task_name"]),
        ]

    def __str__(self):
        return self.episode_id

    def comparable(self):
        return (
            self.robot_id,
            self.task_name,
            self.recorded_at,
            self.duration_seconds,
            self.operator_name,
            self.quality,
        )


class DatasetRequest(models.Model):
    client = models.ForeignKey(
        User, related_name="dataset_requests", on_delete=models.PROTECT
    )
    task_name = models.CharField(max_length=200)
    episodes_requested = models.PositiveIntegerField()
    deadline = models.DateField()
    notes = models.TextField(blank=True)
    status = models.CharField(
        max_length=20, choices=RequestStatus.choices, default=RequestStatus.SUBMITTED
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["client", "status"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"Request {self.pk} ({self.status})"


class Assignment(models.Model):
    request = models.ForeignKey(
        DatasetRequest, related_name="assignments", on_delete=models.CASCADE
    )
    episode = models.OneToOneField(
        Episode, related_name="assignment", on_delete=models.PROTECT
    )
    assigned_by = models.ForeignKey(User, on_delete=models.PROTECT)
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["assigned_at", "id"]


class StatusEvent(models.Model):
    request = models.ForeignKey(
        DatasetRequest, related_name="events", on_delete=models.CASCADE
    )
    from_status = models.CharField(max_length=20, blank=True)
    to_status = models.CharField(max_length=20)
    actor = models.ForeignKey(User, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "status_events"
        ordering = ["created_at", "id"]
        indexes = [
            models.Index(fields=["request", "to_status", "created_at"]),
            models.Index(fields=["to_status", "created_at"]),
        ]
