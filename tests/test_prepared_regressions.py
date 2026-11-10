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

