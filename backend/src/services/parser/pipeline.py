from typing import Dict, Any, Optional

from pydantic import AnyUrl
from docling.datamodel.pipeline_options import (
    PdfPipelineOptions,
    PictureDescriptionApiOptions,
)
from docling.chunking import HybridChunker  # type: ignore

from docling_core.transforms.serializer.base import BaseDocSerializer
from docling_core.types.doc.document import DoclingDocument
from docling_core.transforms.chunker.tokenizer.huggingface import HuggingFaceTokenizer
from docling_core.transforms.chunker.hierarchical_chunker import (
    ChunkingDocSerializer,
    ChunkingSerializerProvider,
)
from docling_core.transforms.serializer.markdown import (
    MarkdownTableSerializer,
    MarkdownParams,
)

from transformers import AutoTokenizer

from src.config import Settings


def get_pdf_pipeline_options(settings: Settings) -> PdfPipelineOptions:
    parser_settings = settings.parser

    # Note: Disabling picture descriptions due to a known issue with OpenAI API response parsing
    # The API returns a tuple (text, token_count) but docling expects just a string
    # This causes: ValidationError: Input should be a valid string [type=string_type, input_value=(..., 548), input_type=tuple]

    # Uncomment and fix the response parsing if picture descriptions are needed:
    # model_url = "https://api.openai.com/v1/chat/completions"
    # picture_description_api_options = PictureDescriptionApiOptions(
    #     url=AnyUrl(model_url),
    #     prompt=parser_settings.picture_prompt,
    #     params={"model": settings.openai.model_name},
    #     headers={"Authorization": f"Bearer {settings.openai.openai_api_key}"},
    #     timeout=settings.openai.timeout,
    # )

    return PdfPipelineOptions(
        images_scale=parser_settings.image_scale,
        generate_picture_images=True,
        do_picture_description=False,  # Disabled due to API response parsing issue
        # picture_description_options=picture_description_api_options,
        do_table_structure=parser_settings.do_table_structure,
        do_ocr=parser_settings.do_orc,
        enable_remote_services=False,  # Disabled since we're not using remote API for picture descriptions
    )


def get_chunker(settings: Settings) -> HybridChunker:
    parser_config = settings.parser

    tokenizer_model_id = parser_config.tokenizer_model_id
    max_tokens = parser_config.max_tokens
    image_mode = parser_config.image_mode
    image_placeholder = parser_config.image_placeholder
    mark_annotation = parser_config.mark_annotation
    include_annotation = parser_config.include_annotation

    tokenizer = HuggingFaceTokenizer(
        tokenizer=AutoTokenizer.from_pretrained(tokenizer_model_id),
        max_tokens=max_tokens,
    )

    class CustomMDSerializerProvider(ChunkingSerializerProvider):
        def get_serializer(self, doc: DoclingDocument):
            return ChunkingDocSerializer(
                doc=doc,
                table_serializer=MarkdownTableSerializer(),
                params=MarkdownParams(
                    image_mode=image_mode,
                    image_placeholder=image_placeholder,
                    mark_annotations=mark_annotation,
                    include_annotations=include_annotation,
                ),
            )

    return HybridChunker(
        tokenizer=tokenizer, serializer_provider=CustomMDSerializerProvider()
    )
