from django.utils import timezone

from desk.models import Episode, User


def make_user(role, email=None, name=None):
    email = email or f"{role}@test.example"
    return User.objects.create_user(
        email=email,
        password="password123",
        name=name or role.title(),
        role=role,
    )


def make_episode(episode_id, quality="good", task_name="pick cup", robot_id="arm-01"):
    return Episode.objects.create(
        episode_id=episode_id,
        robot_id=robot_id,
        task_name=task_name,
        recorded_at=timezone.now(),
        duration_seconds=30,
        operator_name="Aline",
        quality=quality,
    )
