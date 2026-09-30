from rest_framework.test import APITestCase

from desk.tests.helpers import make_episode, make_user


class AssignmentTests(APITestCase):
    def setUp(self):
        self.client_user = make_user("client", email="client@test.example")
        self.operator = make_user("operator", email="ops@test.example")
        self.client.force_authenticate(self.client_user)
        created = self.client.post(
            "/api/requests/",
            {"task_name": "pick cup", "episodes_requested": 2, "deadline": "2026-10-20"},
        )
        self.request_id = created.json()["id"]
        self.client.force_authenticate(self.operator)
        self.client.post(
            f"/api/requests/{self.request_id}/transition/",
            {"to_status": "in_progress"},
        )

    def test_quality_and_single_assignment_rules(self):
        make_episode("EP-1", quality="bad")
        make_episode("EP-2", quality="good")
        make_episode("EP-3", quality="usable")

        bad = self.client.post(
            f"/api/requests/{self.request_id}/assignments/",
            {"episode_id": "ep-1"},
        )
        self.assertEqual(bad.status_code, 400)

        first = self.client.post(
            f"/api/requests/{self.request_id}/assignments/",
            {"episode_id": "ep-2"},
        )
        self.assertEqual(first.status_code, 201)
        again = self.client.post(
            f"/api/requests/{self.request_id}/assignments/",
            {"episode_id": "EP-2"},
        )
        self.assertEqual(again.status_code, 409)

        second_client = make_user("client", email="other@test.example")
        self.client.force_authenticate(second_client)
        other_created = self.client.post(
            "/api/requests/",
            {"task_name": "fold towel", "episodes_requested": 1, "deadline": "2026-11-01"},
        )
        other_id = other_created.json()["id"]
        self.client.force_authenticate(self.operator)
        self.client.post(
            f"/api/requests/{other_id}/transition/", {"to_status": "in_progress"}
        )
        stolen = self.client.post(
            f"/api/requests/{other_id}/assignments/",
            {"episode_id": "EP-2"},
        )
        self.assertEqual(stolen.status_code, 409)

        moved = self.client.delete(
            f"/api/requests/{self.request_id}/assignments/EP-2/"
        )
        self.assertEqual(moved.status_code, 200)
        reused = self.client.post(
            f"/api/requests/{other_id}/assignments/",
            {"episode_id": "EP-2"},
        )
        self.assertEqual(reused.status_code, 201)
        usable = self.client.post(
            f"/api/requests/{self.request_id}/assignments/",
            {"episode_id": "EP-3"},
        )
        self.assertEqual(usable.status_code, 201)

    def test_cannot_assign_before_work_starts(self):
        client = make_user("client", email="fresh@test.example")
        self.client.force_authenticate(client)
        created = self.client.post(
            "/api/requests/",
            {"task_name": "wipe table", "episodes_requested": 1, "deadline": "2026-12-01"},
        )
        make_episode("EP-9", quality="good", task_name="wipe table")
        self.client.force_authenticate(self.operator)
        response = self.client.post(
            f"/api/requests/{created.json()['id']}/assignments/",
            {"episode_id": "EP-9"},
        )
        self.assertEqual(response.status_code, 400)
