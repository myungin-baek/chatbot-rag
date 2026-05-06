"""PDF 파일 파서 (텍스트 + 이미지 추출)."""

import io
from pathlib import Path
from typing import List, Tuple

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

from app.rag.parser.base import ParsedDocument


class PDFFileParser:
    """PDF 파일 파서.
    
    텍스트 추출 (PyMuPDF) + 이미지 추출 + OCR 지원
    """

    def __init__(self, enable_ocr: bool = False):
        self.enable_ocr = enable_ocr
        self._easyocr_reader = None

    def parse(self, file_path: str) -> ParsedDocument:
        """PDF 파일을 파싱합니다."""
        if fitz is None:
            raise ImportError("PyMuPDF (fitz)가 설치되어 있지 않습니다. pip install pymupdf")

        doc = fitz.open(file_path)
        full_text = ""
        images = []
        page_count = len(doc)

        for page_num in range(page_count):
            page = doc.load_page(page_num)

            # 1. 텍스트 추출 (페이지별 메타데이터 포함)
            text = page.get_text()
            if text.strip():
                full_text += f"[Page {page_num + 1}]\n{text}\n"

            # 2. 이미지 추출
            image_list = page.get_images(full=True)
            for img_index, img in enumerate(image_list):
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]

                from PIL import Image
                img_obj = Image.open(io.BytesIO(image_bytes))
                images.append({
                    "page": page_num + 1,
                    "index": img_index,
                    "data": img_obj,
                    "format": base_image["ext"],
                })

        doc.close()

        # 이미지 OCR 처리 (동기)
        ocr_texts = []
        if self.enable_ocr and images:
            ocr_texts = self._perform_ocr(images)

        return ParsedDocument(
            document_id=Path(file_path).stem,
            file_name=Path(file_path).name,
            file_type="pdf",
            content=full_text.strip(),
            metadata={
                "pages": page_count,
                "images_extracted": len(images),
                "ocr_applied": self.enable_ocr and bool(ocr_texts),
            },
        )

    def _perform_ocr(self, images: List[dict]) -> List[str]:
        """이미지에 대해 OCR 수행."""
        try:
            import easyocr
            if self._easyocr_reader is None:
                self._easyocr_reader = easyocr.Reader(["ko", "en"], gpu=False)

            results = []
            for img_info in images:
                result = self._easyocr_reader.readtext(img_info["data"])
                ocr_text = " ".join([item[1] for item in result])
                if ocr_text.strip():
                    results.append(ocr_text)
            return results
        except ImportError:
            print("경고: EasyOCR가 설치되어 있지 않습니다. OCR을 건너뜁니다.")
            return []
