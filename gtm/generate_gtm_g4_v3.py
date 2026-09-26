from __future__ import annotations

from pathlib import Path
import hashlib
import json
import shutil

import pandas as pd
from PIL import Image, ImageDraw, ImageFont


# ============================================================
# ASSUREX CLAIM ENGINE - GTM CARD GENERATOR
# ============================================================
# Pipeline stage:
# CARD FEATURE SET G0 -> Generate images
#
# Rules:
# - Uses the SAME locked Train / Validation / Test claim rows as Python.
# - ClaimClass is used ONLY to place TRAIN images into class folders.
# - ClaimClass / label text is NEVER rendered on the image.
# - ClaimID is used in the filename only; it is NOT rendered on the image.
# - All visual variants of one ClaimID stay in the same locked split.
# - Existing G0 output is cleared before regeneration to prevent stale images.
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

TRAIN_PATH = PROJECT_ROOT / "data" / "train" / "assurex_v3_train.csv"
VALIDATION_PATH = PROJECT_ROOT / "data" / "validation" / "assurex_v3_validation.csv"
TEST_PATH = PROJECT_ROOT / "data" / "test" / "assurex_v3_test.csv"

CONFIG_PATH = (
    PROJECT_ROOT
    / "gtm"
    / "card_features"
    / "g4_card_features_v3.json"
)

OUTPUT_ROOT = PROJECT_ROOT / "gtm_dataset" / "G4_V3"
MANIFEST_PATH = OUTPUT_ROOT / "card_manifest.csv"
SUMMARY_PATH = OUTPUT_ROOT / "generation_summary.json"

TARGET = "ClaimClass"
ID_COLUMN = "ClaimID"

EXPECTED_ROWS = {
    "train": 1050,
    "validation": 225,
    "test": 225,
}

EXPECTED_CLASS_COUNTS = {
    "train": 350,
    "validation": 75,
    "test": 75,
}

CLASS_ORDER = [
    "Invalid Claim",
    "Manual Review",
    "Valid Claim",
]

# These must never appear in a visual feature-set config.
PROHIBITED_RENDER_COLUMNS = {
    "ClaimClass",
    "PolicyClass",
    "HardInvalidReasons",
    "ManualReviewReasons",
    "ExpectedDecision",
    "FinalDecision",
    "ScenarioID",
}

POSITIVE_VALUES = {
    "Yes",
    "Active",
    "Covered",
    "Complete",
}

NEGATIVE_VALUES = {
    "No",
    "Expired",
}

WARNING_VALUES = {
    "Unknown",
    "Not Applicable",
    "MISSING",
}

FIELD_LABEL_WIDTH = 230


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(
        path,
        keep_default_na=False,
        na_values=[""],
    )


def load_config(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(
            f"Card feature config not found:\n{path}"
        )

    config = json.loads(
        path.read_text(encoding="utf-8")
    )

    if config.get("feature_set") != "G4":
        raise ValueError(
            "This generator currently expects feature_set=G4."
        )

    return config


def config_columns(config: dict) -> list[str]:
    columns = []

    for group in config["groups"]:
        for field in group["fields"]:
            columns.append(field["column"])

    return columns


def validate_config(config: dict) -> None:
    columns = config_columns(config)

    duplicate_columns = sorted(
        {
            column
            for column in columns
            if columns.count(column) > 1
        }
    )

    if duplicate_columns:
        raise ValueError(
            "Duplicate fields in G0 config: "
            + ", ".join(duplicate_columns)
        )

    prohibited = sorted(
        set(columns) & PROHIBITED_RENDER_COLUMNS
    )

    if prohibited:
        raise ValueError(
            "Target/leakage fields are prohibited from GTM cards: "
            + ", ".join(prohibited)
        )

    if not columns:
        raise ValueError("G0 card feature set is empty.")


def validate_splits(
    train: pd.DataFrame,
    validation: pd.DataFrame,
    test: pd.DataFrame,
    config: dict,
) -> None:
    splits = {
        "train": train,
        "validation": validation,
        "test": test,
    }

    required_columns = {
        ID_COLUMN,
        TARGET,
        *config_columns(config),
    }

    for split_name, df in splits.items():
        if len(df) != EXPECTED_ROWS[split_name]:
            raise ValueError(
                f"{split_name}: expected {EXPECTED_ROWS[split_name]} rows, "
                f"found {len(df)}."
            )

        if df[ID_COLUMN].duplicated().any():
            raise ValueError(
                f"{split_name}: duplicate ClaimID detected."
            )

        missing = sorted(
            required_columns - set(df.columns)
        )

        if missing:
            raise ValueError(
                f"{split_name}: missing card fields: "
                + ", ".join(missing)
            )

        counts = df[TARGET].value_counts().to_dict()

        for label in CLASS_ORDER:
            if counts.get(label, 0) != EXPECTED_CLASS_COUNTS[split_name]:
                raise ValueError(
                    f"{split_name}: expected "
                    f"{EXPECTED_CLASS_COUNTS[split_name]} {label}, "
                    f"found {counts.get(label, 0)}."
                )

    train_ids = set(train[ID_COLUMN])
    val_ids = set(validation[ID_COLUMN])
    test_ids = set(test[ID_COLUMN])

    if train_ids & val_ids:
        raise ValueError("Train/Validation ClaimID overlap.")

    if train_ids & test_ids:
        raise ValueError("Train/Test ClaimID overlap.")

    if val_ids & test_ids:
        raise ValueError("Validation/Test ClaimID overlap.")


def find_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = []

    if bold:
        candidates.extend([
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
            "/Library/Fonts/Arial Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ])
    else:
        candidates.extend([
            "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/Library/Fonts/Arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ])

    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            return ImageFont.truetype(
                str(path),
                size=size,
            )

    return ImageFont.load_default()


def normalize_display_value(column: str, value) -> str:
    if pd.isna(value):
        return "MISSING"

    # Numbers
    if column == "ClaimAmount":
        try:
            return f"{float(value):,.0f}"
        except (TypeError, ValueError):
            return str(value)

    if column == "OCRConfidence":
        try:
            return f"{float(value):.2f}"
        except (TypeError, ValueError):
            return str(value)

    if column in {
        "WarrantyRemainingDays",
        "WarrantyDurationMonths",
        "ClaimReportingDelayDays",
        "MissingDocumentCount",
        "RepairCount",
        "PriorClaimCount",
    }:
        try:
            return str(int(round(float(value))))
        except (TypeError, ValueError):
            return str(value)

    text = str(value).strip()

    return text if text else "MISSING"


def value_style(value: str) -> tuple[tuple[int, int, int], tuple[int, int, int]]:
    if value in POSITIVE_VALUES:
        return (223, 246, 232), (26, 92, 52)

    if value in NEGATIVE_VALUES:
        return (252, 230, 230), (145, 32, 32)

    if value in WARNING_VALUES:
        return (250, 241, 214), (128, 90, 18)

    return (233, 239, 248), (42, 62, 92)


def truncate_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font,
    max_width: int,
) -> str:
    if draw.textbbox((0, 0), text, font=font)[2] <= max_width:
        return text

    suffix = "..."

    for length in range(len(text) - 1, 0, -1):
        candidate = text[:length] + suffix

        if draw.textbbox(
            (0, 0),
            candidate,
            font=font,
        )[2] <= max_width:
            return candidate

    return suffix


def draw_field_row(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    width: int,
    height: int,
    label: str,
    value: str,
    label_font,
    value_font,
) -> None:
    draw.text(
        (x, y + 5),
        label,
        font=label_font,
        fill=(60, 68, 82),
    )

    badge_x = x + FIELD_LABEL_WIDTH
    badge_width = width - FIELD_LABEL_WIDTH

    bg, fg = value_style(value)

    draw.rounded_rectangle(
        [
            badge_x,
            y,
            badge_x + badge_width,
            y + height - 4,
        ],
        radius=12,
        fill=bg,
    )

    display = truncate_text(
        draw,
        value,
        value_font,
        badge_width - 24,
    )

    draw.text(
        (badge_x + 12, y + 5),
        display,
        font=value_font,
        fill=fg,
    )


def ordered_groups(config: dict, variant: int) -> list[dict]:
    groups = list(config["groups"])

    if not groups:
        return []

    if variant == 1:
        return groups

    shift = (variant - 1) % len(groups)

    return (
        groups[shift:]
        + groups[:shift]
    )


def render_card(
    row: pd.Series,
    config: dict,
    variant: int,
    output_path: Path,
) -> None:
    width = int(config["image_width"])
    height = int(config["image_height"])

    if variant % 2 == 1:
        background = (247, 249, 252)
        panel_fill = (255, 255, 255)
    else:
        background = (243, 247, 250)
        panel_fill = (252, 254, 255)

    image = Image.new(
        "RGB",
        (width, height),
        background,
    )

    draw = ImageDraw.Draw(image)

    title_font = find_font(42, bold=True)
    subtitle_font = find_font(23, bold=False)
    group_font = find_font(27, bold=True)
    label_font = find_font(21, bold=False)
    value_font = find_font(21, bold=True)

    margin = 45
    y = 38

    # Neutral header: never render ClaimClass or ClaimID.
    draw.text(
        (margin, y),
        "ASSUREX CLAIM SUMMARY",
        font=title_font,
        fill=(26, 43, 68),
    )

    y += 58

    draw.text(
        (margin, y),
        "Warranty claim evidence card",
        font=subtitle_font,
        fill=(92, 103, 120),
    )

    y += 55

    groups = ordered_groups(
        config,
        variant,
    )

    available_height = height - y - margin
    gap = 14
    total_fields = sum(
        len(group["fields"])
        for group in groups
    )

    # Group titles and rows share the remaining vertical space.
    group_title_h = 38
    total_group_overhead = len(groups) * (group_title_h + gap)
    row_height = max(
        36,
        int(
            (
                available_height
                - total_group_overhead
            )
            / max(total_fields, 1)
        ),
    )

    for group in groups:
        group_fields = group["fields"]

        panel_height = (
            group_title_h
            + len(group_fields) * row_height
            + 22
        )

        draw.rounded_rectangle(
            [
                margin,
                y,
                width - margin,
                y + panel_height,
            ],
            radius=18,
            fill=panel_fill,
            outline=(221, 228, 237),
            width=2,
        )

        draw.text(
            (margin + 22, y + 11),
            group["name"],
            font=group_font,
            fill=(35, 55, 82),
        )

        row_y = y + group_title_h + 12

        for field in group_fields:
            column = field["column"]
            label = field["label"]

            value = normalize_display_value(
                column,
                row[column],
            )

            draw_field_row(
                draw=draw,
                x=margin + 22,
                y=row_y,
                width=width - 2 * margin - 44,
                height=row_height,
                label=label,
                value=value,
                label_font=label_font,
                value_font=value_font,
            )

            row_y += row_height

        y += panel_height + gap

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    image.save(
        output_path,
        format="PNG",
        optimize=True,
    )


def image_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def prepare_output() -> None:
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)

    OUTPUT_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )


def generate_split(
    split_name: str,
    df: pd.DataFrame,
    config: dict,
    variants: int,
    manifest_rows: list[dict],
) -> int:
    generated = 0

    for _, row in df.iterrows():
        claim_id = str(row[ID_COLUMN])
        actual_class = str(row[TARGET])

        for variant in range(1, variants + 1):
            filename = (
                f"{claim_id}_v{variant:02d}.png"
            )

            if split_name == "train":
                output_path = (
                    OUTPUT_ROOT
                    / "train"
                    / actual_class
                    / filename
                )
            else:
                # Validation/Test stay flat. Actual label comes from locked CSV.
                output_path = (
                    OUTPUT_ROOT
                    / split_name
                    / "images"
                    / filename
                )

            render_card(
                row=row,
                config=config,
                variant=variant,
                output_path=output_path,
            )

            manifest_rows.append({
                "ClaimID": claim_id,
                "Split": split_name,
                "ActualClass": actual_class,
                "Variant": variant,
                "Filename": filename,
                "RelativePath": str(
                    output_path.relative_to(
                        PROJECT_ROOT
                    )
                ),
                "FeatureSet": config["feature_set"],
                "ImageSHA256": image_sha256(
                    output_path
                ),
                "TargetRendered": False,
                "ClaimIDRendered": False,
            })

            generated += 1

    return generated


def main():
    print("=" * 72)
    print("ASSUREX V3 - GTM G4 CARD GENERATION")
    print("=" * 72)

    config = load_config(CONFIG_PATH)
    validate_config(config)

    train = read_csv(TRAIN_PATH)
    validation = read_csv(VALIDATION_PATH)
    test = read_csv(TEST_PATH)

    validate_splits(
        train,
        validation,
        test,
        config,
    )

    prepare_output()

    manifest_rows = []

    train_images = generate_split(
        "train",
        train,
        config,
        int(config["train_variants"]),
        manifest_rows,
    )

    validation_images = generate_split(
        "validation",
        validation,
        config,
        int(config["validation_variants"]),
        manifest_rows,
    )

    test_images = generate_split(
        "test",
        test,
        config,
        int(config["test_variants"]),
        manifest_rows,
    )

    manifest = pd.DataFrame(
        manifest_rows
    )

    manifest.to_csv(
        MANIFEST_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    # Integrity checks after generation.
    expected_train_images = (
        len(train)
        * int(config["train_variants"])
    )
    expected_validation_images = (
        len(validation)
        * int(config["validation_variants"])
    )
    expected_test_images = (
        len(test)
        * int(config["test_variants"])
    )

    if train_images != expected_train_images:
        raise RuntimeError(
            "Unexpected Train image count."
        )

    if validation_images != expected_validation_images:
        raise RuntimeError(
            "Unexpected Validation image count."
        )

    if test_images != expected_test_images:
        raise RuntimeError(
            "Unexpected Test image count."
        )

    if manifest["TargetRendered"].any():
        raise RuntimeError(
            "Target leakage detected in card manifest."
        )

    if manifest["ClaimIDRendered"].any():
        raise RuntimeError(
            "ClaimID unexpectedly rendered."
        )

    # All variants of a claim must be in exactly one split.
    split_counts_per_claim = (
        manifest.groupby("ClaimID")["Split"]
        .nunique()
    )

    if (split_counts_per_claim > 1).any():
        raise RuntimeError(
            "A ClaimID appears in more than one GTM split."
        )

    rendered_fields = config_columns(
        config
    )

    summary = {
        "feature_set": config["feature_set"],
        "rendered_field_count": len(rendered_fields),
        "rendered_fields": rendered_fields,
        "target_rendered": False,
        "claimid_rendered": False,
        "splits": {
            "train": {
                "claims": len(train),
                "variants_per_claim": int(config["train_variants"]),
                "images": train_images,
            },
            "validation": {
                "claims": len(validation),
                "variants_per_claim": int(config["validation_variants"]),
                "images": validation_images,
            },
            "test": {
                "claims": len(test),
                "variants_per_claim": int(config["test_variants"]),
                "images": test_images,
            },
        },
        "claimid_overlap": False,
        "stale_output_prevented": True,
        "output_root": str(OUTPUT_ROOT),
        "next_step": "Train GTM G4 using train class folders only. Keep validation/test images unseen for evaluation.",
    }

    SUMMARY_PATH.write_text(
        json.dumps(
            summary,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"Feature set                   : {config['feature_set']}")
    print(f"Rendered fields               : {len(rendered_fields)}")
    print(f"Train claims                  : {len(train)}")
    print(f"Train variants / claim        : {config['train_variants']}")
    print(f"Train images                  : {train_images}")
    print(f"Validation claims             : {len(validation)}")
    print(f"Validation images             : {validation_images}")
    print(f"Test claims                   : {len(test)}")
    print(f"Test images                   : {test_images}")
    print("ClaimID overlap               : NONE")
    print("ClaimClass rendered           : NO")
    print("ClaimID rendered              : NO")
    print("Old G4_V3 output cleared         : YES")

    print("\nCreated:")
    print(f" - {OUTPUT_ROOT / 'train'}")
    print(f" - {OUTPUT_ROOT / 'validation' / 'images'}")
    print(f" - {OUTPUT_ROOT / 'test' / 'images'}")
    print(f" - {MANIFEST_PATH}")
    print(f" - {SUMMARY_PATH}")

    print("\nIMPORTANT:")
    print(" - Train GTM only from gtm_dataset/G0/train/<class>/ folders.")
    print(" - Do NOT use validation or test images for GTM training.")
    print(" - ClaimClass is not visible on any card.")
    print(" - The same locked ClaimIDs as Python are preserved.")
    print(" - Next pipeline stage: TRAIN GTM G4.")


if __name__ == "__main__":
    main()
