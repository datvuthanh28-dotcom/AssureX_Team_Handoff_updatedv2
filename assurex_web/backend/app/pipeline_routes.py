"""Read-only presentation of the existing V3 pipeline artifacts."""
import json
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Depends
from app.auth_routes import require_roles

ROOT = Path(__file__).resolve().parents[3]
router = APIRouter(prefix="/api/pipeline", tags=["ML pipeline"], dependencies=[Depends(require_roles("ADMIN"))])


def table(path):
    source = ROOT / path
    if not source.exists():
        return {"source": path, "rows": [], "available": False}
    frame = pd.read_csv(source, keep_default_na=False)
    return {"source": path, "rows": json.loads(frame.to_json(orient="records")), "available": True}


def document(path):
    source = ROOT / path
    return json.loads(source.read_text()) if source.exists() else {}


@router.get("")
def pipeline():
    raw = pd.read_csv(ROOT / "data/raw/assurex_v3_raw.csv", keep_default_na=False, na_values=[""])
    clean = pd.read_csv(ROOT / "data/cleaned/assurex_v3_clean.csv", keep_default_na=False, na_values=[""])
    profile = [{"Column": col, "Type": str(clean[col].dtype), "Missing": int(clean[col].isna().sum()), "Missing %": round(float(clean[col].isna().mean() * 100), 2), "Unique": int(clean[col].nunique())} for col in clean.columns]
    reports = {
        "cleaning": "data/audit/assurex_v3_cleaning_summary.csv",
        "missing": "data/audit/assurex_v3_cleaning_missing_before_after.csv",
        "filter": "data/audit/assurex_v3_initial_feature_filter_report.csv",
        "correlation": "data/correlation_v3/pearson_matrix.csv",
        "redundancy": "data/correlation_v3/redundancy_candidates.csv",
        "split": "data/audit/assurex_v3_split_summary.csv",
        "models": "data/model_comparison_v3/assurex_v3_model_comparison.csv",
        "importance": "data/feature_selection_v3/assurex_v3_selected_feature_importance.csv",
        "selection": "data/feature_selection_v3/assurex_v3_feature_selection_history.csv",
        "text_test": "data/final_evaluation_v3/assurex_v3_test_metrics.csv",
        "text_matrix": "data/final_evaluation_v3/assurex_v3_test_confusion_matrix.csv",
        "image_ablation": "gtm/results/visual_ablation_v3.csv",
        "image_test": "data/final_evaluation_v3/gtm/assurex_v3_gtm_g2_final_test_metrics.csv",
        "image_matrix": "data/final_evaluation_v3/gtm/assurex_v3_gtm_g2_final_test_confusion_matrix.csv",
        "comparison": "comparison/assurex_v3_model_comparison_summary.csv",
    }
    return {
        "audit": {"rows": len(clean), "raw_rows": len(raw), "columns": len(clean.columns), "duplicates_removed": int(len(raw) - len(clean)), "duplicates": int(clean.duplicated().sum()), "missing": int(clean.isna().sum().sum()), "class_counts": clean["ClaimClass"].value_counts().to_dict(), "profile": profile},
        "reports": {key: table(path) for key, path in reports.items()},
        "active": document("model_tracking/active_models.json"),
        "split": document("data/audit/assurex_v3_split_manifest.json"),
        "selection": document("data/audit/assurex_v3_feature_selection_manifest.json"),
        "freeze": document("data/audit/assurex_v3_model_freeze_manifest.json"),
        "google": document("gtm/frozen_G2_V1/metadata.json"),
        "cv": {"status": "not_recorded", "folds": 5},
        "tuning": {"status": "not_recorded"},
    }
