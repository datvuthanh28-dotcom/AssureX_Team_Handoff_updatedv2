#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

ROOT = Path.cwd()

CUSTOMER_ROUTES = ROOT / "assurex_web/backend/app/customer_routes.py"
ACTIVE_MODELS = ROOT / "model_tracking/active_models.json"
G2_GENERATOR = ROOT / "gtm/generate_gtm_g2_v3.py"

for p in [CUSTOMER_ROUTES, ACTIVE_MODELS, G2_GENERATOR]:
    if not p.exists():
        raise SystemExit(f"STOP: missing required file: {p}")

backup = ROOT / "integration_backup_v3_gtm"
backup.mkdir(exist_ok=True)

for p in [CUSTOMER_ROUTES, ACTIVE_MODELS, G2_GENERATOR]:
    shutil.copy2(p, backup / p.name)

runtime_dir = ROOT / "assurex_web/backend/gtm_runtime"
runtime_dir.mkdir(parents=True, exist_ok=True)

(runtime_dir / "package.json").write_text('{\n  "name": "assurex-gtm-g2-runtime",\n  "private": true,\n  "version": "1.0.0",\n  "dependencies": {\n    "@tensorflow/tfjs": "^4.22.0",\n    "pngjs": "^7.0.0"\n  }\n}\n', encoding="utf-8")
(runtime_dir / "infer_g2.js").write_text('const fs = require("fs");\nconst path = require("path");\nconst tf = require("@tensorflow/tfjs");\nconst { PNG } = require("pngjs");\n\nasync function loadModel(modelJsonPath) {\n  const dir = path.dirname(modelJsonPath);\n  const modelJson = JSON.parse(fs.readFileSync(modelJsonPath, "utf8"));\n\n  const specs = [];\n  const buffers = [];\n\n  for (const group of modelJson.weightsManifest || []) {\n    for (const spec of group.weights || []) {\n      specs.push(spec);\n    }\n    for (const rel of group.paths || []) {\n      buffers.push(fs.readFileSync(path.join(dir, rel)));\n    }\n  }\n\n  const merged = Buffer.concat(buffers);\n  const weightData = merged.buffer.slice(\n    merged.byteOffset,\n    merged.byteOffset + merged.byteLength\n  );\n\n  const handler = tf.io.fromMemory({\n    modelTopology: modelJson.modelTopology,\n    weightSpecs: specs,\n    weightData: weightData,\n  });\n\n  return await tf.loadLayersModel(handler);\n}\n\nfunction pngToTensor(pngPath, imageSize) {\n  const decoded = PNG.sync.read(fs.readFileSync(pngPath));\n  const { width, height, data } = decoded;\n\n  const rgb = new Float32Array(width * height * 3);\n\n  let j = 0;\n  for (let i = 0; i < data.length; i += 4) {\n    rgb[j++] = data[i];\n    rgb[j++] = data[i + 1];\n    rgb[j++] = data[i + 2];\n  }\n\n  let x = tf.tensor3d(rgb, [height, width, 3], "float32");\n\n  const side = Math.min(width, height);\n  const top = Math.floor((height - side) / 2);\n  const left = Math.floor((width - side) / 2);\n\n  const cropped = x.slice([top, left, 0], [side, side, 3]);\n  const resized = tf.image.resizeBilinear(\n    cropped,\n    [imageSize, imageSize],\n    false\n  );\n\n  const normalized = resized.div(127.5).sub(1.0);\n  const batched = normalized.expandDims(0);\n\n  x.dispose();\n  cropped.dispose();\n  resized.dispose();\n  normalized.dispose();\n\n  return batched;\n}\n\nasync function main() {\n  const [modelJsonPath, metadataPath, pngPath] = process.argv.slice(2);\n\n  if (!modelJsonPath || !metadataPath || !pngPath) {\n    throw new Error(\n      "usage: node infer_g2.js model.json metadata.json card.png"\n    );\n  }\n\n  const metadata = JSON.parse(fs.readFileSync(metadataPath, "utf8"));\n  const labels = metadata.labels;\n  const imageSize = Number(metadata.imageSize || 224);\n\n  const model = await loadModel(modelJsonPath);\n  const input = pngToTensor(pngPath, imageSize);\n\n  let output = model.predict(input);\n  if (Array.isArray(output)) {\n    output = output[0];\n  }\n\n  const values = Array.from(await output.data());\n\n  const probabilities = {};\n  labels.forEach((label, i) => {\n    probabilities[label] = Number(values[i]);\n  });\n\n  let bestIndex = 0;\n  for (let i = 1; i < values.length; i++) {\n    if (values[i] > values[bestIndex]) {\n      bestIndex = i;\n    }\n  }\n\n  process.stdout.write(JSON.stringify({\n    predicted_class: labels[bestIndex],\n    confidence: Number(values[bestIndex]),\n    probabilities,\n  }));\n\n  input.dispose();\n  output.dispose();\n  model.dispose();\n}\n\nmain().catch((err) => {\n  process.stderr.write(String(err.stack || err));\n  process.exit(1);\n});\n', encoding="utf-8")

gtm_service_path = ROOT / "assurex_web/backend/app/ml/gtm_service.py"
gtm_service_path.write_text('from __future__ import annotations\n\nimport importlib.util\nimport json\nimport math\nimport subprocess\nimport tempfile\nfrom pathlib import Path\n\nimport numpy as np\nimport pandas as pd\n\n\nWORKSPACE_ROOT = Path(__file__).resolve().parents[4]\n\nGENERATOR_PATH = WORKSPACE_ROOT / "gtm" / "generate_gtm_g2_v3.py"\nCONFIG_PATH = (\n    WORKSPACE_ROOT / "gtm" / "frozen_G2_V3"\n    / "g2_card_features_v3.json"\n)\nMODEL_PATH = (\n    WORKSPACE_ROOT / "gtm" / "frozen_G2_V3"\n    / "model.json"\n)\nMETADATA_PATH = (\n    WORKSPACE_ROOT / "gtm" / "frozen_G2_V3"\n    / "metadata.json"\n)\nNODE_RUNNER = (\n    WORKSPACE_ROOT / "assurex_web" / "backend"\n    / "gtm_runtime" / "infer_g2.js"\n)\n\n\ndef _load_renderer():\n    spec = importlib.util.spec_from_file_location(\n        "assurex_g2_renderer",\n        GENERATOR_PATH,\n    )\n    if spec is None or spec.loader is None:\n        raise RuntimeError("Unable to load G2 renderer module")\n\n    module = importlib.util.module_from_spec(spec)\n    spec.loader.exec_module(module)\n    return module\n\n\n_RENDERER = _load_renderer()\n_CONFIG = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))\n\n\ndef _config_columns() -> list[str]:\n    columns = []\n    for group in _CONFIG["groups"]:\n        for field in group["fields"]:\n            columns.append(field["column"])\n    return columns\n\n\nCARD_COLUMNS = _config_columns()\n\n\ndef _canonical_key(value: str) -> str:\n    return "".join(\n        char.lower()\n        for char in str(value)\n        if char.isalnum()\n    )\n\n\ndef _clean_value(value):\n    if value is None:\n        return np.nan\n\n    if isinstance(value, float) and math.isnan(value):\n        return np.nan\n\n    return value\n\n\ndef _build_card_row(\n    *,\n    raw_input: dict,\n    model_features: dict,\n    rule_data: dict,\n    derived: dict,\n) -> pd.Series:\n    merged = {}\n\n    for source in (\n        raw_input or {},\n        derived or {},\n        rule_data or {},\n        model_features or {},\n    ):\n        merged.update(source)\n\n    normalized = {\n        _canonical_key(key): value\n        for key, value in merged.items()\n    }\n\n    row = {}\n\n    for column in CARD_COLUMNS:\n        if column in merged:\n            value = merged[column]\n        else:\n            value = normalized.get(\n                _canonical_key(column),\n                np.nan,\n            )\n\n        row[column] = _clean_value(value)\n\n    return pd.Series(row)\n\n\ndef predict_gtm_claim(\n    *,\n    raw_input: dict,\n    model_features: dict,\n    rule_data: dict,\n    derived: dict,\n) -> dict:\n    row = _build_card_row(\n        raw_input=raw_input,\n        model_features=model_features,\n        rule_data=rule_data,\n        derived=derived,\n    )\n\n    missing_card_fields = [\n        column\n        for column in CARD_COLUMNS\n        if pd.isna(row[column])\n    ]\n\n    with tempfile.TemporaryDirectory(prefix="assurex_g2_") as tmp:\n        card_path = Path(tmp) / "claim_v01.png"\n\n        _RENDERER.render_card(\n            row=row,\n            config=_CONFIG,\n            variant=1,\n            output_path=card_path,\n        )\n\n        proc = subprocess.run(\n            [\n                "node",\n                str(NODE_RUNNER),\n                str(MODEL_PATH),\n                str(METADATA_PATH),\n                str(card_path),\n            ],\n            cwd=str(NODE_RUNNER.parent),\n            capture_output=True,\n            text=True,\n            check=False,\n        )\n\n        if proc.returncode != 0:\n            return {\n                "predicted_class": None,\n                "confidence": None,\n                "probabilities": {},\n                "model_name": "Google Teachable Machine G2 V3",\n                "model_version": "gtm-g2-v3-final",\n                "inference_status": "error",\n                "error": proc.stderr.strip(),\n                "missing_card_fields": missing_card_fields,\n            }\n\n        result = json.loads(proc.stdout)\n\n    return {\n        **result,\n        "model_name": "Google Teachable Machine G2 V3",\n        "model_version": "gtm-g2-v3-final",\n        "inference_status": "connected",\n        "missing_card_fields": missing_card_fields,\n    }\n', encoding="utf-8")

s = CUSTOMER_ROUTES.read_text(encoding="utf-8")

import_line = "from app.ml.decision_service import apply_business_rules\n"
gtm_import = "from app.ml.gtm_service import predict_gtm_claim\n"

if gtm_import not in s:
    if import_line not in s:
        raise SystemExit("STOP: could not locate decision_service import")
    s = s.replace(import_line, import_line + gtm_import, 1)

pattern = re.compile(
    r'decision_result\s*=\s*apply_business_rules\(\s*'
    r'feature_result\["rule_data"\],\s*'
    r'prediction\["predicted_class"\],\s*'
    r'prediction\["confidence"\],?\s*'
    r'\)'
)

replacement = """gtm_result = predict_gtm_claim(
        raw_input=raw_input,
        model_features=model_features,
        rule_data=feature_result["rule_data"],
        derived=feature_result["derived"],
    )

    decision_result = apply_business_rules(
        feature_result["rule_data"],
        prediction["predicted_class"],
        prediction["confidence"],
        gtm_prediction=gtm_result.get("predicted_class"),
        gtm_confidence=gtm_result.get("confidence"),
        python_probabilities=prediction.get("probabilities"),
        gtm_probabilities=gtm_result.get("probabilities"),
    )"""

s, count = pattern.subn(replacement, s, count=1)
if count != 1:
    raise SystemExit("STOP: could not patch apply_business_rules call")

for old, new in {
    "gtm_model_version=None,":
        'gtm_model_version=gtm_result.get("model_version"),',
    "google_prediction=None,":
        'google_prediction=gtm_result.get("predicted_class"),',
    "google_confidence=None,":
        'google_confidence=gtm_result.get("confidence"),',
    "confidence_difference=None,":
        'confidence_difference=decision_result.get("confidence_difference"),',
}.items():
    s = s.replace(old, new)

s = re.sub(
    r'model_consistency_status=\(\s*'
    r'"Uncertain Result"\s*'
    r'if\s+google_model\["inference_status"\]\s*!=\s*"connected"\s*'
    r'else\s+None\s*'
    r'\),',
    'model_consistency_status=decision_result.get("model_consistency_status"),',
    s,
    count=1,
)

s = re.sub(
    r'google_inference_status=\s*google_model\["inference_status"\],',
    'google_inference_status=gtm_result.get("inference_status"),',
    s,
    count=1,
)

CUSTOMER_ROUTES.write_text(s, encoding="utf-8")

active = json.loads(ACTIVE_MODELS.read_text(encoding="utf-8"))
google = active.setdefault("google_model", {})
google["name"] = "Google Teachable Machine G2 V3"
google["version"] = "gtm-g2-v3-final"
google["artifact_path"] = "gtm/frozen_G2_V3"
google["inference_status"] = "configured"
google["runtime"] = "assurex_web/backend/gtm_runtime/infer_g2.js"

ACTIVE_MODELS.write_text(
    json.dumps(active, indent=2) + "\n",
    encoding="utf-8",
)

smoke_path = ROOT / "tests_ml/smoke_gtm_g2_runtime.py"
smoke_path.parent.mkdir(exist_ok=True)
smoke_path.write_text('from __future__ import annotations\n\nfrom pathlib import Path\nimport sys\n\nimport pandas as pd\n\nROOT = Path(__file__).resolve().parents[1]\nBACKEND = ROOT / "assurex_web" / "backend"\n\nif str(BACKEND) not in sys.path:\n    sys.path.insert(0, str(BACKEND))\n\nfrom app.ml.gtm_service import predict_gtm_claim\n\n\ntest_path = ROOT / "data" / "test" / "assurex_v3_test.csv"\npred_path = (\n    ROOT / "data" / "final_evaluation_v3" / "gtm"\n    / "assurex_v3_gtm_g2_final_test_predictions.csv"\n)\n\ntest_df = pd.read_csv(test_path)\npred_df = pd.read_csv(pred_path)\n\nrow = test_df.iloc[0]\nclaim_id = str(row["ClaimID"])\ncontext = row.to_dict()\n\nruntime = predict_gtm_claim(\n    raw_input=context,\n    model_features=context,\n    rule_data=context,\n    derived=context,\n)\n\nexpected_row = pred_df[\n    pred_df["ClaimID"].astype(str) == claim_id\n].iloc[0]\n\nexpected_pred = str(expected_row["PredictedClass"])\nexpected_conf = float(expected_row["Confidence"])\n\nprint("=" * 72)\nprint("ASSUREX V3 - GTM G2 RUNTIME SMOKE TEST")\nprint("=" * 72)\nprint("ClaimID           :", claim_id)\nprint("Expected class    :", expected_pred)\nprint("Runtime class     :", runtime.get("predicted_class"))\nprint("Expected conf     :", round(expected_conf, 6))\nprint(\n    "Runtime conf      :",\n    round(float(runtime.get("confidence") or 0), 6),\n)\nprint("Runtime status    :", runtime.get("inference_status"))\n\nif runtime.get("inference_status") != "connected":\n    raise SystemExit(\n        "FAIL: GTM runtime inference did not connect.\\n"\n        + str(runtime.get("error"))\n    )\n\nif runtime.get("predicted_class") != expected_pred:\n    raise SystemExit(\n        "FAIL: runtime class does not match frozen Test prediction."\n    )\n\ndiff = abs(float(runtime["confidence"]) - expected_conf)\n\nprint("Confidence diff   :", round(diff, 6))\n\nif diff > 0.05:\n    raise SystemExit(\n        "FAIL: confidence difference > 0.05; "\n        "preprocessing is not close enough to frozen evaluation."\n    )\n\nprint("PASS: GTM G2 V3 runtime matches frozen Test prediction.")\n', encoding="utf-8")

print("PATCH COMPLETE")
print("Created:")
print(" -", gtm_service_path)
print(" -", runtime_dir / "infer_g2.js")
print(" -", runtime_dir / "package.json")
print(" -", smoke_path)
print("Patched:")
print(" -", CUSTOMER_ROUTES)
print(" -", ACTIVE_MODELS)
print("Backup:")
print(" -", backup)
