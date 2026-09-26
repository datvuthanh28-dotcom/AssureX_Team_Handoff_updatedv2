export const claimFieldGroups = [
  {
    title: 'Warranty & Documents',
    fields: [
      {
        name: 'WarrantyCardAvailable',
        label: 'Warranty Card Available',
        type: 'select',
        options: ['Yes', 'No'],
      },
      {
        name: 'RepairReportAvailable',
        label: 'Repair Report Available',
        type: 'select',
        options: ['Yes', 'No', 'Not Applicable'],
      },
      {
        name: 'PurchaseProofAvailable',
        label: 'Purchase Proof Available',
        type: 'select',
        options: ['Yes', 'No'],
      },
      {
        name: 'RequiredDocumentsComplete',
        label: 'Required Documents Complete',
        type: 'select',
        options: ['Yes', 'No', 'Unknown'],
      },
      {
        name: 'MissingDocumentCount',
        label: 'Missing Document Count',
        type: 'number',
        min: 0,
        step: 1,
      },
      {
        name: 'AvailableDocumentCount',
        label: 'Available Document Count',
        type: 'number',
        min: 0,
        step: 1,
      },
      {
        name: 'OCRConfidence',
        label: 'OCR Confidence',
        type: 'number',
        min: 0,
        max: 1,
        step: 0.001,
      },
    ],
  },

  {
    title: 'Repair History',
    fields: [
      {
        name: 'PreviousRepair',
        label: 'Previous Repair',
        type: 'select',
        options: ['Yes', 'No'],
      },
      {
        name: 'HasRepairHistory',
        label: 'Has Repair History',
        type: 'select',
        options: ['Yes', 'No'],
      },
      {
        name: 'RepairCount',
        label: 'Repair Count',
        type: 'number',
        min: 0,
        step: 1,
      },
      {
        name: 'PriorClaimCount',
        label: 'Prior Claim Count',
        type: 'number',
        min: 0,
        step: 1,
      },
    ],
  },

  {
    title: 'Verification',
    fields: [
      {
        name: 'SerialNumberMatch',
        label: 'Serial Number Match',
        type: 'select',
        options: ['Yes', 'No', 'Unknown'],
      },
      {
        name: 'ProductModelConsistent',
        label: 'Product Model Consistent',
        type: 'select',
        options: ['Yes', 'No'],
      },
      {
        name: 'DuplicateClaimIndicator',
        label: 'Duplicate Claim Indicator',
        type: 'select',
        options: ['Yes', 'No'],
      },
      {
        name: 'ContradictionIndicator',
        label: 'Contradiction Indicator',
        type: 'select',
        options: ['Yes', 'No'],
      },
    ],
  },

  {
    title: 'Claim Details',
    fields: [
      {
        name: 'ClaimAmount',
        label: 'Claim Amount',
        type: 'number',
        min: 0,
        step: 0.01,
      },
      {
        name: 'ClaimSubmissionChannel',
        label: 'Submission Channel',
        type: 'select',
        options: ['Mobile App', 'Web', 'Service Center', 'Email'],
      },
      {
        name: 'ClaimReportingDelayDays',
        label: 'Reporting Delay Days',
        type: 'number',
        step: 1,
      },
      {
        name: 'WarrantyRemainingDays',
        label: 'Warranty Remaining Days',
        type: 'number',
        step: 1,
      },
      {
        name: 'WarrantyStatus',
        label: 'Warranty Status',
        type: 'select',
        options: ['Active', 'Expired', 'Unknown'],
      },
      {
        name: 'ClaimReportingWithinPeriod',
        label: 'Reporting Within Period',
        type: 'select',
        options: ['Yes', 'No', 'Unknown'],
      },
      {
        name: 'FaultCovered',
        label: 'Fault Covered',
        type: 'select',
        options: ['Yes', 'No'],
      },
    ],
  },
]
