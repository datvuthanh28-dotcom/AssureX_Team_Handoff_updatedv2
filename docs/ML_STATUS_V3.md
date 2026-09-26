# AssureX V3 ML Status

Completed:
- Dataset generation, cleaning, EDA, correlation analysis
- Feature engineering and iterative feature selection
- Three Python algorithms compared
- Gradient Boosting selected and frozen
- Python locked Test evaluation
- GTM G0-G4 visual ablation
- GTM G2 V3 selected and frozen
- GTM locked Test evaluation
- Python vs GTM comparison on 225 locked Test claims
- Decision Engine V3
- Regression handling for CLM01148 and CLM01188
- Three configurable warranty-policy files plus policy index
- ML integration contract
- Automated ML validation

Python final:
- Accuracy: 0.991111
- Macro F1: 0.991110
- Errors: 2

GTM G2 V3:
- Accuracy: 0.862222
- Macro F1: 0.861017
- Errors: 31

Comparison:
- Matches: 196
- Disagreements: 29
- Strong Match: 126
- Acceptable Match: 52
- Weak Match: 14
- Model Disagreement: 29
- Uncertain Result: 4

Decision Engine:
- Likely Valid: 69
- Likely Invalid: 22
- Manual Review Required: 134

Ownership boundary:
This ML work does not modify teammate-owned React, FastAPI/API, authentication, or SQL/database implementation.
