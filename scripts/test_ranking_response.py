#!/usr/bin/env python3
"""ranking_response の単体テスト。"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ranking_response import (  # noqa: E402
    NOT_OBJECT_ERROR,
    RankingResponseError,
    coerce_ranking_payload,
    fetch_ranking_with_retries,
    parse_ranking_json_text,
    sync_markets_independently,
)


class CoerceTests(unittest.TestCase):
    def test_accepts_array_as_ranking20(self) -> None:
        items = [{"rank": 1, "ticker": "MSFT"}, {"rank": 2, "ticker": "AAPL"}]
        out = coerce_ranking_payload(items, market="us")
        self.assertEqual(out["ranking20"], items)
        self.assertEqual(out["market"], "us")

    def test_accepts_object(self) -> None:
        data = {"market": "jp", "ranking20": [{"rank": 1, "ticker": "7203"}]}
        out = coerce_ranking_payload(data)
        self.assertEqual(out["ranking20"][0]["ticker"], "7203")

    def test_rejects_non_object_non_array(self) -> None:
        with self.assertRaises(RankingResponseError) as ctx:
            coerce_ranking_payload("not-json-structure")
        self.assertEqual(str(ctx.exception), NOT_OBJECT_ERROR)

    def test_parse_fenced_array(self) -> None:
        text = '```json\n[{"rank": 1, "ticker": "PG"}]\n```'
        out = parse_ranking_json_text(text, market="us")
        self.assertEqual(out["ranking20"][0]["ticker"], "PG")


class RetryTests(unittest.TestCase):
    def test_retries_then_accepts_array(self) -> None:
        calls = {"n": 0}

        def fetch_once() -> object:
            calls["n"] += 1
            if calls["n"] < 3:
                return 123  # 非オブジェクト → リトライ
            return [{"rank": 1, "ticker": "V"}]

        out = fetch_ranking_with_retries(fetch_once, market="us", retries=2)
        self.assertEqual(calls["n"], 3)
        self.assertEqual(out["ranking20"][0]["ticker"], "V")

    def test_exhausted_retries_raise(self) -> None:
        def fetch_once() -> object:
            return 123

        with self.assertRaises(RankingResponseError):
            fetch_ranking_with_retries(fetch_once, retries=2)


class PartialSyncTests(unittest.TestCase):
    def test_us_fail_jp_ok_does_not_raise(self) -> None:
        kept = {"us": {"ranking20": [{"ticker": "CACHE"}]}}
        written: dict[str, object] = {}

        def run_jp() -> dict:
            return {"ranking20": [{"ticker": "9983"}]}

        def run_us() -> dict:
            raise RankingResponseError(NOT_OBJECT_ERROR)

        result = sync_markets_independently(
            {"jp": run_jp, "us": run_us},
            on_success=lambda m, data: written.__setitem__(m, data),
            on_failure=lambda m, exc: written.__setitem__(m, kept[m]),
        )
        self.assertEqual(result["ok"], ["jp"])
        self.assertIn("us", result["failed"])
        self.assertTrue(result["partial"])
        self.assertFalse(result["all_failed"])
        self.assertEqual(written["jp"]["ranking20"][0]["ticker"], "9983")
        self.assertEqual(written["us"]["ranking20"][0]["ticker"], "CACHE")


if __name__ == "__main__":
    unittest.main()
