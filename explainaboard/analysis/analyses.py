"""Base classes to specify analyses."""

from __future__ import annotations

import abc
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, final, Optional, TypeVar

import numpy as np

import explainaboard.analysis.bucketing
from explainaboard.analysis.case import AnalysisCase, AnalysisCaseCollection
from explainaboard.analysis.feature import FeatureType
from explainaboard.analysis.performance import BucketPerformance
from explainaboard.metrics.metric import (
    Metric,
    MetricConfig,
    MetricResult,
    MetricStats,
    Score,
    SimpleMetricStats,
)
from explainaboard.serialization.serializers import PrimitiveSerializer
from explainaboard.utils.typing_utils import narrow, unwrap


@dataclass
class AnalysisResult(metaclass=abc.ABCMeta):
    """A base class specifying the result of an analysis.

    The actual details of the result will be implemented by the inheriting class.

    Attributes:
        name: The name of the analysis.
        level: The level that the analysis belongs to.
    """

    name: str
    level: str

    @abc.abstractmethod
    def generate_report(self) -> str:
        """Generate human-readable report.

        Returns:
            Multi-lined string representing the report of this result.
        """
        ...

    @staticmethod
    def from_dict(dikt):
        """Deserialization method."""
        type = dikt.pop('cls_name')
        if type == 'BucketAnalysisResult':
            return BucketAnalysisResult.from_dict(dikt)
        elif type == 'ComboCountAnalysisResult':
            return ComboCountAnalysisResult.from_dict(dikt)
        elif type == 'CalibrationAnalysisResult':
            return CalibrationAnalysisResult.from_dict(dikt)
        else:
            raise ValueError(f'bad AnalysisResult type {type}')


@dataclass
class Analysis(metaclass=abc.ABCMeta):
    """A super-class for analyses.

    Analyses take in examples and analyze their features in
    some way. The exact analysis performed will vary depending on the inheriting
    class.

    Attributes:
        description: a textual description of the analysis to be performed
        level: The level that the analysis belongs to.
    """

    description: str | None
    level: str

    @abc.abstractmethod
    def perform(
        self,
        cases: list[AnalysisCase],
        metrics: dict[str, Metric],
        stats: dict[str, MetricStats],
        confidence_alpha: float,
    ) -> AnalysisResult:
        """Perform the analysis.

        Args:
            cases: The list of analysis cases over which to perform the analysis.
              These could be examples, spans, tokens, etc.
            metrics: The metrics used to evaluate the cases.
            stats: The statistics calculated by each metric.
            confidence_alpha: In the case that any significance analysis is performed,
                      the inverse confidence level.

        Returns:
            The result of the analysis.
        """
        ...

    @final
    @staticmethod
    def from_dict(dikt: dict):
        """Deserialization method."""
        type = dikt.pop('cls_name')
        if type == 'BucketAnalysis':
            return BucketAnalysis(
                description=dikt.get('description'),
                level=dikt['level'],
                feature=dikt['feature'],
                method=dikt.get('method', 'continuous'),
                num_buckets=dikt.get('num_buckets', 4),
                setting=dikt.get('setting'),
                sample_limit=dikt.get('sample_limit', 50),
            )
        elif type == 'ComboCountAnalysis':
            return ComboCountAnalysis(
                description=dikt.get('description'),
                level=dikt['level'],
                features=tuple(dikt['features']),
            )
        elif type == 'CalibrationAnalysis':
            return CalibrationAnalysis(
                description=dikt.get('description'),
                level=dikt['level'],
                feature=dikt['feature'],
                num_buckets=dikt.get('num_buckets', 10),
                sample_limit=dikt.get('sample_limit', 50),
            )

    @final
    @staticmethod
    def _subsample_analysis_cases(
        sample_limit: int, analysis_cases: list[int]
    ) -> list[int]:
        """Sample a subset from a list.

        Args:
            sample_limit: The maximum number to sample
            analysis_cases: A list of sample IDs

        Returns:
            Subsampled list of sample IDs
        """
        if len(analysis_cases) > sample_limit:
            sample_ids = np.random.choice(analysis_cases, sample_limit, replace=False)
            return sample_ids.tolist()
        else:
            return analysis_cases


@final
@dataclass
class BucketAnalysisResult(AnalysisResult):
    """A result of running a `BucketAnalysis`.

    Attributes:
        bucket_performances: A list of performances bucket-by-bucket, including the
          interval over which the bucket is calculated, the performance itself, etc.
          See `BucketPerformance` for more details.
        cls_name: The name of the class.
    """

    bucket_performances: list[BucketPerformance]
    cls_name: Optional[str] = None

    @staticmethod
    def from_dict(dikt: dict) -> BucketAnalysisResult:
        """Deserialization method."""
        bucket_performances = [
            BucketPerformance.from_dict(v1) for v1 in dikt['bucket_performances']
        ]
        return BucketAnalysisResult(
            name=dikt['name'],
            level=dikt['level'],
            bucket_performances=bucket_performances,
        )

    def __post_init__(self):
        """Set the class name and validate."""
        metric_names = self.bucket_performances[0].results.keys()

        for bucket_perf in self.bucket_performances:
            if bucket_perf.results.keys() != metric_names:
                raise ValueError(
                    "Inconsistent metrics. "
                    f"Required: {set(metric_names)}, "
                    f"got: {set(bucket_perf.results.keys())}"
                )

        self.cls_name: str = self.__class__.__name__

    def generate_report(self) -> str:
        """See AnalysisResult.generate_report."""
        texts: list[str] = []

        metric_names = sorted(k for k in self.bucket_performances[0].results)

        for metric_name in metric_names:
            texts.append(f"the information of #{self.name}#")
            texts.append(f"bucket_name\t{metric_name}\t#samples")

            for bucket_perf in self.bucket_performances:
                metric_result = bucket_perf.results[metric_name]
                metric_value = metric_result.get_value(Score, "score").value

                if bucket_perf.bucket_interval is not None:
                    bucket_name = f"{unwrap(bucket_perf.bucket_interval)}"
                else:
                    bucket_name = unwrap(bucket_perf.bucket_name)

                texts.append(
                    f"{bucket_name}\t" f"{metric_value}\t" f"{bucket_perf.n_samples}"
                )

            texts.append('')

        return "\n".join(texts)


@final
@dataclass
class BucketAnalysis(Analysis):
    """Perform an analysis of various examples bucketed by features.

    Depending on which `method` is chosen here, the way bucketing is performed will be
    different. See the documentation of each function in the
    `explainaboard.analysis.bucketing` package for more details.

    Attributes:
        feature: the name of the feature to bucket
        method: the bucket strategy, can be "continuous", "discrete", or "fixed"
        num_buckets: the number of buckets to be used
        setting: parameters of bucketing, varying by `method`
        sample_limit: an upper limit on the number of samples saved in each bucket.
        cls_name: the name of the class.
    """

    feature: str
    method: str = "continuous"
    num_buckets: int = 4
    setting: Any = None  # For different bucket_methods, the settings are diverse
    sample_limit: int = 50
    cls_name: Optional[str] = None

    def __post_init__(self):
        """Set the class name."""
        self.cls_name: str = self.__class__.__name__

    AnalysisCaseType = TypeVar('AnalysisCaseType')

    def perform(
        self,
        cases: list[AnalysisCase],
        metrics: dict[str, Metric],
        stats: dict[str, MetricStats],
        confidence_alpha: float,
    ) -> AnalysisResult:
        """See Analysis.perform."""
        # Preparation for bucketing
        bucket_func: Callable[..., list[AnalysisCaseCollection]] = getattr(
            explainaboard.analysis.bucketing,
            self.method,
        )

        if len(cases) == 0 or self.feature not in cases[0].features:
            raise RuntimeError(f"bucket analysis: feature {self.feature} not found.")

        samples_over_bucket = bucket_func(
            sample_features=[(x, x.features[self.feature]) for x in cases],
            bucket_number=self.num_buckets,
            bucket_setting=self.setting,
        )

        bucket_performances: list[BucketPerformance] = []
        for bucket_collection in samples_over_bucket:
            # Subsample examples to save
            subsampled_ids = self._subsample_analysis_cases(
                self.sample_limit, bucket_collection.samples
            )

            n_samples = len(bucket_collection.samples)

            results: dict[str, MetricResult] = {}

            for metric_name, metric_func in metrics.items():
                metric_stat = stats[metric_name]

                # Samples may be empty when user defined a bucket interval that
                # has no samples
                if n_samples == 0.0:
                    results[metric_name] = MetricResult({})
                else:
                    bucket_stats = metric_stat.filter(bucket_collection.samples)
                    results[metric_name] = metric_func.evaluate_from_stats(
                        bucket_stats,
                        confidence_alpha=confidence_alpha,
                    )

            bucket_performances.append(
                BucketPerformance(
                    n_samples=n_samples,
                    bucket_samples=subsampled_ids,
                    results=results,
                    bucket_interval=bucket_collection.interval,
                    bucket_name=bucket_collection.name,
                )
            )

        return BucketAnalysisResult(
            name=self.feature, level=self.level, bucket_performances=bucket_performances
        )


@final
@dataclass
class CalibrationAnalysisResult(AnalysisResult):
    """A result of running a `CalibrationAnalysis`.

    Two types of calibration errors are calculated according to
    https://arxiv.org/abs/1706.04599

    Attributes:
        bucket_performances: A list of performances bucket-by-bucket, including the
          interval over which the bucket is calculated, the Accuracy performance, and
          the average confidence as Accuracy performance's auxiliary result.
        expected_calibration_error: calibration error that measures the difference in
          expectation between confidence and accuracy.
        maximum_calibration_error: calibration error that meausre the worst-case
          deviation between confidence and accuracy.
        cls_name: The name of the class.
    """

    bucket_performances: list[BucketPerformance]
    expected_calibration_error: float
    maximum_calibration_error: float
    cls_name: Optional[str] = None

    @staticmethod
    def from_dict(dikt: dict) -> CalibrationAnalysisResult:
        """Deserialization method."""
        bucket_performances = [
            BucketPerformance.from_dict(v1) for v1 in dikt['bucket_performances']
        ]
        expected_calibration_error = dikt['expected_calibration_error']
        maximum_calibration_error = dikt['maximum_calibration_error']
        return CalibrationAnalysisResult(
            name=dikt['name'],
            level=dikt['level'],
            bucket_performances=bucket_performances,
            expected_calibration_error=expected_calibration_error,
            maximum_calibration_error=maximum_calibration_error,
        )

    def __post_init__(self):
        """Set the class name and validate."""
        for bucket_perf in self.bucket_performances:
            metric_result = bucket_perf.results.get("Accuracy", None)
            if metric_result is None:
                raise ValueError(
                    "Wrong metrics. "
                    "Required: Accuracy, "
                    f"got: {set(bucket_perf.results.keys())}"
                )
            confidence = metric_result.get_value_or_none(Score, "confidence")
            if confidence is None:
                raise ValueError("MetricResult does not have the \"confidence\" score.")

        self.cls_name: str = self.__class__.__name__

    def generate_report(self) -> str:
        """See AnalysisResult.generate_report."""
        texts: list[str] = []

        metric_names = sorted(self.bucket_performances[0].results.keys())

        for metric_name in metric_names:
            texts.append(f"the information of #{self.name}#")
            texts.append(f"bucket_name\t{metric_name}\t#samples")

            for bucket_perf in self.bucket_performances:
                metric_result = bucket_perf.results[metric_name]
                score = metric_result.get_value(Score, "score").value

                if bucket_perf.bucket_interval is not None:
                    bucket_name = f"{unwrap(bucket_perf.bucket_interval)}"
                else:
                    bucket_name = unwrap(bucket_perf.bucket_name)

                texts.append(f"{bucket_name}\t" f"{score}\t" f"{bucket_perf.n_samples}")

            texts.append('')

        texts.append(f"expected_calibration_error\t{self.expected_calibration_error}")
        texts.append(f"maximum_calibration_error\t{self.maximum_calibration_error}")
        texts.append('')
        return "\n".join(texts)


@final
@dataclass
class CalibrationAnalysis(Analysis):
    """Perform calibration analysis.

    The interval [0, 1] is evenly divided into buckets.
    Calculate the accuracy and average confidence of each bucket.

    Attributes:
        feature: the name of the confidence feature
        num_buckets: the number of buckets to be used
        sample_limit: an upper limit on the number of samples saved in each bucket.
        cls_name: the name of the class.
    """

    feature: str
    num_buckets: int = 10
    sample_limit: int = 50
    cls_name: Optional[str] = None

    def __post_init__(self):
        """Set the class name."""
        self.cls_name: str = self.__class__.__name__
        if self.num_buckets <= 0:
            raise ValueError(f"Invalid num_buckets: {self.num_buckets}")

    AnalysisCaseType = TypeVar('AnalysisCaseType')

    def _perform_calibration_analysis(
        self, bucket_performances: list[BucketPerformance] = []
    ) -> tuple[float, float]:
        """Calculate the metrics for calibration analysis.

        Args:
            bucket_performances: BucketPerformance to calculate the metrics.

        Returns:
            Tuple of following values:
                - The expected calibration error.
                - The maximul calibration error.
        """
        total_error, total_size = 0.0, 0
        mce = 0.0
        for bucket_performance in bucket_performances:
            metric_result = bucket_performance.results.get("Accuracy", MetricResult({}))
            bucket_accuracy = metric_result.get_value(Score, "score").value
            bucket_confidence = metric_result.get_value(Score, "confidence").value
            bucket_size = bucket_performance.n_samples
            total_error += bucket_size * abs(bucket_accuracy - bucket_confidence)
            total_size += bucket_size
            mce = max(mce, abs(bucket_accuracy - bucket_confidence))
        ece = (total_error / total_size) if total_size > 0 else 0.0
        return ece, mce

    def perform(
        self,
        cases: list[AnalysisCase],
        metrics: dict[str, Metric],
        stats: dict[str, MetricStats],
        confidence_alpha: float,
    ) -> AnalysisResult:
        """See Analysis.perform."""
        if len(cases) == 0 or self.feature not in cases[0].features:
            raise RuntimeError(
                f"calibration analysis: feature {self.feature} not found."
            )

        acc_metric = metrics.get('Accuracy', None)
        metric_stat = stats.get('Accuracy', None)
        if not acc_metric or not metric_stat:
            raise RuntimeError("calibration analysis: metric Accuracy not found.")

        # Get confidence metric stats
        acc_data = metric_stat.get_data()
        conf_data = np.expand_dims(
            np.array([float(case.features.get(self.feature, 0.0)) for case in cases]), 1
        )
        assert acc_data.shape == conf_data.shape
        conf_metric_stat = SimpleMetricStats(conf_data)

        # Preparation for bucketing
        bucket_func: Callable[..., list[AnalysisCaseCollection]] = getattr(
            explainaboard.analysis.bucketing,
            "fixed",
        )

        bucket_setting = [
            (
                (float(i) / self.num_buckets, float(i + 1) / self.num_buckets)
                if i < self.num_buckets - 1
                else (float(i) / self.num_buckets, 1.0)
            )
            for i in range(self.num_buckets)
        ]

        samples_over_bucket = bucket_func(
            sample_features=[(x, x.features[self.feature]) for x in cases],
            bucket_number=self.num_buckets,
            bucket_setting=bucket_setting,
        )

        bucket_performances: list[BucketPerformance] = []
        for bucket_collection in samples_over_bucket:
            # Subsample examples to save
            subsampled_ids = self._subsample_analysis_cases(
                self.sample_limit, bucket_collection.samples
            )

            n_samples = len(bucket_collection.samples)

            # Samples may be empty when user defined a bucket interval that
            # has no samples
            if n_samples == 0.0:
                metric_result = MetricResult({})
            else:
                bucket_stats = metric_stat.filter(bucket_collection.samples)
                bucket_conf_stats = conf_metric_stat.filter(bucket_collection.samples)
                metric_result = acc_metric.evaluate_from_stats(
                    bucket_stats,
                    confidence_alpha=confidence_alpha,
                    auxiliary_stats=bucket_conf_stats,
                )

            bucket_performances.append(
                BucketPerformance(
                    n_samples=n_samples,
                    bucket_samples=subsampled_ids,
                    results={"Accuracy": metric_result},
                    bucket_interval=bucket_collection.interval,
                    bucket_name=bucket_collection.name,
                )
            )

        ece, mce = self._perform_calibration_analysis(bucket_performances)
        return CalibrationAnalysisResult(
            name=self.feature,
            level=self.level,
            bucket_performances=bucket_performances,
            expected_calibration_error=ece,
            maximum_calibration_error=mce,
        )


@dataclass(frozen=True)
class ComboOccurence:
    """A struct representing occurences of the string tuples.

    Args:
        features: The feature values that the occurence is counted.
        sample_count: Number of occurrences of the feature.
        sample_ids: List of sample IDs that has the given feature values
            This list may contain subsampled IDs to suppress memory
            efficiency, so `len(sample_ids) <= sample_count`.
    """

    features: tuple[str, ...]
    sample_count: int
    sample_ids: list[int]

    @staticmethod
    def from_dict(dikt: dict) -> ComboOccurence:
        """Deserialization method."""
        return ComboOccurence(
            features=dikt['features'],
            sample_count=dikt['sample_count'],
            sample_ids=dikt['sample_ids'],
        )

    def __lt__(self, other: ComboOccurence) -> bool:
        """Implement __lt__ to allow natural sorting."""
        return (self.features, self.sample_count) < (other.features, other.sample_count)


@final
@dataclass
class ComboCountAnalysisResult(AnalysisResult):
    """A result of running a `ComboCountAnalysis`.

    Attributes:
        features: A tuple of strings, representing the feature names that were
          analyzed
        combo_occurrences: A list of tuples. The first tuple element is the feature
          values corresponding to the feature names in `features`. The second element is
          the count of that feature combination in the corpus.
    """

    features: tuple[str, ...]
    combo_occurrences: list[ComboOccurence]
    cls_name: Optional[str] = None

    @staticmethod
    def from_dict(dikt: dict) -> ComboCountAnalysisResult:
        """Deserialization method."""
        return ComboCountAnalysisResult(
            name=dikt['name'],
            level=dikt['level'],
            features=dikt['features'],
            combo_occurrences=[
                ComboOccurence.from_dict(d) for d in dikt['combo_occurrences']
            ],
        )

    def __post_init__(self):
        """Set the class name and validate."""
        num_features = len(self.features)
        for occ in self.combo_occurrences:
            if len(occ.features) != num_features:
                raise ValueError(
                    "Inconsistent number of features. "
                    f"Required: {num_features}, got: {len(occ.features)}"
                )

        self.cls_name: str = self.__class__.__name__

    def generate_report(self) -> str:
        """See AnalysisResult.generate_report."""
        texts: list[str] = []

        texts.append('feature combos for ' + ', '.join(self.features))
        texts.append('\t'.join(self.features + ('#',)))

        for occ in sorted(self.combo_occurrences):
            texts.append('\t'.join(occ.features + (str(occ.sample_count),)))

        texts.append('')
        return "\n".join(texts)


@final
@dataclass
class ComboCountAnalysis(Analysis):
    """A class used to count feature combinations (e.g. for confusion matrices).

    It will return counts of each combination of values for the features named in
    `features`.

    Args:
        features: the name of the features over which to perform the analysis
        cls_name: the name of the class
        method: the bucket strategy, only supports "discrete" for now
        sample_limit: an upper limit on the number of samples saved
          in each combo occurrence.
    """

    features: tuple[str, ...]
    cls_name: Optional[str] = None
    method: str = "discrete"
    sample_limit: int = 50

    def __post_init__(self):
        """Set the class name."""
        self.cls_name: str = self.__class__.__name__

    AnalysisCaseType = TypeVar('AnalysisCaseType')

    def perform(
        self,
        cases: list[AnalysisCase],
        metrics: dict[str, Metric],
        stats: dict[str, MetricStats],
        confidence_alpha: float,
    ) -> AnalysisResult:
        """See Analysis.perform."""
        for x in self.features:
            if x not in cases[0].features:
                raise RuntimeError(f"combo analysis: feature {x} not found.")

        combo_map: defaultdict[tuple[str, ...], list[int]] = defaultdict(list)
        for case in cases:
            feat_vals = tuple([case.features[x] for x in self.features])
            combo_map[feat_vals].append(case.sample_id)

        combo_list = [
            ComboOccurence(
                k, len(v), self._subsample_analysis_cases(self.sample_limit, v)
            )
            for k, v in combo_map.items()
        ]

        return ComboCountAnalysisResult(
            name='combo(' + ','.join(self.features) + ')',
            level=self.level,
            features=self.features,
            combo_occurrences=combo_list,
        )


@dataclass
class AnalysisLevel:
    """Specifies the features of a particular level at which analysis is performed.

    Args:
        name: the name of the analysis level
        features: the features specified for the analysis level
        metric_configs: configurations of the metrics to be applied to the level
    """

    name: str
    features: dict[str, FeatureType]
    metric_configs: dict[str, MetricConfig]

    @staticmethod
    def from_dict(dikt: dict):
        """Deserialization method."""
        serializer = PrimitiveSerializer()

        features = {
            # See https://github.com/python/mypy/issues/4717
            k: narrow(FeatureType, serializer.deserialize(v))  # type: ignore
            for k, v in dikt['features'].items()
        }
        metric_configs = {
            # See mypy/issues/4717
            narrow(str, k): narrow(
                MetricConfig, serializer.deserialize(v)  # type: ignore
            )
            for k, v in dikt['metric_configs'].items()
        }
        return AnalysisLevel(
            name=dikt['name'],
            features=features,
            metric_configs=metric_configs,
        )
