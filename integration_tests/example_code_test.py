import unittest

from integration_tests.utils import test_output_path, top_path

from explainaboard import FileType, get_processor, Source, TaskType
from explainaboard.loaders import get_loader_class
from explainaboard.loaders.file_loader import DatalabLoaderOption


class ExampleCodeTest(unittest.TestCase):
    """
    This tests example code that is included in the documentation.
    """

    def test_readme_datalab_dataset(self):
        loader = get_loader_class(TaskType.text_classification).from_datalab(
            dataset=DatalabLoaderOption("sst2"),
            output_data=f"{top_path}/integration_tests/artifacts/text_classification/"
            "output_sst2.txt",
            output_source=Source.local_filesystem,
            output_file_type=FileType.text,
        )
        data = loader.load().samples
        processor = get_processor(TaskType.text_classification)
        analysis = processor.process(metadata={}, sys_output=data)
        analysis.write_to_directory(test_output_path)

    def test_readme_custom_dataset(self):
        dataset = f"{top_path}/integration_tests/artifacts/summarization/dataset.tsv"
        output = f"{top_path}/integration_tests/artifacts/summarization/output.txt"
        loader = get_loader_class(TaskType.summarization)(
            dataset_data=dataset, output_data=output
        )
        data = loader.load().samples
        processor = get_processor(TaskType.summarization)
        analysis = processor.process(metadata={}, sys_output=data)
        analysis.write_to_directory(test_output_path)