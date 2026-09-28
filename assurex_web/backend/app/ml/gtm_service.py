from __future__ import annotations

import importlib.util
import json
import math
import subprocess
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd


WORKSPACE_ROOT = Path(__file__).resolve().parents[4]

GENERATOR_PATH = WORKSPACE_ROOT / "gtm" / "generate_gtm_g2_v3.py"
CONFIG_PATH = (
    WORKSPACE_ROOT / "gtm" / "frozen_G2_V1"
    / "g2_card_features_v1.json"
)
MODEL_PATH = (
    WORKSPACE_ROOT / "gtm" / "frozen_G2_V1"
    / "model.json"
)
METADATA_PATH = (
    WORKSPACE_ROOT / "gtm" / "frozen_G2_V1"
    / "metadata.json"
)
NODE_RUNNER = (
    WORKSPACE_ROOT / "assurex_web" / "backend"
    / "gtm_runtime" / "infer_g2.js"
)


def _load_renderer():
    spec = importlib.util.spec_from_file_location(
        "assurex_g2_renderer",
        GENERATOR_PATH,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load G2 renderer module")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_RENDERER = _load_renderer()
_CONFIG = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def _config_columns() -> list[str]:
    columns = []
    for group in _CONFIG["groups"]:
        for field in group["fields"]:
            columns.append(field["column"])
    return columns


CARD_COLUMNS = _config_columns()


def _canonical_key(value: str) -> str:
    return "".join(
        char.lower()
        for char in str(value)
        if char.isalnum()
    )


def _clean_value(value):
    if value is None:
        return np.nan

    if isinstance(value, float) and math.isnan(value):
        return np.nan

    return value


def _build_card_row(
    *,
    raw_input: dict,
    model_features: dict,
    rule_data: dict,
    derived: dict,
) -> pd.Series:
    merged = {}

    for source in (
        raw_input or {},
        derived or {},
        rule_data or {},
        model_features or {},
    ):
        merged.update(source)

    normalized = {
        _canonical_key(key): value
        for key, value in merged.items()
    }

    row = {}

    for column in CARD_COLUMNS:
        if column in merged:
            value = merged[column]
        else:
            value = normalized.get(
                _canonical_key(column),
                np.nan,
            )

        row[column] = _clean_value(value)

    return pd.Series(row)


def predict_gtm_claim(
    *,
    raw_input: dict,
    model_features: dict,
    rule_data: dict,
    derived: dict,
) -> dict:
    row = _build_card_row(
        raw_input=raw_input,
        model_features=model_features,
        rule_data=rule_data,
        derived=derived,
    )

    missing_card_fields = [
        column
        for column in CARD_COLUMNS
        if pd.isna(row[column])
    ]

    with tempfile.TemporaryDirectory(prefix="assurex_g2_") as tmp:
        card_path = Path(tmp) / "claim_v01.png"

        _RENDERER.render_card(
            row=row,
            config=_CONFIG,
            variant=1,
            output_path=card_path,
        )

        proc = subprocess.run(
            [
                "node",
                str(NODE_RUNNER),
                str(MODEL_PATH),
                str(METADATA_PATH),
                str(card_path),
            ],
            cwd=str(NODE_RUNNER.parent),
            capture_output=True,
            text=True,
            check=False,
        )

        if proc.returncode != 0:
            return {
                "predicted_class": None,
                "confidence": None,
                "probabilities": {},
                "model_name": "Google Teachable Machine G2 V1",
                "model_version": "gtm-g2-v1-final",
                "inference_status": "error",
                "error": proc.stderr.strip(),
                "missing_card_fields": missing_card_fields,
            }

        result = json.loads(proc.stdout)

    return {
        **result,
        "model_name": "Google Teachable Machine G2 V1",
        "model_version": "gtm-g2-v1-final",
        "inference_status": "connected",
        "missing_card_fields": missing_card_fields,
    }
