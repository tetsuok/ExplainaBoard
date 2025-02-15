"""Tests for explainaboard.loaders.extractive_qa."""

import unittest

from explainaboard.constants import TaskType
from explainaboard.loaders.loader_factory import get_loader_class
from explainaboard.loaders.qa_extractive import QAExtractiveLoader


class ExtractiveQALoaderTest(unittest.TestCase):
    def test_get_loader_class(self) -> None:
        self.assertIs(get_loader_class(TaskType.qa_extractive), QAExtractiveLoader)
