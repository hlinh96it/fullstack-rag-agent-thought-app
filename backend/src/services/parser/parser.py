from typing import Optional, Any

from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat

from src.config import Settings
from src.schema.document.models import ParsedDocument, DocumentContent, DocumentMetadata, PaperSection
from src.exeptions import PDFParsingException

from .pipeline import get_pdf_pipeline_options, get_chunker

import logging
logger = logging.getLogger(__name__)


class ParserService:
    def __init__(self, settings: Settings):
        self.settings = settings.parser
        
        pipeline_options = get_pdf_pipeline_options(settings)
        chunker = get_chunker(settings)
        
        self.converter = DocumentConverter(
            allowed_formats=[InputFormat.PDF],
            format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)}
        )
        
        self.max_pages = self.settings.max_pages
        self.max_file_size_bytes = self.settings.max_file_size_mb * 1024 * 1024
        
    async def parse_document(self, file_path: str) -> ParsedDocument:
        try: 
            result = self.converter.convert(
                source=str(file_path), max_num_pages=self.max_pages, max_file_size=self.max_file_size_bytes
            ).document
            
            sections = []
            current_section = {'title': 'Content', 'content': ''}
            for element in result.texts:
                
                # extract title and section header
                if hasattr(element, 'label') and element.label in ['title', 'section_header']:
                    if current_section['content'].strip():
                        sections.append(PaperSection(
                            title=current_section['title'], content=current_section['content'].strip()
                        ))
                    current_section = {'title': element.text.strip(), 'content': ''}
                
                # add content to current section
                else:
                    if hasattr(element, 'text') and element.text:
                        current_section['content'] += element.text + '\n'
                
            if current_section['content'].strip():
                sections.append(PaperSection(
                    title=current_section['title'], content=current_section['content'].strip()
                ))
                
            doc_content = DocumentContent(
                sections=sections, figures=[], tables=[], raw_text=result.export_to_markdown(),
                references=[]
            )
            doc_metadata = DocumentMetadata(
                title='', authors=[], abstract='', categories=[], published_date='' 
            )
            return ParsedDocument(doc_content=doc_content, doc_metadata=doc_metadata)
            
        except Exception as e:
            logger.error(f'Failed to parse document: {e}')
            error_msg = str(e).lower()

            # Note: Page and size limit checks are now handled in _validate_pdf method

            if "not valid" in error_msg:
                logger.error("PDF appears to be corrupted or not a valid PDF file")
                raise PDFParsingException(f"PDF appears to be corrupted or invalid: {file_path}")
            elif "timeout" in error_msg:
                logger.error("PDF processing timed out - file may be too complex")
                raise PDFParsingException(f"PDF processing timed out: {file_path}")
            elif "memory" in error_msg or "ram" in error_msg:
                logger.error("Out of memory - PDF may be too large or complex")
                raise PDFParsingException(f"Out of memory processing PDF: {file_path}")
            elif "max_num_pages" in error_msg or "page" in error_msg:
                logger.error(f"PDF processing issue likely related to page limits (current limit: {self.max_pages} pages)")
                raise PDFParsingException(
                    f"PDF processing failed, possibly due to page limit ({self.max_pages} pages). Error: {e}"
                )
            else:
                raise PDFParsingException(f"Failed to parse PDF with Docling: {e}")
        
    

if __name__ == "__main__":
    settings = Settings()
    parser = ParserService(settings)