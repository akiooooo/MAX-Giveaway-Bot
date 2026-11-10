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

