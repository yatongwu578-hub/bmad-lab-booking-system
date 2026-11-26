
"""Reviewer-owned Django client probe. Run as an explicit test label, never by discovery."""

from datetime import datetime, timedelta
from html.parser import HTMLParser
from urllib.parse import urlsplit

from django.test import Client, TestCase

from accounts.models import Role, User
from audit.models import OperationHistory
from equipment.models import Equipment
from reservations.models import Reservation
from reservations.services import BEIJING


class Page(HTMLParser):
    def __init__(self, response):
        super().__init__()
        self.links = []
        self.csrf = []
        self.feed(response.content.decode("utf-8"))

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if tag == "a" and "href" in attrs:
            self.links.append(attrs["href"])
        if tag == "input" and attrs.get("name") == "csrfmiddlewaretoken":
            self.csrf.append(attrs["value"])


class IndependentNavigationReview(TestCase):
    def link(self, response, matches):
        found = [path for path in Page(response).links if matches(path)]
        self.assertEqual(len(found), 1)
        path, = found
        parsed = urlsplit(path)
        self.assertFalse(parsed.netloc or parsed.scheme)
        return path

    def test_student_teacher_follow_rendered_links_and_submit(self):
        password = "Synthetic-review-only-a1"
        start = (datetime.now(BEIJING) + timedelta(days=2)).replace(hour=10, minute=0, second=0, microsecond=0)
        end = start + timedelta(hours=1)
        for i, role in enumerate((Role.STUDENT, Role.TEACHER)):
            with self.subTest(role=role):
                name = f"reviewed-navigation-{role}"
                user = User.objects.create_user(username=name, role=role, password=password)
                device = Equipment.objects.create(number=f"S21RV-NAV-{i}", name=f"Review Device {i}",
                                                  category="test", location="isolated")
                client = Client(enforce_csrf_checks=True)
                login = client.get("/login/")
                token, = Page(login).csrf
                identity = client.post("/login/", {"username": name, "password": password,
                                                   "csrfmiddlewaretoken": token}, follow=True)
                self.assertEqual(identity.redirect_chain, [("/identity/", 302)])
                catalog_path = self.link(identity, lambda x: x == "/equipment/")
                catalog = client.get(catalog_path)
                self.assertEqual(catalog.status_code, 200)
                detail_path = self.link(catalog, lambda x: x == f"/equipment/{device.pk}/")
                detail = client.get(detail_path)
                self.assertEqual(detail.status_code, 200)
                form_path = self.link(detail, lambda x: x == f"/equipment/{device.pk}/reserve/")
                form = client.get(form_path)
                self.assertContains(form, device.number)
                token, = Page(form).csrf
                def submit(a, b):
                    return client.post(form_path, {"start_at": a, "end_at": b, "csrfmiddlewaretoken": token})
                fmt = lambda d: d.strftime("%Y-%m-%dT%H:%M")
                rejected = submit(fmt(start)+":00+08:00", fmt(end))
                self.assertEqual(rejected.status_code, 400)
                self.assertFalse(Reservation.objects.filter(applicant=user).exists())
                confirmation = submit(fmt(start), fmt(end))
                self.assertEqual(confirmation.status_code, 201)
                row = Reservation.objects.get(applicant=user, equipment=device)
                self.assertEqual((row.start_at, row.end_at, row.status), (start, end, "pending"))
                result_path = self.link(confirmation, lambda x: x == f"/reservations/{row.pk}/result/")
                result = client.get(result_path)
                for page, code in [(confirmation,201),(result,200)]:
                    for text in [device.number, device.name, start.strftime("%Y-%m-%d %H:%M"),
                                 end.strftime("%Y-%m-%d %H:%M"), "待审核", f"<dd>{row.pk}</dd>"]:
                        self.assertContains(page, text, status_code=code)
                self.assertEqual(OperationHistory.objects.filter(reservation=row).count(), 0)
                print(f"STORY21_NAVIGATION {role} {catalog_path} {detail_path} {form_path} {result_path}")
