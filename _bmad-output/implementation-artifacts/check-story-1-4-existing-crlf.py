"""Separate Q-3 evidence for the applied Story 1.4, outside normal test discovery."""

import os
import re
import sys
from hashlib import sha256
from pathlib import Path


if sys.version_info[:3] != (3, 13, 17):
    raise SystemExit("The existing Python 3.13.17 venv is required.")
if os.environ.get("LAB_BOOKING_DB_MODE") != "test":
    raise SystemExit("Q-3 is limited to the isolated test mode.")
if os.environ.get("DJANGO_SETTINGS_MODULE") != "lab_booking.settings":
    raise SystemExit("Q-3 requires the guarded project settings.")

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import django

django.setup()

from django.conf import settings
from django.test import Client, TestCase
from django.urls import reverse
from django.utils.html import escape

from accounts.models import Role, User
from equipment.models import Equipment
from lab_booking.test_runner import IsolatedPostgresRunner


expected_target = ("lab_booking.postgresql", "test_lab_booking", "lab_booking_test", "127.0.0.1", "5433")
database = settings.DATABASES["default"]
if tuple(str(database[key]) for key in ("ENGINE", "NAME", "USER", "HOST", "PORT")) != expected_target:
    raise SystemExit("Unexpected Q-3 database target.")


def equipment_rows():
    return list(Equipment.objects.order_by("id").values())


class Q3Runner(IsolatedPostgresRunner):
    def setup_databases(self, **kwargs):
        return super().setup_databases(**kwargs), equipment_rows()

    def teardown_databases(self, old_config, **kwargs):
        schema, before = old_config
        try:
            if equipment_rows() != before:
                raise RuntimeError("Q-3 equipment snapshot did not return to its initial state.")
        finally:
            super().teardown_databases(schema, **kwargs)
        self.log("Q-3 cleanup: full equipment snapshot restored.")


class ExistingCRLFReview(TestCase):
    def test_other_fields_preserve_stored_crlf_bytes(self):
        actor = User.objects.create_user(username="story14-q3-admin", role=Role.ADMIN)
        text = '\r\n  first  <strong>literal & text</strong>  \r\n\r\n  last  \r\n '
        target = Equipment.objects.create(
            number="ST14-Q3-TARGET", name="Original", category="Category", location="Site", description=text,
        )
        Equipment.objects.create(number="ST14-Q3-OTHER", name="Other", category="Category", location="Site")
        baseline = equipment_rows()
        saved = next(row for row in baseline if row["id"] == target.pk)
        self.assertEqual(saved["description"].encode("utf-8"), text.encode("utf-8"))

        client = Client(enforce_csrf_checks=True)
        client.force_login(actor)
        edit_url = reverse("equipment-edit", args=[target.pk])
        detail_url = reverse("equipment-detail", args=[target.pk])
        form = client.get(edit_url)
        self.assertEqual(form.status_code, 200)
        token = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', form.content.decode(form.charset))
        self.assertIsNotNone(token)
        digest_before = sha256(saved["description"].encode("utf-8")).hexdigest()

        for kind, payload, new_name in (
            ("CRLF", text, "Edited via CRLF"),
            ("LF-equivalent", text.replace("\r\n", "\n"), "Edited via equivalent LF"),
        ):
            with self.subTest(transport=kind):
                response = client.post(edit_url, {
                    "name": new_name, "category": saved["category"], "location": saved["location"],
                    "description": payload, "csrfmiddlewaretoken": token[1],
                })
                self.assertRedirects(response, detail_url, fetch_redirect_response=False)
                data = equipment_rows()
                reloaded = next(row for row in data if row["id"] == target.pk)
                digest_after = sha256(reloaded["description"].encode("utf-8")).hexdigest()
                print(f"Q-3 transport={kind} before_sha256={digest_before} after_sha256={digest_after}", flush=True)
                self.assertEqual(reloaded["description"].encode("utf-8"), text.encode("utf-8"))
                self.assertEqual(data, [{**row, "name": new_name} if row["id"] == target.pk else row for row in baseline])
                detail = client.get(detail_url)
                self.assertEqual(detail.status_code, 200)
                description = re.search(
                    r'<dd id="equipment-description"[^>]*>(.*?)</dd>',
                    detail.content.decode(detail.charset), re.DOTALL,
                )
                self.assertIsNotNone(description)
                self.assertEqual(description[1], escape(text))
        print("Q-3 stored CRLF preserved: 2 transport variants; identity and escaped detail verified.", flush=True)


if __name__ == "__main__":
    runner = Q3Runner(verbosity=2, interactive=False, keepdb=True, parallel=1)
    sys.exit(int(bool(runner.run_tests([f"__main__.{ExistingCRLFReview.__name__}"]))))
