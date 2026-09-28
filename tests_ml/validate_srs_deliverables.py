from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


REQUIRED_FILES = [
    "README.md",
    "AI_USAGE.md",
    "LICENSE",
    "docs/SRS_COMPLIANCE_MATRIX.md",
    "docs/TEST_CASE_MATRIX.md",
    "docs/INSTALLATION_AND_EXECUTION.md",
    "docs/DEMO_AND_BLOG_PLACEHOLDERS.md",
    "documentation/PROJECT_REPORT.md",
    "reports/SRS_COMPLIANCE_REPORT.md",
    "assurex_web/backend/requirements.txt",
    "package.json",
    "model/assurex_v3_final_model.joblib",
    "gtm/frozen_G2_V3/model.json",
    "gtm/frozen_G2_V3/weights.bin",
    "gtm/frozen_G2_V3/metadata.json",
    "gtm/frozen_G2_V3/g2_card_features_v3.json",
    "gtm/frozen_G2_V3/SHA256SUMS.txt",
    "data/train/assurex_v3_train.csv",
    "data/validation/assurex_v3_validation.csv",
    "data/test/assurex_v3_test.csv",
    "comparison/assurex_v3_model_comparison_final.csv",
]

REQUIRED_DIRS = [
    "assurex_web/backend",
    "assurex_web/frontend",
    "dataset_generator",
    "preprocessing",
    "features",
    "training",
    "model",
    "gtm",
    "config/warranty_policies",
    "tests_ml",
    "tests",
    "screenshots",
    "reports",
    "documentation",
]


def pass_line(message: str) -> None:
    print(f"PASS: {message}")


def warn_line(message: str) -> None:
    print(f"WARN: {message}")


def fail_line(message: str) -> None:
    raise AssertionError(message)


def require_file(relative: str) -> None:
    path = ROOT / relative
    if not path.is_file():
        fail_line(f"Missing required file: {relative}")
    pass_line(f"Found file: {relative}")


def require_dir(relative: str) -> None:
    path = ROOT / relative
    if not path.is_dir():
        fail_line(f"Missing required directory: {relative}")
    pass_line(f"Found directory: {relative}")


def check_placeholder(path: Path, label: str) -> None:
    text = path.read_text(encoding="utf-8", errors="replace")
    if "TO_BE_FILLED" in text:
        warn_line(f"{label} still contains TO_BE_FILLED placeholders")
    else:
        pass_line(f"{label} placeholders completed")


def main() -> None:
    print("=" * 72)
    print("ASSUREX SRS DELIVERABLE VALIDATION")
    print("=" * 72)

    for relative in REQUIRED_FILES:
        require_file(relative)

    for relative in REQUIRED_DIRS:
        require_dir(relative)

    sample_cards = list((ROOT / "sample_claims" / "gtm_cards").glob("*"))
    if len(sample_cards) < 2100:
        warn_line(
            "Committed sample_claims/gtm_cards has fewer than 2,100 images. "
            "Generate or attach the full GTM training-image dataset before final submission."
        )
    else:
        pass_line("GTM sample card count >= 2,100")

    check_placeholder(ROOT / "docs" / "DEMO_AND_BLOG_PLACEHOLDERS.md", "Demo/blog links")
    check_placeholder(ROOT / "docs" / "INSTALLATION_AND_EXECUTION.md", "Evaluator credentials")
    check_placeholder(ROOT / "AI_USAGE.md", "AI usage declaration")

    print("=" * 72)
    print("VALIDATION COMPLETE")
    print("=" * 72)


if __name__ == "__main__":
    main()

