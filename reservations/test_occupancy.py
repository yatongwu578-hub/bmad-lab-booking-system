from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from accounts.models import Role, User
from audit.models import OperationHistory
from equipment.models import Equipment, EquipmentStatus

from . import services
from .models import Reservation, ReservationStatus as Status


class EquipmentOccupancyTests(TestCase):
    day = "2026-11-26"

    @classmethod
    def setUpTestData(cls):
        cls.users = {role: User.objects.create_user(username=f"reader-{role}", role=role) for role in Role}
        cls.owner = User.objects.create_user(username="private-other-owner", role=Role.STUDENT)
        cls.dev = Equipment.objects.create(number="A", name="Equipment A", category="test", location="lab")
        cls.other = Equipment.objects.create(number="B", name="Equipment B", category="test", location="lab")

    def setUp(self):
        self.client.force_login(self.users[Role.STUDENT])
        self.url = reverse("equipment-occupancy", args=[self.dev.pk])

    @staticmethod
    def at(hour, minute=0, *, day=26):
        return datetime(2026, 11, day, hour, minute, tzinfo=services.BEIJING)

    def enter(self, start, end, status=Status.PENDING, *, dev=None):
        return Reservation.objects.create(applicant=self.owner, equipment=dev or self.dev,
                                          start_at=start, end_at=end, status=status,
                                          applied_at=start - timedelta(days=1))

    def get(self, decision, *, url=None, day=None):
        with patch.object(services, "_decision_time", return_value=decision.astimezone(UTC)) as clock:
            response = self.client.get(url or self.url, {"date": day or self.day})
        self.assertEqual(response.status_code, 200)
        clock.assert_called_once()
        self.assertIn("no-store", response.headers["Cache-Control"])
        return response

    @staticmethod
    def windows(intervals):
        return [(item.start_at, item.end_at, item.category) for item in intervals]

    def test_ac1_beijing_half_open_bounds_status_and_complement(self):
        self.enter(self.at(23, day=25), self.at(0), Status.APPROVED)
        self.enter(self.at(23, day=25), self.at(1), Status.APPROVED)
        self.enter(self.at(3), self.at(4), Status.APPROVED)
        self.enter(self.at(3, 30), self.at(5), Status.PENDING)
        self.enter(self.at(10), self.at(11), Status.APPROVED, dev=self.other)
        for status in (Status.EXPIRED, Status.CANCELLED, Status.REJECTED):
            self.enter(self.at(10), self.at(11), status)
        self.enter(self.at(23), self.at(1, day=27), Status.APPROVED)
        self.enter(self.at(0, day=27), self.at(1, day=27), Status.PENDING)
        result = self.get(self.at(22, day=25)).context["result"]
        self.assertEqual(self.windows(result.occupied), [
            (self.at(0), self.at(1), "approved_future"),
            (self.at(3), self.at(4), "approved_future"),
            (self.at(3, 30), self.at(5), "pending"),
            (self.at(23), self.at(0, day=27), "approved_future"),
        ])
        self.assertEqual(self.windows(result.unoccupied), [
            (self.at(1), self.at(3), "unoccupied"), (self.at(5), self.at(23), "unoccupied"),
        ])
        self.assertFalse(result.historical)
        self.assertFalse(OperationHistory.objects.exists())

    def test_ac1_approved_at_start_during_and_at_end(self):
        approved = self.enter(self.at(10), self.at(11), Status.APPROVED)
        for decision, category in [(self.at(9, 59), "approved_future"), (self.at(10), "in_progress"),
                                   (self.at(10, 30), "in_progress"), (self.at(10, 59), "in_progress"),
                                   (self.at(11), "historical"), (self.at(12), "historical"),
                                   (self.at(0, day=27), "historical")]:
            with self.subTest(decision=decision):
                response = self.get(decision)
                result = response.context["result"]
                intervals = result.historical if category == "historical" else result.occupied
                self.assertEqual(self.windows(intervals), [(self.at(10), self.at(11), category)])
                self.assertFalse(result.occupied if category == "historical" else result.historical)
                self.assertEqual(self.windows(result.unoccupied), [
                    (self.at(0), self.at(10), "unoccupied"), (self.at(11), self.at(0, day=27), "unoccupied"),
                ])
                if decision == self.at(10, 30):
                    self.assertContains(response, "已批准（进行中）")
                if category == "historical":
                    self.assertContains(response, "历史预约区间")
        approved.refresh_from_db()
        self.assertEqual(approved.status, Status.APPROVED)
        self.assertFalse(OperationHistory.objects.exists())

    def test_ac2_pending_at_start_and_already_ended_are_expired_once(self):
        at_start = self.enter(self.at(10), self.at(11))
        ended = self.enter(self.at(7), self.at(8))
        future = self.enter(self.at(12), self.at(13))
        excluded = [self.enter(self.at(10), self.at(11), dev=self.other),
                    self.enter(self.at(7, day=25), self.at(8, day=25))]
        response = self.get(self.at(10))
        self.assertEqual(self.windows(response.context["result"].occupied), [(self.at(12), self.at(13), "pending")])
        self.get(self.at(10, 30))
        self.assertEqual(list(OperationHistory.objects.order_by("reservation_id").values_list(
            "reservation_id", "action", "actor_type", "actor_id", "before_status", "after_status", "decision_at",
        )), [(row.pk, "expire", "system", None, Status.PENDING, Status.EXPIRED, self.at(10))
             for row in (at_start, ended)])
        for row in (at_start, ended, future, *excluded):
            row.refresh_from_db()
            self.assertEqual(row.status, Status.EXPIRED if row in (at_start, ended) else Status.PENDING)
        isolated_device = Equipment.objects.create(number="C", name="Equipment C", category="test", location="lab")
        isolated = self.enter(self.at(10), self.at(11), dev=isolated_device)
        result = self.get(self.at(10, 30), url=reverse("equipment-occupancy", args=[isolated_device.pk])).context["result"]
        self.assertFalse(result.occupied)
        isolated.refresh_from_db()
        self.assertEqual(isolated.status, Status.EXPIRED)
        self.assertTrue(OperationHistory.objects.filter(reservation=isolated, decision_at=self.at(10, 30)).exists())

    def test_ac3_lock_recheck_rereads_clock_and_writes_in_order(self):
        self.enter(self.at(10), self.at(11))
        self.enter(self.at(12), self.at(13))
        with CaptureQueriesContext(connection) as evidence:
            response = self.client.get(self.url, {"date": self.day})
        self.assertEqual(response.status_code, 200)
        sql = [v["sql"] for v in evidence]
        candidates = [i for i, s in enumerate(sql) if 'FROM "reservations_reservation"' in s]
        locks = [i for i, s in enumerate(sql) if "FOR UPDATE" in s]
        clocks = [i for i, s in enumerate(sql) if "clock_timestamp() AS decision_at" in s]
        self.assertEqual(len(locks), 1)
        self.assertEqual(len(clocks), 1)
        self.assertLess(candidates[0], locks[0])
        self.assertLess(locks[0], candidates[1])
        self.assertLess(candidates[1], clocks[0])
        self.assertIn('"reservations_reservation"."id" IN (', sql[candidates[1]])
        self.assertIn('"equipment_equipment"', sql[locks[0]])
        between = sql[locks[0] + 1:clocks[0]]
        self.assertTrue(any('"accounts_user"."is_active"' in s and 'FROM "accounts_user"' in s for s in between))
        self.assertTrue(any('"equipment_equipment"."status"' in s for s in between))

    def test_ac3_no_pending_and_no_candidates_do_not_lock(self):
        for has_approved in (False, True):
            with self.subTest(has_approved=has_approved):
                if has_approved:
                    self.enter(self.at(10), self.at(11), Status.APPROVED)
                with patch.object(services, "lock_equipment") as lock, CaptureQueriesContext(connection) as evidence:
                    response = self.client.get(self.url, {"date": self.day})
                self.assertEqual(response.status_code, 200)
                lock.assert_not_called()
                self.assertEqual(sum("clock_timestamp() AS decision_at" in v["sql"] for v in evidence), 1)
        self.assertFalse(OperationHistory.objects.exists())

    def test_ac4_new_row_after_freeze_is_not_visible_until_next_query(self):
        original = self.enter(self.at(10), self.at(11))
        added = []
        real_lock = services.lock_equipment

        def add_before_lock(pk):
            added.append(self.enter(self.at(12), self.at(13)))
            return real_lock(pk)

        with patch.object(services, "lock_equipment", side_effect=add_before_lock):
            first = self.get(self.at(9)).context["result"]
        second = self.get(self.at(9)).context["result"]
        self.assertEqual(self.windows(first.occupied), [(original.start_at, original.end_at, "pending")])
        self.assertEqual(self.windows(second.occupied), [
            (original.start_at, original.end_at, "pending"), (added[0].start_at, added[0].end_at, "pending"),
        ])

    def test_ac5_three_roles_use_detail_entry_and_only_see_interval_projection(self):
        row = self.enter(self.at(10), self.at(11), Status.APPROVED)
        for role, user in self.users.items():
            with self.subTest(role=role):
                self.client.force_login(user)
                detail = self.client.get(reverse("equipment-detail", args=[self.dev.pk]))
                self.assertContains(detail, f'action="{self.url}"')
                self.assertContains(detail, '<label for="id_date">查询日期（北京时间）:</label>', html=True)
                self.assertContains(detail, reverse("equipment-catalog"))
                nav = "equipment-edit" if role == Role.ADMIN else "reservation-submit"
                self.assertContains(detail, reverse(nav, args=[self.dev.pk]))
                response = self.get(self.at(9))
                self.assertNotContains(response, self.owner.username)
                self.assertNotContains(response, reverse("reservation-result", args=[row.pk]))
                self.assertEqual(set(asdict(response.context["result"].occupied[0])),
                                 {"start_at", "end_at", "category"})

    def test_ac5_anonymous_and_inactive_sessions_do_not_scan_or_change_reservations(self):
        old = self.enter(self.at(7), self.at(8))
        self.client.logout()
        for inactive_session in (False, True):
            if inactive_session:
                user = self.users[Role.STUDENT]
                self.client.force_login(user)
                User.objects.filter(pk=user.pk).update(is_active=False)
            with CaptureQueriesContext(connection) as evidence:
                response = self.client.get(self.url, {"date": self.day})
            self.assertEqual(response.status_code, 302)
            self.assertTrue(response.headers["Location"].startswith(reverse("login")))
            self.assertFalse(any('"reservations_reservation"' in q["sql"] for q in evidence))
        old.refresh_from_db()
        self.assertEqual(old.status, Status.PENDING)
        self.assertFalse(OperationHistory.objects.exists())

    def test_ac6_invalid_dates_missing_device_and_post_do_not_run_business_queries(self):
        inputs = ({}, {"date": "2026-11-6"}, {"date": "2026-02-29"}, {"date": " 2026-11-26"},
                  {"date": "2026-11-26T00:00"}, {"date": "２０２６-11-26"}, {"date": "9999-12-31"},
                  {"date": "0001-01-01"})
        with CaptureQueriesContext(connection) as evidence:
            for params in inputs:
                self.assertEqual(self.client.get(self.url, params).status_code, 400)
            missing_url = reverse("equipment-occupancy", args=[self.other.pk + 999])
            self.assertEqual(self.client.get(missing_url, {"date": self.day}).status_code, 404)
            self.assertEqual(self.client.post(self.url, {"date": self.day}).status_code, 405)
        self.assertFalse(any(pattern in q["sql"] for q in evidence for pattern in
                             ('"reservations_reservation"', "FOR UPDATE", "clock_timestamp()", "INSERT", "UPDATE")))

    def test_ac7_empty_and_past_do_not_imply_reservable_and_submit_rechecks(self):
        for status in EquipmentStatus:
            Equipment.objects.filter(pk=self.dev.pk).update(status=status)
            response = self.get(self.at(10, day=27))
            self.assertContains(response, f"设备当前状态：{status.label}")
            self.assertContains(response, "该日期无有效预约占用。")
            self.assertContains(response, "无占用不等于可预约")
        Equipment.objects.filter(pk=self.dev.pk).update(status=EquipmentStatus.AVAILABLE)
        self.get(self.at(9))
        reserve = reverse("reservation-submit", args=[self.dev.pk])
        post = {"start_at": self.day + "T10:00", "end_at": self.day + "T11:00"}
        with patch.object(services, "_decision_time", return_value=self.at(9).astimezone(UTC)):
            self.client.force_login(self.users[Role.TEACHER])
            self.assertEqual(self.client.post(reserve, post).status_code, 201)
            self.client.force_login(self.users[Role.STUDENT])
            self.assertEqual(self.client.post(reserve, post).status_code, 409)
        self.assertEqual(list(Reservation.objects.values_list("applicant_id", "status")),
                         [(self.users[Role.TEACHER].pk, Status.PENDING)])

    def test_ac8_later_history_failure_rolls_back_every_transition(self):
        rows = [self.enter(self.at(7), self.at(8)), self.enter(self.at(9), self.at(10))]
        append_expiry = services.append_reservation_expiry

        def fail_second(pk, decision):
            if pk == rows[1].pk:
                raise services.ReservationFailed
            append_expiry(pk, decision)

        with patch.object(services, "append_reservation_expiry", side_effect=fail_second), patch.object(
            services, "_decision_time", return_value=self.at(11).astimezone(UTC)
        ):
            response = self.client.get(self.url, {"date": self.day})
        self.assertContains(response, "本次占用查询未成功", status_code=503)
        self.assertNotContains(response, "被有效预约占用", status_code=503)
        self.assertEqual(list(Reservation.objects.order_by("pk").values_list("status", flat=True)),
                         [Status.PENDING, Status.PENDING])
        self.assertFalse(OperationHistory.objects.exists())

    def test_ac8_unknown_does_not_render_success_or_claim_rollback(self):
        with patch("reservations.views.get_daily_occupancy", side_effect=services.ReservationUnknown):
            response = self.client.get(self.url, {"date": self.day})
        self.assertContains(response, "待核查", status_code=503)
        self.assertNotContains(response, "已回滚", status_code=503)
        self.assertNotContains(response, "被有效预约占用", status_code=503)
