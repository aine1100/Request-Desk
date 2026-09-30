from rest_framework.test import APITestCase

from desk.models import StatusEvent
from desk.tests.helpers import make_episode, make_user


class TransitionTests(APITestCase):
    def setUp(self):
        self.client_user = make_user("client", email="client@test.example", name="Acme")
        self.operator = make_user("operator", email="ops@test.example", name="Olu")
        self.client.force_authenticate(self.client_user)
        created = self.client.post(
            "/api/requests/",
            {"task_name": "pick cup", "episodes_requested": 1, "deadline": "2026-10-20"},
        )
        self.request_id = created.json()["id"]

    def test_only_valid_transitions_and_delivery_requires_assignments(self):
        self.client.force_authenticate(self.operator)
        skipped = self.client.post(
            f"/api/requests/{self.request_id}/transition/",
            {"to_status": "delivered"},
        )
        self.assertEqual(skipped.status_code, 400)

        started = self.client.post(
            f"/api/requests/{self.request_id}/transition/",
            {"to_status": "in_progress"},
        )
        self.assertEqual(started.status_code, 200)
        self.assertEqual(started.json()["events"][-1]["actor_email"], self.operator.email)
        self.assertEqual(started.json()["events"][-1]["from_status"], "submitted")

        early = self.client.post(
            f"/api/requests/{self.request_id}/transition/",
            {"to_status": "delivered"},
        )
        self.assertEqual(early.status_code, 400)

        make_episode("EP-10", quality="good")
        assigned = self.client.post(
            f"/api/requests/{self.request_id}/assignments/",
            {"episode_id": "EP-10"},
        )
        self.assertEqual(assigned.status_code, 201)

        delivered = self.client.post(
            f"/api/requests/{self.request_id}/transition/",
            {"to_status": "delivered"},
        )
        self.assertEqual(delivered.status_code, 200)
        self.assertEqual(delivered.json()["status"], "delivered")

        self.client.force_authenticate(self.operator)
        accepted_by_ops = self.client.post(
            f"/api/requests/{self.request_id}/transition/",
            {"to_status": "accepted"},
        )
        self.assertEqual(accepted_by_ops.status_code, 403)

        self.client.force_authenticate(self.client_user)
        accepted = self.client.post(
            f"/api/requests/{self.request_id}/transition/",
            {"to_status": "accepted"},
        )
        self.assertEqual(accepted.status_code, 200)
        self.assertEqual(accepted.json()["status"], "accepted")
        terminal = self.client.post(
            f"/api/requests/{self.request_id}/transition/",
            {"to_status": "in_progress"},
        )
        self.assertEqual(terminal.status_code, 400)
        self.assertEqual(
            StatusEvent.objects.filter(request_id=self.request_id).count(), 4
        )

    def test_reject_then_rework(self):
        make_episode("EP-11", quality="usable")
        self.client.force_authenticate(self.operator)
        self.client.post(
            f"/api/requests/{self.request_id}/transition/",
            {"to_status": "in_progress"},
        )
        self.client.post(
            f"/api/requests/{self.request_id}/assignments/",
            {"episode_id": "EP-11"},
        )
        self.client.post(
            f"/api/requests/{self.request_id}/transition/",
            {"to_status": "delivered"},
        )
        self.client.force_authenticate(self.client_user)
        rejected = self.client.post(
            f"/api/requests/{self.request_id}/transition/",
            {"to_status": "rejected"},
        )
        self.assertEqual(rejected.status_code, 200)

        self.client.force_authenticate(self.operator)
        resumed = self.client.post(
            f"/api/requests/{self.request_id}/transition/",
            {"to_status": "in_progress"},
        )
        self.assertEqual(resumed.status_code, 200)
        self.assertEqual(resumed.json()["status"], "in_progress")
