from __future__ import annotations

from explainaboard import TaskType
from explainaboard.analysis import feature
from explainaboard.analysis.analyses import (
    Analysis,
    AnalysisLevel,
    BucketAnalysis,
    ComboCountAnalysis,
)
from explainaboard.analysis.feature import FeatureType
from explainaboard.metrics.accuracy import AccuracyConfig
from explainaboard.metrics.metric import MetricConfig
from explainaboard.processors.processor import Processor
from explainaboard.processors.processor_registry import register_processor
from explainaboard.utils.typing_utils import unwrap


@register_processor(TaskType.tabular_classification)
class TextClassificationProcessor(Processor):
    @classmethod
    def task_type(cls) -> TaskType:
        return TaskType.tabular_classification

    def default_analysis_levels(self) -> list[AnalysisLevel]:
        features: dict[str, FeatureType] = {
            "true_label": feature.Value(
                dtype="string",
                description="the true label of the input",
            ),
            "predicted_label": feature.Value(
                dtype="string",
                description="the predicted label",
            ),
        }

        return [
            AnalysisLevel(
                name='example',
                features=features,
                metric_configs=self.default_metrics(),
            )
        ]

    def default_analyses(self) -> list[Analysis]:
        features = self.default_analysis_levels()[0].features
        continuous_features = [
            k for k, v in features.items() if ('float' in unwrap(v.dtype))
        ]
        # Create analyses
        analyses: list[Analysis] = [
            BucketAnalysis(
                level="example",
                description=features["true_label"].description,
                feature="true_label",
                method="discrete",
                number=15,
            ),
            ComboCountAnalysis(
                level="example",
                description="confusion matrix",
                features=("true_label", "predicted_label"),
            ),
        ]
        for x in continuous_features:
            analyses.append(
                BucketAnalysis(
                    level="example",
                    description=features[x].description,
                    feature=x,
                    method="continuous",
                )
            )
        return analyses

    @classmethod
    def default_metrics(
        cls, level="example", source_language=None, target_language=None
    ) -> list[MetricConfig]:
        return [AccuracyConfig(name='Accuracy')]
