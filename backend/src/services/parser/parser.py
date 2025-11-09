from typing import Optional, Any, List
from uuid import uuid4

from langchain_docling.loader import DoclingLoader
from langchain_core.documents import Document
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat

from src.config import Settings
from src.schema.document.models import (
    ParsedDocument,
    DocumentContent,
    DocumentMetadata,
    PaperSection,
)
from src.exeptions import PDFParsingException

from .pipeline import get_pdf_pipeline_options, get_chunker

import logging

logger = logging.getLogger(__name__)


class ParserService:
    def __init__(self, settings: Settings):
        self.settings = settings.parser
        self.milvus_namespace = settings.milvus.namespace

        self.pipeline_options = get_pdf_pipeline_options(settings)
        self.chunker = get_chunker(settings)
        self.converter = DocumentConverter(
            allowed_formats=[InputFormat.PDF],
            format_options={
                InputFormat.PDF: PdfFormatOption(
                    pipeline_options=self.pipeline_options)
            },
        )

        self.max_pages = self.settings.max_pages
        self.max_file_size_bytes = self.settings.max_file_size_mb * 1024 * 1024

        logger.info(f"👌 Docling Parser Service initialized")

    async def parse_document_docling(self, file_path: str) -> ParsedDocument:
        """Parse document by using docling only

        Args:
            file_path (str): path to parsing file
        """
        try:
            result = self.converter.convert(
                source=str(file_path), max_num_pages=self.max_pages, max_file_size=self.max_file_size_bytes,
            ).document

            sections = []
            current_section = {"title": "Content", "content": ""}
            for element in result.texts:

                # extract title and section header
                if hasattr(element, "label") and element.label in [
                    "title",
                    "section_header",
                ]:
                    if current_section["content"].strip():
                        sections.append(
                            PaperSection(
                                title=current_section["title"],
                                content=current_section["content"].strip(),
                            )
                        )
                    current_section = {
                        "title": element.text.strip(), "content": ""}

                # add content to current section
                else:
                    if hasattr(element, "text") and element.text:
                        current_section["content"] += element.text + "\n"

            if current_section["content"].strip():
                sections.append(
                    PaperSection(
                        title=current_section["title"],
                        content=current_section["content"].strip(),
                    )
                )

            doc_content = DocumentContent(
                sections=sections,
                figures=[],
                tables=[],
                raw_text=result.export_to_markdown(),
                references=[],
            )
            doc_metadata = DocumentMetadata(
                title="", authors=[], abstract="", categories=[], published_date=""
            )
            return ParsedDocument(doc_content=doc_content, doc_metadata=doc_metadata)

        except Exception as e:
            logger.error(f"Failed to parse document: {e}")
            error_msg = str(e).lower()

            # Note: Page and size limit checks are now handled in _validate_pdf method

            if "not valid" in error_msg:
                logger.error(
                    "PDF appears to be corrupted or not a valid PDF file")
                raise PDFParsingException(
                    f"PDF appears to be corrupted or invalid: {file_path}"
                )
            elif "timeout" in error_msg:
                logger.error(
                    "PDF processing timed out - file may be too complex")
                raise PDFParsingException(
                    f"PDF processing timed out: {file_path}")
            elif "memory" in error_msg or "ram" in error_msg:
                logger.error("Out of memory - PDF may be too large or complex")
                raise PDFParsingException(
                    f"Out of memory processing PDF: {file_path}")
            elif "max_num_pages" in error_msg or "page" in error_msg:
                logger.error(
                    f"PDF processing issue likely related to page limits (current limit: {self.max_pages} pages)"
                )
                raise PDFParsingException(
                    f"PDF processing failed, possibly due to page limit ({self.max_pages} pages). Error: {e}"
                )
            else:
                raise PDFParsingException(
                    f"Failed to parse PDF with Docling: {e}")

    async def parse_document_langchain(self, file_path: str) -> List[Document]:
        """Parse document using Langchain-Docling while returning Langchain-Document"""
        try:
            docs = DoclingLoader(
                file_path=file_path, converter=self.converter, chunker=self.chunker,
                export_type=self.settings.export_type,
            ).load()

            processed_docs = []
            for doc in docs:
                metadata = doc.metadata
                _metadata = {
                    "source": str(metadata["source"]),
                    "page_no": metadata["dl_meta"]["doc_items"][0]["prov"][0]["page_no"],
                    "namespace": self.milvus_namespace,
                }
                processed_docs.append(
                    Document(page_content=doc.page_content, metadata=_metadata)
                )

            return processed_docs

        except Exception as e:
            logger.error(f"Failed to parse document: {e}")
            error_msg = str(e).lower()

            # Note: Page and size limit checks are now handled in _validate_pdf method

            if "not valid" in error_msg:
                logger.error(
                    "PDF appears to be corrupted or not a valid PDF file")
                raise PDFParsingException(
                    f"PDF appears to be corrupted or invalid: {file_path}"
                )
            elif "timeout" in error_msg:
                logger.error(
                    "PDF processing timed out - file may be too complex")
                raise PDFParsingException(
                    f"PDF processing timed out: {file_path}")
            elif "memory" in error_msg or "ram" in error_msg:
                logger.error("Out of memory - PDF may be too large or complex")
                raise PDFParsingException(
                    f"Out of memory processing PDF: {file_path}")
            elif "max_num_pages" in error_msg or "page" in error_msg:
                logger.error(
                    f"PDF processing issue likely related to page limits (current limit: {self.max_pages} pages)"
                )
                raise PDFParsingException(
                    f"PDF processing failed, possibly due to page limit ({self.max_pages} pages). Error: {e}"
                )
            else:
                raise PDFParsingException(
                    f"Failed to parse PDF with Docling: {e}")
