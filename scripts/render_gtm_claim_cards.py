import argparse
import csv
import json
import os
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
DATASET_DIR = ROOT / "submission_final" / "dataset"
FEATURE_CONFIG = ROOT / "submission_final" / "gtm_config" / "g5_card_features.json"
EXPECTED_CLASSES = {"Invalid Claim", "Manual Review", "Valid Claim"}


def load_font(size, bold=False):
    font_name = "arialbd.ttf" if bold else "arial.ttf"
    font_path = Path("C:/Windows/Fonts") / font_name
    try:
        return ImageFont.truetype(str(font_path), size)
    except OSError:
        return ImageFont.load_default()


def safe_claim_id(value):
    normalized = re.sub(r"[^A-Za-z0-9_-]", "_", value)
    if not normalized:
        raise ValueError("ClaimID cannot be converted to a safe filename")
    return normalized


def wrap_text(draw, value, font, max_width):
    words = str(value).split()
    lines = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if current and draw.textlength(candidate, font=font) > max_width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines or [""]


def render_card(row, groups, width, height, destination):
    image = Image.new("RGB", (width, height), "#f3f6fb")
    draw = ImageDraw.Draw(image)
    font_title = load_font(31, bold=True)
    font_section = load_font(18, bold=True)
    font_label = load_font(14, bold=True)
    font_value = load_font(17)

    draw.rectangle((0, 0, width, 174), fill="#18314d")
    draw.text((54, 38), "ASSUREX  /  CLAIM SUMMARY", font=font_title, fill="#ffffff")
    draw.text((56, 96), "Structured warranty record", font=font_label, fill="#c7d7e8")
    draw.text((56, 120), "Claim evidence summary", font=font_section, fill="#ffffff")

    margin = 52
    column_gap = 18
    card_width = (width - margin * 2 - column_gap) // 2
    group_top = 194
    group_gap = 11
    row_height = 44
    label_height = 17

    for group in groups:
        fields = group["fields"]
        rows = (len(fields) + 1) // 2
        group_height = 52 + rows * row_height + 10
        draw.rounded_rectangle(
            (margin, group_top, width - margin, group_top + group_height),
            radius=7,
            fill="#ffffff",
            outline="#d8e0ea",
            width=2,
        )
        draw.text(
            (margin + 18, group_top + 13),
            group["name"],
            font=font_section,
            fill="#234b6b",
        )
        for index, field in enumerate(fields):
            column = index % 2
            row_index = index // 2
            x = margin + 18 + column * (card_width + column_gap)
            y = group_top + 48 + row_index * row_height
            label = str(field["label"])
            value = str(row.get(field["column"], "")).strip() or "Not provided"
            draw.text((x, y), label, font=font_label, fill="#65758a")
            value_lines = wrap_text(
                draw,
                value,
                font_value,
                card_width - 35,
            )
            for line_index, line in enumerate(value_lines[:2]):
                draw.text(
                    (x, y + label_height + 2 + line_index * 20),
                    line,
                    font=font_value,
                    fill="#17283e",
                )
        group_top += group_height + group_gap

    draw.text(
        (margin, height - 43),
        "Claim evidence summary · no model output or decision shown",
        font=font_label,
        fill="#68798e",
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    image.save(destination, format="PNG", optimize=True)


def render_dataset(args, output_dir, manifest_path):
    config = json.loads(FEATURE_CONFIG.read_text(encoding="utf-8"))
    groups = config["groups"]
    configured_fields = [
        field["column"]
        for group in groups
        for field in group["fields"]
    ]
    forbidden = {
        "ClaimClass",
        "ActualClass",
        "PythonPrediction",
        "PythonConfidence",
        "FinalDecision",
        "Decision",
    }
    if len(configured_fields) != len(set(configured_fields)):
        raise ValueError("G5 card configuration contains duplicate fields")
    if forbidden.intersection(configured_fields):
        raise ValueError("Card fields must not contain labels or model decisions")

    manifest_rows = []
    all_claim_ids = set()
    for split in ("train", "validation", "test"):
        csv_path = DATASET_DIR / f"assurex_{split}.csv"
        with csv_path.open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            missing = sorted(set(configured_fields + ["ClaimID", "ClaimClass"]) - set(reader.fieldnames or []))
            if missing:
                raise ValueError(f"{split} CSV is missing columns: {missing}")
            rows = list(reader)
        split_ids = [row["ClaimID"] for row in rows]
        if len(split_ids) != len(set(split_ids)):
            raise ValueError(f"Duplicate ClaimID found in {split} split")
        overlap = all_claim_ids.intersection(split_ids)
        if overlap:
            raise ValueError(f"ClaimIDs overlap between splits: {len(overlap)}")
        all_claim_ids.update(split_ids)

        for row in rows:
            actual_class = row["ClaimClass"]
            if actual_class not in EXPECTED_CLASSES:
                raise ValueError(f"Unexpected ClaimClass: {actual_class}")
            claim_id = row["ClaimID"]
            relative_path = (
                Path("gtm_dataset")
                / args.dataset_version
                / "cards"
                / split
                / f"{safe_claim_id(claim_id)}.png"
            )
            card_path = ROOT / relative_path
            card_valid = False
            if card_path.exists():
                try:
                    with Image.open(card_path) as existing_card:
                        card_valid = existing_card.size == (
                            int(config["image_width"]),
                            int(config["image_height"]),
                        )
                        existing_card.verify()
                except OSError:
                    card_valid = False
            if not card_valid:
                render_card(
                    row,
                    groups,
                    int(config["image_width"]),
                    int(config["image_height"]),
                    card_path,
                )
            manifest_rows.append(
                {
                    "ClaimID": claim_id,
                    "Split": split,
                    "ActualClass": actual_class,
                    "RelativePath": relative_path.as_posix(),
                }
            )

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with manifest_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=["ClaimID", "Split", "ActualClass", "RelativePath"],
        )
        writer.writeheader()
        writer.writerows(manifest_rows)
    print(
        json.dumps(
            {
                "dataset_version": args.dataset_version,
                "manifest": manifest_path.relative_to(ROOT).as_posix(),
                "cards_rendered": len(manifest_rows),
                "split_counts": {
                    split: sum(row["Split"] == split for row in manifest_rows)
                    for split in ("train", "validation", "test")
                },
                "configured_card_fields": len(configured_fields),
                "labels_or_predictions_rendered": False,
            },
            indent=2,
        )
    )


def main():
    parser = argparse.ArgumentParser(
        description="Render locked CSV splits as Google Teachable Machine claim cards."
    )
    parser.add_argument("--dataset-version", default="G5-v2")
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", args.dataset_version):
        parser.error("--dataset-version may contain only letters, digits, _ and -")

    output_dir = ROOT / "gtm_dataset" / args.dataset_version
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "card_manifest.csv"
    if manifest_path.exists():
        raise FileExistsError(
            f"Versioned card dataset is already complete: {manifest_path}"
        )

    lock_path = output_dir / ".render.lock"
    try:
        with lock_path.open("x", encoding="utf-8") as lock_file:
            lock_file.write(str(os.getpid()))
    except FileExistsError as exc:
        raise RuntimeError(
            f"Another renderer owns {args.dataset_version}; refusing concurrent writes."
        ) from exc

    try:
        render_dataset(args, output_dir, manifest_path)
    finally:
        lock_path.unlink(missing_ok=True)


if __name__ == "__main__":
    main()