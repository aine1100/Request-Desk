from django.core.management import call_command
from rest_framework.test import APITestCase

from desk.models import User
from desk.tests.helpers import make_user


class AuthorizationTests(APITestCase):
    def test_health_is_public(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_anonymous_cannot_list_requests(self):
        response = self.client.get("/api/requests/")
        self.assertEqual(response.status_code, 401)

    def test_login_and_me(self):
        make_user("client", email="client@test.example", name="Acme")
        response = self.client.post(
            "/api/auth/login/",
            {"email": "client@test.example", "password": "password123"},
        )
        self.assertEqual(response.status_code, 200)
        token = response.json()["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        me = self.client.get("/api/auth/me/")
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.json()["role"], "client")

    def test_inactive_user_cannot_log_in(self):
        user = make_user("operator", email="ops@test.example")
        user.is_active = False
        user.save(update_fields=["is_active"])
        response = self.client.post(
            "/api/auth/login/",
            {"email": "ops@test.example", "password": "password123"},
        )
        self.assertEqual(response.status_code, 401)

    def test_client_sees_only_their_requests(self):
        client_a = make_user("client", email="a@test.example")
        client_b = make_user("client", email="b@test.example")
        self.client.force_authenticate(client_a)
        created = self.client.post(
            "/api/requests/",
            {
                "task_name": "Pick Cup",
                "episodes_requested": 2,
                "deadline": "2026-10-20",
                "notes": "morning light",
            },
        )
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.json()["task_name"], "pick cup")
        request_id = created.json()["id"]

        self.client.force_authenticate(client_b)
        listing = self.client.get("/api/requests/")
        self.assertEqual(listing.json()["results"], [])
        detail = self.client.get(f"/api/requests/{request_id}/")
        self.assertEqual(detail.status_code, 404)

    def test_client_cannot_import_or_assign_or_start_work(self):
        client = make_user("client", email="a@test.example")
        self.client.force_authenticate(client)
        created = self.client.post(
            "/api/requests/",
            {"task_name": "pick cup", "episodes_requested": 1, "deadline": "2026-10-20"},
        )
        request_id = created.json()["id"]
        start = self.client.post(
            f"/api/requests/{request_id}/transition/",
            {"to_status": "in_progress"},
        )
        self.assertEqual(start.status_code, 403)
        assign = self.client.post(
            f"/api/requests/{request_id}/assignments/",
            {"episode_id": "EP-1"},
        )
        self.assertEqual(assign.status_code, 403)
        imported = self.client.post("/api/episodes/import/", {})
        self.assertEqual(imported.status_code, 403)
        analytics = self.client.get("/api/analytics/?start=2026-08-01&end=2026-08-02")
        self.assertEqual(analytics.status_code, 403)

    def test_operator_cannot_create_requests_or_manage_users(self):
        operator = make_user("operator")
        self.client.force_authenticate(operator)
        users = self.client.get("/api/users/")
        self.assertEqual(users.status_code, 403)
        created = self.client.post(
            "/api/requests/",
            {"task_name": "pick cup", "episodes_requested": 1, "deadline": "2026-10-20"},
        )
        self.assertEqual(created.status_code, 403)

    def test_seed_users_store_hashed_passwords(self):
        call_command("seed_users")
        call_command("seed_users")
        admin = User.objects.get(email="admin@example.com")
        self.assertTrue(admin.check_password("admin123"))
        self.assertNotEqual(admin.password, "admin123")
        self.assertFalse(admin.password.startswith("admin123"))
        self.assertEqual(User.objects.filter(email="ops1@example.com").count(), 1)
        self.assertEqual(User.objects.count(), 5)
