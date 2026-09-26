from pathlib import Path

import pytesseract
from PIL import (
    Image,
    ImageEnhance,
    ImageFilter,
    ImageOps,
)
from pytesseract import Output

from app.ocr.warranty_parser import (
    extract_warranty_fields,
)


def preprocess_image(
    image,
):
    image = image.convert("RGB")

    gray = ImageOps.grayscale(
        image
    )

    gray = ImageOps.autocontrast(
        gray
    )

    # Upscale before OCR.
    gray = gray.resize(
        (
            gray.width * 2,
            gray.height * 2,
        ),
        Image.Resampling.LANCZOS,
    )

    gray = ImageEnhance.Contrast(
        gray
    ).enhance(1.5)

    gray = gray.filter(
        ImageFilter.UnsharpMask(
            radius=2,
            percent=180,
            threshold=3,
        )
    )

    return gray


def run_ocr(
    image,
    psm,
):
    config = (
        f"--oem 3 --psm {psm} "
        "-c preserve_interword_spaces=1"
    )

    raw_text = (
        pytesseract.image_to_string(
            image,
            lang="vie+eng",
            config=config,
        )
    )

    data = (
        pytesseract.image_to_data(
            image,
            lang="vie+eng",
            output_type=Output.DICT,
            config=config,
        )
    )

    confidences = []

    for value in data.get(
        "conf",
        [],
    ):
        try:
            confidence = float(
                value
            )
        except (
            TypeError,
            ValueError,
        ):
            continue

        if confidence >= 0:
            confidences.append(
                confidence
            )

    mean_confidence = (
        sum(confidences)
        / len(confidences)
        if confidences
        else 0.0
    )

    extracted = (
        extract_warranty_fields(
            raw_text
        )
    )

    field_count = sum(
        value not in {
            None,
            "",
        }
        for value in extracted.values()
    )

    return {
        "raw_text":
            raw_text,

        "ocr_confidence":
            mean_confidence / 100,

        "extracted_data":
            extracted,

        "field_count":
            field_count,

        "psm":
            psm,
    }


def extract_warranty_image(
    image_path: str | Path,
):
    image = Image.open(
        image_path
    )

    prepared = preprocess_image(
        image
    )

    # Try both dense-table OCR and
    # sparse-text OCR.
    candidates = [
        run_ocr(
            prepared,
            6,
        ),
        run_ocr(
            prepared,
            11,
        ),
    ]

    # Prefer candidate extracting
    # more structured fields.
    # Confidence breaks ties.
    best = max(
        candidates,
        key=lambda item: (
            item["field_count"],
            item["ocr_confidence"],
        ),
    )

    return {
        "ocr_confidence": round(
            best[
                "ocr_confidence"
            ],
            4,
        ),

        "extracted_data":
            best[
                "extracted_data"
            ],

        "raw_text":
            best[
                "raw_text"
            ],

        "ocr_psm":
            best["psm"],
    }
