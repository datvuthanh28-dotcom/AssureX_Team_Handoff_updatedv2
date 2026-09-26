ASSUREX CLAIM ENGINE - FINAL SUBMISSION
======================================

1. DATASET
----------
dataset/assurex_train.csv
dataset/assurex_validation.csv
dataset/assurex_test.csv

Locked split:
- Train      : 1050 claims
- Validation : 225 claims
- Test       : 225 claims

Each class contains 75 Test claims.

2. PRIMARY PYTHON MODEL
-----------------------
Model      : Gradient Boosting
File       : python_model/assurex_final_model.joblib

Final Test:
- Accuracy        : 0.955556
- Macro Precision : 0.958220
- Macro Recall    : 0.955556
- Macro F1        : 0.955886
- Mean Confidence : 0.932035
- Errors          : 10 / 225

SRS Accuracy >= 85%: PASS

3. GTM MODEL
------------
Final Feature Set : G5
Rendered Fields   : 23

Files:
- gtm_model/model.json
- gtm_model/metadata.json
- gtm_model/weights.bin

Final Test:
- Accuracy        : 0.813333
- Macro Precision : 0.832807
- Macro Recall    : 0.813333
- Macro F1        : 0.812936
- Mean Confidence : 0.877439
- Errors          : 42 / 225

SRS Accuracy >= 85%: FAIL

GTM feature selection used Validation only.
Test data was not used for tuning.

4. FINAL MODEL SELECTION
------------------------
Primary selection metric : Macro F1

Primary Model   : Python Gradient Boosting
Secondary Model : GTM G5

Python Macro F1 : 0.955886
GTM Macro F1    : 0.812936

Both models were evaluated on the same locked 225 Test ClaimIDs.

5. GTM ABLATION
---------------
Removed from final G5:
- DamageType
- ExtendedWarranty
- WarrantyDurationMonths

Removal tested but rolled back:
- Brand
- ClaimSubmissionChannel
- ReceiptAvailable
- PriorClaimCount

6. COMPARISON FILES
-------------------
See comparison/ for:
- overall model metrics
- per-class metrics
- confusion matrix comparison
- error-pattern comparison
- final comparison summary
