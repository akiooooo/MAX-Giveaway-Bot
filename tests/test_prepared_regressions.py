import json
import os
import random
import sqlite3
import tempfile
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch
from zoneinfo import ZoneInfo

import requests
from promo_bot.app import PromoBot
from promo_bot.config import Settings, load_env
from promo_bot.database import Database
from promo_bot.max_api import MaxApiError, MaxClient


class PreparedRegressionTests(unittest.TestCase):
    def setUp(self):
        self.db = Database(":memory:")
        self.now = datetime(2026, 11, 1, 12, tzinfo=ZoneInfo("Europe/Moscow"))
        self.partner_data = {"slug": "shop", "name": "Магазин", "campaign_day": "2026-11-01",
            "channel_id": -1001, "channel_url": "https://max.ru/shop", "promo_place": "на сайте",
            "promo_expires_on": "2026-11-30", "daily_prize": "мерч", "prize_instructions": "Ответить боту",
            "winner_count": 1, "claim_hours": 24}
        self.partner = self.db.add_partner(self.partner_data)
        self.client = MaxClient("test-token", "https://example.test/")

    def tearDown(self):
        self.client.session.close()
        self.db.close()

    def user(self, uid=1, **extra):
        return self.db.upsert_user({"user_id": uid, "first_name": "Иван", **extra}, self.now)

    def rows(self, sql, values=()):
        with self.db.transaction() as conn:
            return [dict(row) for row in conn.execute(sql, values)]

    def draw(self, count=3, approve=False):
        for uid in range(1, count+1):
            self.user(uid)
            self.db.register_participation(uid, self.partner, self.now)
        draw = self.db.create_daily_draw(self.now.date(), self.now, random.Random(17))
        if approve:
            self.db.approve_draw(draw, self.now, "билеты")
        return draw

    def claim(self):
        draw = self.draw(1, approve=True)
        return draw, 1

    def test_001(self):
        self.assertEqual(self.now.utcoffset(), timedelta(hours=3))

    def test_002(self):
        self.assertTrue(self.user())
        self.assertFalse(self.user())
        self.assertEqual(len(self.rows("SELECT * FROM users")), 1)

    def test_003(self):
        self.user(username="before")
        self.user(username="after")
        self.assertEqual(self.rows("SELECT * FROM users")[0]["username"], "after")

    def test_004(self):
        self.user()
        self.db.upsert_user({"user_id": 1}, self.now + timedelta(days=1))
        row = self.rows("SELECT * FROM users")[0]
        self.assertEqual(row["created_at"], self.now.isoformat())
        self.assertEqual(row["last_seen_at"], (self.now + timedelta(days=1)).isoformat())

    def test_005(self):
        self.user(first_name="Алёна", last_name="О'Коннор")
        row = self.rows("SELECT * FROM users")[0]
        self.assertEqual((row["first_name"], row["last_name"]), ("Алёна", "О'Коннор"))

    def test_006(self):
        self.user(1, username="first")
        self.user(2, username="second")
        self.assertEqual([u["username"] for u in self.rows("SELECT * FROM users ORDER BY user_id")], ["first", "second"])

    def test_007(self):
        self.user(2**40)
        self.assertEqual(self.rows("SELECT user_id FROM users")[0]["user_id"], 2**40)

    def test_008(self):
        self.user()
        self.db.upsert_user({"user_id": 2}, self.now - timedelta(days=1))
        self.assertEqual(self.db.get_stats(self.now.date())["new_users"], 1)

    def test_009(self):
        self.user(1)
        self.user(2)
        self.user(1)
        self.assertEqual(self.db.get_stats(self.now.date())["total_users"], 2)

    def test_010(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"nested"/"bot.db"
            db = Database(str(path))
            db.upsert_user({"user_id": 8}, self.now)
            self.assertTrue(path.is_file())
            db.close()

    def test_011(self):
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory)/"bot.db")
            first = Database(path)
            first.upsert_user({"user_id": 8}, self.now)
            first.close()
            second = Database(path)
            self.assertEqual(second.get_stats(self.now.date())["total_users"], 1)
            second.close()

    def test_012(self):
        with self.assertRaises(RuntimeError):
            with self.db.transaction() as conn:
                conn.execute("UPDATE partners SET name='Ошибка'")
                raise RuntimeError("rollback")
        self.assertEqual(self.db.get_partner_for_day(self.now.date())["name"], "Магазин")

    def test_013(self):
        self.assertEqual(self.db.get_partner_for_day(self.now.date())["slug"], "shop")

    def test_014(self):
        self.assertIsNone(self.db.get_partner_for_day(date(2026, 11, 2)))

    def test_015(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.add_partner({**self.partner_data, "slug": "another"})

    def test_016(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.add_partner({**self.partner_data, "campaign_day": "2026-11-02"})

    def test_017(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.add_partner({**self.partner_data, "slug": "new", "campaign_day": "2026-11-02", "winner_count": 0})

    def test_018(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.add_partner({**self.partner_data, "slug": "new", "campaign_day": "2026-11-02", "claim_hours": 0})

    def test_019(self):
        data = {**self.partner_data, "slug": "new", "campaign_day": "2026-11-02"}
        del data["claim_hours"]
        self.db.add_partner(data)
        self.assertEqual(self.db.get_partner_for_day(date(2026, 11, 2))["claim_hours"], 24)

    def test_020(self):
        self.db.add_partner({**self.partner_data, "slug": "early", "campaign_day": "2026-10-31"})
        self.assertEqual([p["slug"] for p in self.db.get_stats(self.now.date())["partners"]], ["early", "shop"])

    def test_021(self):
        with self.assertRaisesRegex(ValueError, "unknown partner"):
            self.db.add_promo_codes("missing", ["A"])

    def test_022(self):
        self.db.add_promo_codes("shop", ["  CODE-1  "])
        self.assertEqual(self.rows("SELECT code FROM promo_codes")[0]["code"], "CODE-1")

    def test_023(self):
        self.assertEqual(self.db.add_promo_codes("shop", ["", " ", "\t"]), 0)

    def test_024(self):
        self.assertEqual(self.db.add_promo_codes("shop", ["A", "A"]), 1)
        self.assertEqual(self.db.add_promo_codes("shop", ["A", "B"]), 1)

    def test_025(self):
        self.db.add_partner({**self.partner_data, "slug": "other", "campaign_day": "2026-11-02"})
        self.assertEqual(self.db.add_promo_codes("shop", ["A"]), 1)
        self.assertEqual(self.db.add_promo_codes("other", ["A"]), 1)

    def test_026(self):
        self.user(1)
        self.user(2)
        self.db.add_promo_codes("shop", ["FIRST", "SECOND"])
        self.assertEqual(self.db.request_promo(1, self.partner, self.now).code, "FIRST")
        self.assertEqual(self.db.request_promo(2, self.partner, self.now).code, "SECOND")

    def test_027(self):
        self.user(1)
        self.user(2)
        self.db.add_promo_codes("shop", ["ONLY"])
        self.db.request_promo(1, self.partner, self.now)
        result = self.db.request_promo(2, self.partner, self.now)
        self.assertEqual((result.status, result.code), ("exhausted", None))

    def test_028(self):
        self.user()
        self.db.add_promo_codes("shop", ["A", "B"])
        self.db.request_promo(1, self.partner, self.now)
        result = self.db.request_promo(1, self.partner, self.now)
        self.assertEqual((result.status, result.code), ("existing", "A"))

    def test_029(self):
        self.user()
        self.db.add_promo_codes("shop", ["A", "B"])
        for _ in range(3):
            self.db.request_promo(1, self.partner, self.now)
        self.assertEqual(self.db.get_stats(self.now.date())["promos_issued"], 1)

    def test_030(self):
        self.user()
        for _ in range(3):
            self.db.request_promo(1, self.partner, self.now)
        self.assertEqual(self.db.get_stats(self.now.date())["promo_requests"], 3)

    def test_031(self):
        self.user()
        self.db.request_promo(1, self.partner, self.now)
        self.assertEqual(self.db.get_user_progress(1, 10)["chances"], 0)

    def test_032(self):
        self.user()
        with self.assertRaises(ValueError):
            self.db.request_promo(1, 9999, self.now)
        self.assertEqual(self.rows("SELECT * FROM promo_requests"), [])

    def test_033(self):
        self.db.add_promo_codes("shop", ["A"])
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.request_promo(999, self.partner, self.now)
        self.assertIsNone(self.rows("SELECT * FROM promo_codes")[0]["assigned_user_id"])

    def test_034(self):
        self.db.add_promo_codes("shop", ["A", "B", "C"])
        for uid in (1, 2):
            self.user(uid)
            self.db.register_participation(uid, self.partner, self.now)
        partner = self.db.get_stats(self.now.date())["partners"][0]
        self.assertEqual((partner["promos_left"], partner["participants"]), (3, 2))

    def test_035(self):
        self.user()
        self.db.add_promo_codes("shop", ["A"])
        self.db.request_promo(1, self.partner, self.now)
        self.assertEqual(self.rows("SELECT * FROM promo_codes")[0]["assigned_at"], self.now.isoformat())

    def test_036(self):
        self.user()
        self.assertTrue(self.db.register_participation(1, self.partner, self.now))
        self.assertFalse(self.db.register_participation(1, self.partner, self.now))

    def test_037(self):
        self.user()
        self.db.register_participation(1, self.partner, self.now)
        self.assertTrue(self.db.is_participant(1, self.partner))
        self.assertFalse(self.db.is_participant(1, 999))

    def test_038(self):
        self.user()
        self.db.add_promo_codes("shop", ["A"])
        self.db.request_promo(1, self.partner, self.now)
        self.db.register_participation(1, self.partner, self.now)
        self.assertEqual(self.db.get_user_progress(1, 10)["chances"], 1)

    def test_039(self):
        self.user()
        self.db.add_promo_codes("shop", ["A"])
        self.db.request_promo(1, self.partner, self.now)
        self.db.register_participation(1, self.partner, self.now)
        self.assertEqual(self.db.get_user_progress(1, 10)["partners"], ["Магазин"])

    def test_040(self):
        self.user()
        self.assertEqual(self.db.get_user_progress(1, 10), {"chances": 0, "days": [], "partners": [], "remaining": 10})

    def test_041(self):
        self.user()
        with self.db.transaction() as conn:
            conn.executemany("INSERT INTO activity_days VALUES(?,?,?,'promo',?)", [(1, f"2026-10-{d:02}", self.partner, self.now.isoformat()) for d in range(1, 15)])
        progress = self.db.get_user_progress(1, 10)
        self.assertEqual((progress["chances"], len(progress["days"]), progress["remaining"]), (10, 10, 0))

    def test_042(self):
        self.user(1)
        self.user(2)
        self.db.register_participation(1, self.partner, self.now)
        self.assertEqual(self.db.get_user_progress(2, 10)["chances"], 0)

    def test_043(self):
        self.user()
        with self.db.transaction() as conn:
            for day in ("2026-10-03", "2026-10-01", "2026-10-02"):
                conn.execute("INSERT INTO activity_days VALUES(?,?,?,'promo',?)", (1, day, self.partner, self.now.isoformat()))
        self.assertEqual(self.db.get_user_progress(1, 10)["days"], ["2026-10-01", "2026-10-02", "2026-10-03"])

    def test_044(self):
        self.user()
        self.db.add_promo_codes("shop", ["A"])
        self.db.request_promo(1, self.partner, self.now)
        self.assertFalse(self.db.is_participant(1, self.partner))

    def test_045(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.register_participation(999, self.partner, self.now)

    def test_046(self):
        draw = self.db.get_draw(self.draw(0))
        self.assertEqual((draw["participant_count"], draw["winner_count"], draw["entries"]), (0, 0, []))

    def test_047(self):
        with self.db.transaction() as conn:
            conn.execute("UPDATE partners SET winner_count=5")
        draw = self.db.get_draw(self.draw(2))
        self.assertEqual((draw["winner_count"], draw["reserve_count"]), (2, 0))

    def test_048(self):
        draw = self.db.get_draw(self.draw(5))
        chosen = [e["user_id"] for e in draw["entries"] if e["role"] in ("winner", "reserve")]
        self.assertEqual(len(chosen), len(set(chosen)))

    def test_049(self):
        self.draw()
        self.assertEqual(self.db.get_queued_notifications(), [])
        self.assertEqual(self.rows("SELECT * FROM claims"), [])

    def test_050(self):
        self.draw()
        with self.assertRaises(ValueError):
            self.db.create_daily_draw(self.now.date(), self.now, random.Random(1))

    def test_051(self):
        with self.assertRaises(ValueError):
            self.db.create_daily_draw(date(2026, 12, 1), self.now, random.Random(1))

    def test_052(self):
        draw = self.draw(approve=True)
        self.assertEqual(self.db.approve_draw(draw, self.now, "билеты"), 0)
        self.assertEqual(len(self.db.get_queued_notifications()), 1)

    def test_053(self):
        with self.assertRaises(ValueError):
            self.db.approve_draw(999, self.now, "билеты")

    def test_054(self):
        self.assertIsNone(self.db.get_draw(999))

    def test_055(self):
        draw = self.draw(approve=True)
        self.assertEqual(self.db.get_draw(draw)["status"], "approved")

    def test_056(self):
        draw = self.db.create_final_draw(self.now.date(), self.now, 5, 5, 10, random.Random(1))
        self.assertEqual(self.db.get_draw(draw)["entries"], [])

    def test_057(self):
        self.db.create_final_draw(self.now.date(), self.now, 5, 5, 10, random.Random(1))
        with self.assertRaises(ValueError):
            self.db.create_final_draw(self.now.date(), self.now, 5, 5, 10, random.Random(1))

    def test_058(self):
        self.user()
        self.db.add_promo_codes("shop", ["A"])
        self.db.request_promo(1, self.partner, self.now)
        draw = self.db.create_final_draw(self.now.date(), self.now, 1, 0, 10, random.Random(1))
        self.assertEqual(self.db.get_draw(draw)["entries"][0]["user_id"], 1)

    def test_059(self):
        draw = self.db.get_draw(self.draw(5))
        self.assertEqual(len(draw["entries"]), 5)
        self.assertEqual(draw["participant_count"], 5)

    def test_060(self):
        selected = self.db._weighted_unique([(1, 1), (2, 5)], 20, random.Random(3))
        self.assertEqual(set(selected), {1, 2})
        self.assertEqual(len(selected), 2)

    def test_061(self):
        draw, _ = self.claim()
        self.user(2)
        with self.assertRaises(ValueError):
            self.db.save_claim_name(draw, 2, "Иван", "Петров", self.now)

    def test_062(self):
        draw, uid = self.claim()
        with self.assertRaises(ValueError):
            self.db.save_claim_name(draw, uid, "Иван", "Петров", self.now + timedelta(hours=25))

    def test_063(self):
        draw, uid = self.claim()
        with self.assertRaises(ValueError):
            self.db.submit_consent(draw, uid, True, self.now)

    def test_064(self):
        draw, uid = self.claim()
        self.db.save_claim_name(draw, uid, "Иван", "Петров", self.now)
        self.db.submit_consent(draw, uid, False, self.now)
        claim = self.rows("SELECT * FROM claims")[0]
        self.assertEqual((claim["status"], claim["consent"]), ("declined", 0))

    def test_065(self):
        draw, uid = self.claim()
        self.db.set_user_state(uid, "claim_name", {"draw_id": draw}, self.now)
        self.db.save_claim_name(draw, uid, "Иван", "Петров", self.now)
        self.db.submit_consent(draw, uid, True, self.now)
        self.assertIsNone(self.db.get_user_state(uid))

    def test_066(self):
        draw, uid = self.claim()
        self.db.save_claim_name(draw, uid, "Иван", "Петров", self.now)
        with self.assertRaisesRegex(ValueError, "deadline"):
            self.db.submit_consent(draw, uid, True, self.now + timedelta(hours=25))
        self.assertEqual(self.rows("SELECT status FROM claims")[0]["status"], "waiting")

    def test_067(self):
        draw, uid = self.claim()
        self.db.save_claim_name(draw, uid, "Иван", "Петров", self.now)
        self.db.submit_consent(draw, uid, True, self.now)
        with self.assertRaises(ValueError):
            self.db.submit_consent(draw, uid, True, self.now)

    def test_068(self):
        self.draw(approve=True)
        self.assertEqual(self.db.expire_claims(self.now + timedelta(hours=23), "билеты"), 0)

    def test_069(self):
        draw = self.draw(approve=True)
        uid = self.rows("SELECT user_id FROM claims")[0]["user_id"]
        self.db.save_claim_name(draw, uid, "Иван", "Петров", self.now)
        self.db.submit_consent(draw, uid, True, self.now)
        self.assertEqual(self.db.expire_claims(self.now + timedelta(hours=25), "билеты"), 0)

    def test_070(self):
        self.draw(approve=True)
        later = self.now + timedelta(hours=25)
        self.assertEqual(self.db.expire_claims(later, "билеты"), 1)
        self.assertEqual(self.db.expire_claims(later, "билеты"), 0)

    def test_071(self):
        self.user(1)
        self.user(2)
        self.assertEqual(self.db.queue_push("Новость", self.now), 2)
        self.assertEqual(len(self.db.get_queued_notifications()), 2)

    def test_072(self):
        self.user(1)
        self.user(2)
        self.assertEqual(self.db.queue_push("Лично", self.now, 2), 1)
        self.assertEqual(self.db.get_queued_notifications()[0]["user_id"], 2)

    def test_073(self):
        self.assertEqual(self.db.queue_push("Лично", self.now, 999), 0)

    def test_074(self):
        self.user()
        for _ in range(3):
            self.db.queue_push("Новость", self.now)
        self.assertEqual(len(self.db.get_queued_notifications(limit=2)), 2)

    def test_075(self):
        self.user()
        self.db.queue_push("Новость", self.now)
        notification = self.db.get_queued_notifications()[0]
        self.db.mark_notification(notification["id"], True, self.now)
        self.assertEqual(self.db.get_queued_notifications(), [])
        self.assertEqual(self.rows("SELECT * FROM notifications")[0]["sent_at"], self.now.isoformat())

    def test_076(self):
        self.user()
        self.db.queue_push("Новость", self.now)
        self.db.mark_notification(1, False, self.now, "network down")
        row = self.rows("SELECT * FROM notifications")[0]
        self.assertEqual((row["status"], row["sent_at"], row["error"]), ("failed", None, "network down"))

    def test_077(self):
        self.user()
        self.db.queue_push("Новость", self.now)
        self.db.mark_notification(1, False, self.now, "x"*1000)
        self.assertEqual(len(self.rows("SELECT error FROM notifications")[0]["error"]), 500)

    def test_078(self):
        self.user()
        self.db.queue_push("Первая", self.now)
        self.db.queue_push("Вторая", self.now)
        self.assertEqual([n["text"] for n in self.db.get_queued_notifications()], ["Первая", "Вторая"])

    def test_079(self):
        self.user()
        self.db.set_user_state(1, "claim_name", {"имя": "Алёна", "draw_id": 5}, self.now)
        self.assertEqual(self.db.get_user_state(1)["payload"], {"имя": "Алёна", "draw_id": 5})

    def test_080(self):
        self.user()
        self.db.set_user_state(1, "first", {}, self.now)
        self.db.set_user_state(1, "second", {"step": 2}, self.now)
        self.assertEqual(self.db.get_user_state(1)["state"], "second")
        self.assertEqual(len(self.rows("SELECT * FROM user_states")), 1)

    def test_081(self):
        self.assertEqual(self.client.base_url, "https://example.test")

    def test_082(self):
        self.assertEqual(self.client.session.headers["Authorization"], "test-token")
        self.assertNotIn("test-token", self.client.base_url)

    def test_083(self):
        with patch.object(self.client, "_request", return_value={}) as call:
            self.client.get_updates(0)
        self.assertEqual(call.call_args.kwargs["params"]["marker"], 0)

    def test_084(self):
        with patch.object(self.client, "_request", return_value={}) as call:
            self.client.get_updates(None)
        self.assertNotIn("marker", call.call_args.kwargs["params"])

    def test_085(self):
        with patch.object(self.client, "_request", return_value={}) as call:
            self.client.get_updates(12, timeout=15)
        self.assertEqual(call.call_args.kwargs["params"]["timeout"], 15)

    def test_086(self):
        with patch.object(self.client, "_request", return_value={"members": [{"user_id": "7"}, {"user_id": 8}]}):
            self.assertTrue(self.client.is_channel_member(-1001, 7))
            self.assertFalse(self.client.is_channel_member(-1001, 9))

    def test_087(self):
        with patch.object(self.client, "_request", return_value={}):
            self.assertFalse(self.client.is_channel_member(-1001, 7))

    def test_088(self):
        with patch.object(self.client, "_request", return_value={}) as call:
            self.client.send_message(7, "Текст", notify=False)
        self.assertFalse(call.call_args.kwargs["json"]["notify"])

    def test_089(self):
        with patch.object(self.client, "_request", return_value={}) as call:
            self.client.send_message(7, "Текст")
        self.assertNotIn("attachments", call.call_args.kwargs["json"])

    def test_090(self):
        buttons = [[{"type": "callback", "text": "Меню", "payload": "menu:how"}]]
        with patch.object(self.client, "_request", return_value={}) as call:
            self.client.send_message(7, "Привет", buttons, image_token="banner")
        attachments = call.call_args.kwargs["json"]["attachments"]
        self.assertEqual([a["type"] for a in attachments], ["image", "inline_keyboard"])

    def test_091(self):
        buttons = [[{"type": "callback", "text": "Меню", "payload": "menu:how"}]]
        with patch.object(self.client, "_request", return_value={}) as call:
            self.client.answer_callback("callback-1", "Ответ", buttons)
        self.assertEqual(call.call_args.kwargs["json"]["message"]["attachments"][0]["payload"]["buttons"], buttons)

    def test_092(self):
        response = Mock(ok=False, status_code=503, text="Unavailable")
        with patch.object(self.client.session, "request", return_value=response):
            with self.assertRaisesRegex(MaxApiError, "503"):
                self.client.get_updates(None)

    def test_093(self):
        with patch.object(self.client.session, "request", side_effect=requests.Timeout):
            with self.assertRaises(requests.Timeout):
                self.client.get_updates(None)

    def test_094(self):
        response = Mock(ok=True)
        response.json.side_effect = ValueError("bad JSON")
        with patch.object(self.client.session, "request", return_value=response):
            with self.assertRaises(ValueError):
                self.client.get_updates(None)

    def test_095(self):
        response = Mock(ok=False, status_code=500, text="x"*10000)
        with patch.object(self.client.session, "request", return_value=response):
            with self.assertRaises(MaxApiError) as error:
                self.client.get_updates(None)
        self.assertLess(len(str(error.exception)), 350)

