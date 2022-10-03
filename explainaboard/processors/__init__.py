"""A package for processors for each test.

When a new processor is implemented, remember to import it here so it gets registered.
"""

from explainaboard.processors import (
    argument_pair_extraction,
    aspect_based_sentiment_classification,
    chunking,
    cloze_generative,
    cloze_multiple_choice,
    conditional_generation,
    extractive_qa,
    grammatical_error_correction,
    kg_link_tail_prediction,
    language_modeling,
    machine_translation,
    meta_evaluation_wmt_da,
    named_entity_recognition,
    qa_multiple_choice,
    qa_open_domain,
    qa_tat,
    summarization,
    tabular_classification,
    tabular_regression,
    text_classification,
    text_pair_classification,
    word_segmentation,
)
from explainaboard.processors.processor_factory import get_processor_class

__all__ = [
    'aspect_based_sentiment_classification',
    'conditional_generation',
    'extractive_qa',
    'get_processor_class',
    'kg_link_tail_prediction',
    'language_modeling',
    'machine_translation',
    'named_entity_recognition',
    'qa_multiple_choice',
    'summarization',
    'text_classification',
    'tabular_classification',
    'tabular_regression',
    'text_pair_classification',
    'word_segmentation',
    'chunking',
    'cloze_multiple_choice',
    'cloze_generative',
    'grammatical_error_correction',
    'qa_open_domain',
    'meta_evaluation_wmt_da',
    'qa_tat',
    'argument_pair_extraction',
]
