"""Tests for explainaboard.metrics.f1_score"""

from __future__ import annotations

import unittest

from sklearn.metrics import f1_score

from explainaboard.metrics.f1_score import (
    F1Score,
    F1ScoreConfig,
    SeqF1Score,
    SeqF1ScoreConfig,
)
from explainaboard.metrics.metric import Score
from explainaboard.utils.typing_utils import unwrap


class F1ScoreConfigTest(unittest.TestCase):
    def test_serialize(self) -> None:
        self.assertEqual(
            F1ScoreConfig(
                "F1Score",
                average="macro",
                separate_match=False,
            ).serialize(),
            {
                "name": "F1Score",
                "source_language": None,
                "target_language": None,
                "average": "macro",
                "separate_match": False,
                "ignore_classes": [],
            },
        )

    def test_deserialize(self) -> None:
        self.assertEqual(
            F1ScoreConfig.deserialize(
                {
                    "name": "F1Score",
                    "average": "macro",
                    "separate_match": False,
                }
            ),
            F1ScoreConfig(
                "F1Score",
                average="macro",
                separate_match=False,
            ),
        )

    def test_to_metric(self) -> None:
        self.assertIsInstance(
            F1ScoreConfig("F1Score").to_metric(),
            F1Score,
        )


class F1ScoreTest(unittest.TestCase):
    def test_evaluate_micro(self) -> None:
        metric = F1ScoreConfig(name='F1', average='micro').to_metric()
        true = ['a', 'b', 'a', 'b', 'a', 'a', 'c', 'c']
        pred = ['a', 'b', 'a', 'b', 'b', 'a', 'c', 'a']
        sklearn_f1 = f1_score(true, pred, average='micro')
        result = metric.evaluate(true, pred, confidence_alpha=0.05)
        self.assertAlmostEqual(
            unwrap(result.get_value(Score, "score")).value, sklearn_f1
        )

    def test_evaluate_macro(self) -> None:
        metric = F1ScoreConfig(name='F1', average='macro').to_metric()
        true = ['a', 'b', 'a', 'b', 'a', 'a', 'c', 'c']
        pred = ['a', 'b', 'a', 'b', 'b', 'a', 'c', 'a']
        sklearn_f1 = f1_score(true, pred, average='macro')
        result = metric.evaluate(true, pred, confidence_alpha=None)
        self.assertAlmostEqual(
            unwrap(result.get_value(Score, "score")).value, sklearn_f1
        )


class SeqF1ScoreConfigTest(unittest.TestCase):
    def test_serialize(self) -> None:
        self.assertEqual(
            SeqF1ScoreConfig(
                "SeqF1Score",
                average="macro",
                separate_match=False,
                tag_schema="bio",
            ).serialize(),
            {
                "name": "SeqF1Score",
                "source_language": None,
                "target_language": None,
                "average": "macro",
                "separate_match": False,
                "ignore_classes": [],
                "tag_schema": "bio",
            },
        )

    def test_deserialize(self) -> None:
        self.assertEqual(
            SeqF1ScoreConfig.deserialize(
                {
                    "name": "SeqF1Score",
                    "average": "macro",
                    "separate_match": False,
                    "tag_schema": "bio",
                }
            ),
            SeqF1ScoreConfig(
                "SeqF1Score",
                average="macro",
                separate_match=False,
                tag_schema="bio",
            ),
        )

    def test_to_metric(self) -> None:
        self.assertIsInstance(
            SeqF1ScoreConfig("SeqF1Score").to_metric(),
            SeqF1Score,
        )


class SeqF1ScoreTest(unittest.TestCase):
    def test_evaluate_micro(self) -> None:
        true = [
            ['O', 'O', 'B-MISC', 'I-MISC', 'B-MISC', 'O', 'O'],
            ['B-PER', 'I-PER', 'O'],
        ]
        pred = [
            ['O', 'O', 'B-MISC', 'I-MISC', 'B-MISC', 'I-MISC', 'O'],
            ['B-PER', 'I-PER', 'O'],
        ]
        metric = SeqF1ScoreConfig(
            name='MicroF1', average='micro', tag_schema='bio'
        ).to_metric()
        result = metric.evaluate(true, pred, confidence_alpha=None)
        self.assertAlmostEqual(
            unwrap(result.get_value(Score, "score")).value, 2.0 / 3.0
        )

    def test_evaluate_macro(self) -> None:
        true = [
            ['O', 'O', 'B-MISC', 'I-MISC', 'B-MISC', 'O', 'O'],
            ['B-PER', 'I-PER', 'O'],
        ]
        pred = [
            ['O', 'O', 'B-MISC', 'I-MISC', 'B-MISC', 'I-MISC', 'O'],
            ['B-PER', 'I-PER', 'O'],
        ]
        metric = SeqF1ScoreConfig(
            name='MacroF1', average='macro', tag_schema='bio'
        ).to_metric()
        result = metric.evaluate(true, pred, confidence_alpha=None)
        self.assertAlmostEqual(
            unwrap(result.get_value(Score, "score")).value, 3.0 / 4.0
        )
