from datetime import timedelta

from django.utils import timezone
from rest_framework.test import APITestCase

from desk.models import Episode, StatusEvent
from desk.tests.helpers import make_episode, make_user


class AnalyticsTests(APITestCase):
    def test_aggregates_are_scoped_to_the_range(self):
        operator = make_user("operator", email="ops@test.example")
        client = make_user("client", email="client@test.example")
        day = timezone.datetime(2026, 8, 10, 12, 0, tzinfo=timezone.get_current_timezone())
        Episode.objects.create(
            episode_id="EP-1",
            robot_id="arm-01",
            task_name="pick cup",
            recorded_at=day,
            duration_seconds=20,
            operator_name="Aline",
            quality="good",
        )
        Episode.objects.create(
            episode_id="EP-2",
            robot_id="arm-01",
            task_name="pick cup",
            recorded_at=day,
            duration_seconds=20,
            operator_name="Aline",
            quality="good",
        )
        Episode.objects.create(
            episode_id="EP-3",
            robot_id="arm-02",
            task_name="fold towel",
            recorded_at=day,
            duration_seconds=20,
            operator_name="Aline",
            quality="usable",
        )
        make_episode("EP-9", quality="good")

        self.client.force_authenticate(client)
        created = self.client.post(
            "/api/requests/",
            {"task_name": "pick cup", "episodes_requested": 1, "deadline": "2026-10-20"},
        )
        request_id = created.json()["id"]
        self.client.force_authenticate(operator)
        self.client.post(
            f"/api/requests/{request_id}/transition/", {"to_status": "in_progress"}
        )
        self.client.post(
            f"/api/requests/{request_id}/assignments/", {"episode_id": "EP-9"}
        )
        self.client.post(
            f"/api/requests/{request_id}/transition/", {"to_status": "delivered"}
        )
        submitted = StatusEvent.objects.get(request_id=request_id, to_status="submitted")
        delivered = StatusEvent.objects.get(request_id=request_id, to_status="delivered")
        base = timezone.now()
        StatusEvent.objects.filter(pk=submitted.pk).update(created_at=base)
        StatusEvent.objects.filter(pk=delivered.pk).update(
            created_at=base + timedelta(hours=2)
        )

        today = timezone.localdate().isoformat()
        response = self.client.get(f"/api/analytics/?start={today}&end={today}")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["requests_by_status"]["delivered"], 1)
        self.assertEqual(body["requests_by_status"]["submitted"], 0)
        self.assertAlmostEqual(body["median_seconds_submitted_to_delivered"], 7200, delta=5)

        historical = self.client.get("/api/analytics/?start=2026-08-10&end=2026-08-10")
        rows = historical.json()["episodes_per_day_per_robot"]
        arm = next(row for row in rows if row["robot_id"] == "arm-01")
        self.assertEqual(arm["count"], 2)
        self.assertEqual(arm["date"], "2026-08-10")
        top = historical.json()["top_tasks_by_good_episodes"]
        self.assertEqual(top[0]["task_name"], "pick cup")
        self.assertEqual(top[0]["count"], 2)
        self.assertTrue(all(item["task_name"] != "fold towel" for item in top))
