from pathlib import Path

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase

from desk.models import Episode
from desk.tests.helpers import make_user

SAMPLE = """episode_id,robot_id,task_name,recorded_at,duration_seconds,operator_name,quality
EP-1,arm-01,  Pick Cup ,2026-08-01T10:00:00,30,Aline,Good
EP-1,arm-01,pick cup,2026-08-01T10:00:00,30,Aline,good
EP-2,arm-99,pick cup,2026-08-01T10:00:00,30,Aline,good
EP-3,arm-01,pick cup,14/08/2026 09:15,30,Aline,bad
EP-4,arm-01,pick cup,2026-08-01T10:00:00,N/A,Aline,good
EP-5,arm-01,open drawer,2026-08-02T10:00:00,40,Eric,usable
EP-5,arm-02,open drawer,2026-08-02T10:00:00,40,Eric,usable
"""


class ImportTests(APITestCase):
    def setUp(self):
        self.operator = make_user("operator", email="ops@test.example")
        self.client.force_authenticate(self.operator)

    def _upload(self, text, name="episodes.csv"):
        uploaded = SimpleUploadedFile(name, text.encode("utf-8"), content_type="text/csv")
        return self.client.post("/api/episodes/import/", {"file": uploaded}, format="multipart")

    def test_import_is_idempotent_and_reports_skips(self):
        first = self._upload(SAMPLE)
        self.assertEqual(first.status_code, 200)
        body = first.json()
        self.assertEqual(body["imported"], 3)
        self.assertEqual(body["unchanged"], 1)
        self.assertEqual(body["conflicts"], 1)
        self.assertGreaterEqual(body["rejected"], 2)
        self.assertEqual(Episode.objects.count(), 3)
        self.assertEqual(Episode.objects.get(episode_id="EP-1").quality, "good")
        self.assertEqual(Episode.objects.get(episode_id="EP-1").task_name, "pick cup")
        self.assertEqual(Episode.objects.get(episode_id="EP-5").robot_id, "arm-01")
        self.assertFalse(Episode.objects.filter(episode_id="EP-2").exists())
        self.assertFalse(Episode.objects.filter(episode_id="EP-4").exists())

        second = self._upload(SAMPLE)
        self.assertEqual(second.status_code, 200)
        again = second.json()
        self.assertEqual(again["imported"], 0)
        self.assertEqual(Episode.objects.count(), 3)
        self.assertGreaterEqual(again["unchanged"], 3)

    def test_seed_export_imports_cleanly_twice(self):
        path = Path(settings.BASE_DIR).parent / "seed" / "episodes.csv"
        text = path.read_text(encoding="utf-8-sig")
        first = self._upload(text, name="episodes.csv")
        self.assertEqual(first.status_code, 200)
        report = first.json()
        self.assertGreater(report["imported"], 150)
        self.assertGreater(report["rejected"] + report["conflicts"], 0)
        self.assertFalse(Episode.objects.filter(robot_id="arm-99").exists())
        self.assertFalse(Episode.objects.filter(episode_id="EP-90003").exists())
        self.assertFalse(Episode.objects.filter(episode_id="EP-90004").exists())
        self.assertEqual(Episode.objects.get(episode_id="EP-00011").quality, "bad")
        original = Episode.objects.get(episode_id="EP-00003")
        self.assertEqual(original.robot_id, "humanoid-01")
        self.assertEqual(original.task_name, "fold towel")
        self.assertTrue(Episode.objects.filter(episode_id="EP-00014").exists())
        self.assertTrue(Episode.objects.filter(task_name="pick cup, then place").exists())
        count = Episode.objects.count()

        second = self._upload(text, name="episodes.csv")
        self.assertEqual(second.json()["imported"], 0)
        self.assertEqual(Episode.objects.count(), count)
