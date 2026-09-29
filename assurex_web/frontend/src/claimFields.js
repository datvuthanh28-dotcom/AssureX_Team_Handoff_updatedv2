


export const MODEL_14_FEATURES = [
  'RepairAuthorized',
  'SerialNumberMatch',
  'ProductModelConsistent',
  'DuplicateClaimIndicator',
  'ContradictionIndicator',
  'OCRConfidence',
  'ClaimReportingDelayDays',
  'WarrantyRemainingDays',
  'ClaimReportingWithinPeriod',
  'FaultCovered',
  'RequiredDocumentsComplete',
  'MissingDocumentCount',
  'ProductIdentityMatch',
  'OCRQualityBand',
]

export const MODEL_8_FEATURES = MODEL_14_FEATURES
export const MODEL_9_FEATURES = MODEL_14_FEATURES




export const FAULT_CATEGORIES_BY_PRODUCT_CATEGORY = {
  Laptop: [
    {
      value: 'Display Failure',
      label: 'Display Failure',
      isCovered: true,
      description: 'Screen lines, flicker, dark display, touch/display malfunction without cracked glass.',
    },
    {
      value: 'Power Failure',
      label: 'Power / Mainboard Failure',
      isCovered: true,
      description: 'Device will not power on, shuts down unexpectedly, or has charging/power-board symptoms.',
    },
    {
      value: 'Battery Problem',
      label: 'Battery / Charging Problem',
      isCovered: true,
      description: 'Battery drains abnormally, will not charge, overheats during charging, or is swollen.',
    },
    {
      value: 'Keyboard & Trackpad Failure',
      label: 'Keyboard / Trackpad Failure',
      isCovered: true,
      description: 'Keys, touchpad, or pointing controls stop responding during normal use.',
    },
    {
      value: 'Overheating',
      label: 'Overheating / Fan Issue',
      isCovered: true,
      description: 'Fan noise, fan not spinning, or device shuts down because of abnormal heat.',
    },
    {
      value: 'Connectivity Issue',
      label: 'Connectivity / Port Issue',
      isCovered: true,
      description: 'Wi-Fi, Bluetooth, cellular, USB, HDMI, LAN, or other ports fail under normal use.',
    },
    {
      value: 'Audio Failure',
      label: 'Audio / Speaker / Microphone Failure',
      isCovered: true,
      description: 'Speaker, microphone, or audio output is distorted or unavailable.',
    },
    {
      value: 'Physical Damage',
      label: 'Physical Damage (Not covered)',
      isCovered: false,
      description: 'Cracks, dents, drops, impact damage, or broken exterior/panel.',
    },
    {
      value: 'Liquid Damage',
      label: 'Liquid / Water Damage (Not covered)',
      isCovered: false,
      description: 'Water, moisture, spill, or liquid ingress damage.',
    },
  ],
  Smartphone: [
    {
      value: 'Display Failure',
      label: 'Display Failure',
      isCovered: true,
      description: 'Screen lines, flicker, dark display, touch/display malfunction without cracked glass.',
    },
    {
      value: 'Power Failure',
      label: 'Power / Mainboard Failure',
      isCovered: true,
      description: 'Device will not power on, shuts down unexpectedly, or has charging/power-board symptoms.',
    },
    {
      value: 'Battery Problem',
      label: 'Battery / Charging Problem',
      isCovered: true,
      description: 'Battery drains abnormally, will not charge, overheats during charging, or is swollen.',
    },
    {
      value: 'Camera Failure',
      label: 'Camera Failure',
      isCovered: true,
      description: 'Camera, autofocus, lens, or camera sensor defect.',
    },
    {
      value: 'Connectivity Issue',
      label: 'Connectivity / Port Issue',
      isCovered: true,
      description: 'Wi-Fi, Bluetooth, cellular, USB, HDMI, LAN, or other ports fail under normal use.',
    },
    {
      value: 'Audio Failure',
      label: 'Audio / Speaker / Microphone Failure',
      isCovered: true,
      description: 'Speaker, microphone, or audio output is distorted or unavailable.',
    },
    {
      value: 'Physical Damage',
      label: 'Physical Damage (Not covered)',
      isCovered: false,
      description: 'Cracks, dents, drops, impact damage, or broken exterior/panel.',
    },
    {
      value: 'Liquid Damage',
      label: 'Liquid / Water Damage (Not covered)',
      isCovered: false,
      description: 'Water, moisture, spill, or liquid ingress damage.',
    },
  ],
  Tablet: [
    {
      value: 'Display Failure',
      label: 'Display Failure',
      isCovered: true,
      description: 'Screen lines, flicker, dark display, touch/display malfunction without cracked glass.',
    },
    {
      value: 'Power Failure',
      label: 'Power / Mainboard Failure',
      isCovered: true,
      description: 'Device will not power on, shuts down unexpectedly, or has charging/power-board symptoms.',
    },
    {
      value: 'Battery Problem',
      label: 'Battery / Charging Problem',
      isCovered: true,
      description: 'Battery drains abnormally, will not charge, overheats during charging, or is swollen.',
    },
    {
      value: 'Connectivity Issue',
      label: 'Connectivity / Port Issue',
      isCovered: true,
      description: 'Wi-Fi, Bluetooth, cellular, USB, HDMI, LAN, or other ports fail under normal use.',
    },
    {
      value: 'Physical Damage',
      label: 'Physical Damage (Not covered)',
      isCovered: false,
      description: 'Cracks, dents, drops, impact damage, or broken exterior/panel.',
    },
    {
      value: 'Liquid Damage',
      label: 'Liquid / Water Damage (Not covered)',
      isCovered: false,
      description: 'Water, moisture, spill, or liquid ingress damage.',
    },
  ],
  Television: [
    {
      value: 'Display Failure',
      label: 'Display Failure',
      isCovered: true,
      description: 'Screen lines, flicker, dark display, touch/display malfunction without cracked glass.',
    },
    {
      value: 'Power Failure',
      label: 'Power / Mainboard Failure',
      isCovered: true,
      description: 'Device will not power on, shuts down unexpectedly, or has charging/power-board symptoms.',
    },
    {
      value: 'Audio Failure',
      label: 'Audio / Speaker / Microphone Failure',
      isCovered: true,
      description: 'Speaker, microphone, or audio output is distorted or unavailable.',
    },
    {
      value: 'Connectivity Issue',
      label: 'Connectivity / Port Issue',
      isCovered: true,
      description: 'Wi-Fi, Bluetooth, cellular, USB, HDMI, LAN, or other ports fail under normal use.',
    },
    {
      value: 'Physical Damage',
      label: 'Physical Damage (Not covered)',
      isCovered: false,
      description: 'Cracks, dents, drops, impact damage, or broken exterior/panel.',
    },
    {
      value: 'Electrical Surge',
      label: 'Electrical Surge (Not covered)',
      isCovered: false,
      description: 'Damage caused by lightning or excessive external voltage.',
    },
  ],
  Monitor: [
    {
      value: 'Display Failure',
      label: 'Display Failure',
      isCovered: true,
      description: 'Screen lines, flicker, dark display, touch/display malfunction without cracked glass.',
    },
    {
      value: 'Power Failure',
      label: 'Power / Mainboard Failure',
      isCovered: true,
      description: 'Device will not power on, shuts down unexpectedly, or has charging/power-board symptoms.',
    },
    {
      value: 'Connectivity Issue',
      label: 'Connectivity / Port Issue',
      isCovered: true,
      description: 'Wi-Fi, Bluetooth, cellular, USB, HDMI, LAN, or other ports fail under normal use.',
    },
    {
      value: 'Physical Damage',
      label: 'Physical Damage (Not covered)',
      isCovered: false,
      description: 'Cracks, dents, drops, impact damage, or broken exterior/panel.',
    },
  ],
  Refrigerator: [
    {
      value: 'Cooling Failure',
      label: 'Cooling Failure',
      isCovered: true,
      description: 'Cooling performance is weak or unavailable under normal operation.',
    },
    {
      value: 'Compressor Failure',
      label: 'Compressor Failure',
      isCovered: true,
      description: 'Compressor or outdoor unit does not run, stops repeatedly, or makes abnormal noise.',
    },
    {
      value: 'Power Failure',
      label: 'Power / Mainboard Failure',
      isCovered: true,
      description: 'Device will not power on, shuts down unexpectedly, or has charging/power-board symptoms.',
    },
    {
      value: 'Water Leakage',
      label: 'Water Leakage',
      isCovered: true,
      description: 'Water leaks, drainage problems, or abnormal frost/water buildup.',
    },
    {
      value: 'Noise',
      label: 'Abnormal Noise',
      isCovered: true,
      description: 'Unusual operating noise, vibration, grinding, or rattling under normal use.',
    },
    {
      value: 'Improper Voltage',
      label: 'Improper Voltage Damage (Not covered)',
      isCovered: false,
      description: 'Damage caused by wrong or unstable power supply.',
    },
    {
      value: 'Physical Damage',
      label: 'Physical Damage (Not covered)',
      isCovered: false,
      description: 'Cracks, dents, drops, impact damage, or broken exterior/panel.',
    },
  ],
  'Washing Machine': [
    {
      value: 'Motor Failure',
      label: 'Motor / Spin Failure',
      isCovered: true,
      description: 'Motor, drum, spin, or motion mechanism does not work correctly.',
    },
    {
      value: 'Water Leakage',
      label: 'Water Leakage',
      isCovered: true,
      description: 'Water leaks, drainage problems, or abnormal frost/water buildup.',
    },
    {
      value: 'Power Failure',
      label: 'Power / Mainboard Failure',
      isCovered: true,
      description: 'Device will not power on, shuts down unexpectedly, or has charging/power-board symptoms.',
    },
    {
      value: 'Mechanical Failure',
      label: 'Mechanical Failure',
      isCovered: true,
      description: 'Internal mechanical parts, rollers, bearings, or fuser mechanisms fail.',
    },
    {
      value: 'Noise',
      label: 'Abnormal Noise',
      isCovered: true,
      description: 'Unusual operating noise, vibration, grinding, or rattling under normal use.',
    },
    {
      value: 'Foreign Object Damage',
      label: 'Foreign Object Damage (Not covered)',
      isCovered: false,
      description: 'Foreign objects or misuse caused the failure.',
    },
    {
      value: 'Pest Damage',
      label: 'Pest / Rodent Damage (Not covered)',
      isCovered: false,
      description: 'Damage caused by insects, rodents, or pests.',
    },
  ],
  'Air Conditioner': [
    {
      value: 'Cooling Failure',
      label: 'Cooling Failure',
      isCovered: true,
      description: 'Cooling performance is weak or unavailable under normal operation.',
    },
    {
      value: 'Compressor Failure',
      label: 'Compressor Failure',
      isCovered: true,
      description: 'Compressor or outdoor unit does not run, stops repeatedly, or makes abnormal noise.',
    },
    {
      value: 'Water Leakage',
      label: 'Water Leakage',
      isCovered: true,
      description: 'Water leaks, drainage problems, or abnormal frost/water buildup.',
    },
    {
      value: 'Power Failure',
      label: 'Power / Mainboard Failure',
      isCovered: true,
      description: 'Device will not power on, shuts down unexpectedly, or has charging/power-board symptoms.',
    },
    {
      value: 'Noise',
      label: 'Abnormal Noise',
      isCovered: true,
      description: 'Unusual operating noise, vibration, grinding, or rattling under normal use.',
    },
    {
      value: 'Improper Installation',
      label: 'Improper Installation (Not covered)',
      isCovered: false,
      description: 'Issue caused by third-party or incorrect installation.',
    },
    {
      value: 'Power Surge',
      label: 'External Power Surge (Not covered)',
      isCovered: false,
      description: 'Damage caused by lightning, surge, or external electrical event.',
    },
  ],
  Camera: [
    {
      value: 'Lens Failure',
      label: 'Lens / Autofocus Failure',
      isCovered: true,
      description: 'Lens, zoom, aperture, or autofocus mechanism defect.',
    },
    {
      value: 'Sensor Failure',
      label: 'Sensor / Shutter Failure',
      isCovered: true,
      description: 'Image sensor, shutter, or imaging electronics defect.',
    },
    {
      value: 'Power Failure',
      label: 'Power / Mainboard Failure',
      isCovered: true,
      description: 'Device will not power on, shuts down unexpectedly, or has charging/power-board symptoms.',
    },
    {
      value: 'Display Failure',
      label: 'Display Failure',
      isCovered: true,
      description: 'Screen lines, flicker, dark display, touch/display malfunction without cracked glass.',
    },
    {
      value: 'Physical Damage',
      label: 'Physical Damage (Not covered)',
      isCovered: false,
      description: 'Cracks, dents, drops, impact damage, or broken exterior/panel.',
    },
    {
      value: 'Liquid Damage',
      label: 'Liquid / Water Damage (Not covered)',
      isCovered: false,
      description: 'Water, moisture, spill, or liquid ingress damage.',
    },
  ],
  Printer: [
    {
      value: 'Paper Feed Failure',
      label: 'Paper Feed Failure',
      isCovered: true,
      description: 'Paper feed, tray, roller, or jam problem under normal use.',
    },
    {
      value: 'Printhead Failure',
      label: 'Printhead / Print Quality Failure',
      isCovered: true,
      description: 'Print quality, printhead, missing color, or streaking problem using approved consumables.',
    },
    {
      value: 'Mechanical Failure',
      label: 'Mechanical Failure',
      isCovered: true,
      description: 'Internal mechanical parts, rollers, bearings, or fuser mechanisms fail.',
    },
    {
      value: 'Power Failure',
      label: 'Power / Mainboard Failure',
      isCovered: true,
      description: 'Device will not power on, shuts down unexpectedly, or has charging/power-board symptoms.',
    },
    {
      value: 'Non-OEM Ink Damage',
      label: 'Non-OEM Ink Damage (Not covered)',
      isCovered: false,
      description: 'Damage caused by non-approved ink, toner, or consumables.',
    },
    {
      value: 'Foreign Object Damage',
      label: 'Foreign Object Damage (Not covered)',
      isCovered: false,
      description: 'Foreign objects or misuse caused the failure.',
    },
  ],
  Other: [
    {
      value: 'Power Failure',
      label: 'Power / Mainboard Failure',
      isCovered: true,
      description: 'Device will not power on, shuts down unexpectedly, or has charging/power-board symptoms.',
    },
    {
      value: 'Operational Failure',
      label: 'Operational Failure',
      isCovered: true,
      description: 'The product cannot perform its main designed function.',
    },
    {
      value: 'Internal Component Defect',
      label: 'Internal Component Defect',
      isCovered: true,
      description: 'Internal electronic component or PCB defect under normal use.',
    },
    {
      value: 'Physical Damage',
      label: 'Physical Damage (Not covered)',
      isCovered: false,
      description: 'Cracks, dents, drops, impact damage, or broken exterior/panel.',
    },
    {
      value: 'Liquid Damage',
      label: 'Liquid / Water Damage (Not covered)',
      isCovered: false,
      description: 'Water, moisture, spill, or liquid ingress damage.',
    },
  ],
}

const ENGLISH_FAULT_CATEGORY_TEXT = {
  'Display Failure': ['Display Failure', 'Screen lines, flicker, dark display, touch/display malfunction without cracked glass.'],
  'Power Failure': ['Power / Mainboard Failure', 'Device will not power on, shuts down unexpectedly, or has charging/power-board symptoms.'],
  'Battery Problem': ['Battery / Charging Problem', 'Battery drains abnormally, will not charge, overheats during charging, or is swollen.'],
  'Keyboard & Trackpad Failure': ['Keyboard / Trackpad Failure', 'Keys, touchpad, or pointing controls stop responding during normal use.'],
  Overheating: ['Overheating / Fan Issue', 'Fan noise, fan not spinning, or device shuts down because of abnormal heat.'],
  'Connectivity Issue': ['Connectivity / Port Issue', 'Wi-Fi, Bluetooth, cellular, USB, HDMI, LAN, or other ports fail under normal use.'],
  'Audio Failure': ['Audio / Speaker / Microphone Failure', 'Speaker, microphone, or audio output is distorted or unavailable.'],
  'Physical Damage': ['Physical Damage', 'Cracks, dents, drops, impact damage, or broken exterior/panel.'],
  'Liquid Damage': ['Liquid / Water Damage', 'Water, moisture, spill, or liquid ingress damage.'],
  'Camera Failure': ['Camera Failure', 'Camera, autofocus, lens, or camera sensor defect.'],
  'Cooling Failure': ['Cooling Failure', 'Cooling performance is weak or unavailable under normal operation.'],
  'Compressor Failure': ['Compressor Failure', 'Compressor or outdoor unit does not run, stops repeatedly, or makes abnormal noise.'],
  'Water Leakage': ['Water Leakage', 'Water leaks, drainage problems, or abnormal frost/water buildup.'],
  Noise: ['Abnormal Noise', 'Unusual operating noise, vibration, grinding, or rattling under normal use.'],
  'Improper Voltage': ['Improper Voltage Damage', 'Damage caused by wrong or unstable power supply.'],
  'Motor Failure': ['Motor / Spin Failure', 'Motor, drum, spin, or motion mechanism does not work correctly.'],
  'Mechanical Failure': ['Mechanical Failure', 'Internal mechanical parts, rollers, bearings, or fuser mechanisms fail.'],
  'Foreign Object Damage': ['Foreign Object Damage', 'Foreign objects or misuse caused the failure.'],
  'Pest Damage': ['Pest / Rodent Damage', 'Damage caused by insects, rodents, or pests.'],
  'Improper Installation': ['Improper Installation', 'Issue caused by third-party or incorrect installation.'],
  'Power Surge': ['External Power Surge', 'Damage caused by lightning, surge, or external electrical event.'],
  'Electrical Surge': ['Electrical Surge', 'Damage caused by lightning or excessive external voltage.'],
  'Lens Failure': ['Lens / Autofocus Failure', 'Lens, zoom, aperture, or autofocus mechanism defect.'],
  'Sensor Failure': ['Sensor / Shutter Failure', 'Image sensor, shutter, or imaging electronics defect.'],
  'Paper Feed Failure': ['Paper Feed Failure', 'Paper feed, tray, roller, or jam problem under normal use.'],
  'Printhead Failure': ['Printhead / Print Quality Failure', 'Print quality, printhead, missing color, or streaking problem using approved consumables.'],
  'Non-OEM Ink Damage': ['Non-OEM Ink Damage', 'Damage caused by non-approved ink, toner, or consumables.'],
  'Operational Failure': ['Operational Failure', 'The product cannot perform its main designed function.'],
  'Internal Component Defect': ['Internal Component Defect', 'Internal electronic component or PCB defect under normal use.'],
  Other: ['Other', 'Select this when none of the listed categories match. A short description is required.'],
}

function toEnglishFaultCategory(category) {
  const [label, description] = ENGLISH_FAULT_CATEGORY_TEXT[category.value] || [category.value, category.description]
  return {
    ...category,
    label: category.isCovered === false ? `${label} (Not covered)` : label,
    description,
  }
}

export function getFaultCategoriesForProduct(category) {
  const normalized = category ? category.trim() : 'Other'
  const base = (
    FAULT_CATEGORIES_BY_PRODUCT_CATEGORY[normalized] ||
    FAULT_CATEGORIES_BY_PRODUCT_CATEGORY.Other
  )
  const mapped = base.map(toEnglishFaultCategory)
  if (!mapped.some((item) => item.value === 'Other')) {
    mapped.push(toEnglishFaultCategory({ value: 'Other', label: 'Other', isCovered: true, description: '' }))
  }
  return mapped
}




export const DEMO_USERS = [
  {
    id: 1,
    user_code: 'CUS0001',
    full_name: 'Bui Ngoc Mai',
    email: 'ngoc.mai07@example.com',
    phone: '0912345678',
    address: '123 Kim Ma, Ba Dinh, Hanoi',
  },
  {
    id: 2,
    user_code: 'CUS0002',
    full_name: 'Nguyen Van An',
    email: 'an.nguyen@example.com',
    phone: '0987654321',
    address: '45 Le Duan, District 1, Ho Chi Minh City',
  },
  {
    id: 3,
    user_code: 'CUS0003',
    full_name: 'Tran Thi Lan',
    email: 'lan.tran@example.com',
    phone: '0901234567',
    address: '78 Tran Phu, Hai Chau, Da Nang',
  },
  {
    id: 4,
    user_code: 'CUS0004',
    full_name: 'Le Hoang Nam',
    email: 'nam.le@example.com',
    phone: '0934567890',
    address: '12 Nguyen Thi Minh Khai, Hue',
  },
]

export const DEMO_CATALOG = [
  {
    id: 1,
    catalog_code: 'CAT-NB14',
    product_name: 'NovaBook 14 Ultra',
    category: 'Laptop',
    brand: 'NovaTech',
    model_number: 'NB14-2026',
    standard_warranty_months: 24,
    warranty_provider: 'NovaTech Official Care',
  },
  {
    id: 2,
    catalog_code: 'CAT-TPT14',
    product_name: 'ThinkPad T14 Gen 4',
    category: 'Laptop',
    brand: 'Lenovo',
    model_number: '21HD0001US',
    standard_warranty_months: 24,
    warranty_provider: 'Lenovo Premier Support',
  },
  {
    id: 3,
    catalog_code: 'CAT-S24U',
    product_name: 'Galaxy S24 Ultra',
    category: 'Smartphone',
    brand: 'Samsung',
    model_number: 'SM-S928B',
    standard_warranty_months: 12,
    warranty_provider: 'Samsung Care+',
  },
  {
    id: 4,
    catalog_code: 'CAT-U2724D',
    product_name: 'UltraSharp 27 4K Monitor',
    category: 'Monitor',
    brand: 'Dell',
    model_number: 'U2724D',
    standard_warranty_months: 36,
    warranty_provider: 'Dell Advanced Exchange',
  },
  {
    id: 5,
    catalog_code: 'CAT-LJ4103',
    product_name: 'LaserJet Pro MFP 4103fdw',
    category: 'Printer',
    brand: 'HP',
    model_number: '4103fdw',
    standard_warranty_months: 12,
    warranty_provider: 'HP Commercial Support',
  },
]

export const DEMO_SOLD_PRODUCTS = [
  {
    id: 1,
    product_code: 'AX26-00001',
    user_id: 1,
    catalog_id: 1,
    product_name: 'NovaBook 14 Ultra',
    brand: 'NovaTech',
    model_number: 'NB14-2026',
    serial_number: 'NB142026-00001',
    purchase_date: '2026-07-17',
    purchase_price: 1299.0,
    retailer: 'NovaStore Central',
    invoice_number: 'INV-2026-9021',
    warranty_months: 24,
    warranty_start_date: '2026-07-17',
    warranty_expiry_date: '2028-07-16',
    extended_warranty: false,
    status: 'active',
  },
  {
    id: 2,
    product_code: 'AX26-00002',
    user_id: 2,
    catalog_id: 2,
    product_name: 'ThinkPad T14 Gen 4',
    brand: 'Lenovo',
    model_number: '21HD0001US',
    serial_number: 'PF4X9812',
    purchase_date: '2025-11-10',
    purchase_price: 1450.0,
    retailer: 'TechWorld Store',
    invoice_number: 'INV-2025-4491',
    warranty_months: 24,
    warranty_start_date: '2025-11-10',
    warranty_expiry_date: '2027-11-09',
    extended_warranty: false,
    status: 'active',
  },
  {
    id: 3,
    product_code: 'AX26-00003',
    user_id: 3,
    catalog_id: 3,
    product_name: 'Galaxy S24 Ultra',
    brand: 'Samsung',
    model_number: 'SM-S928B',
    serial_number: 'R5CW109K',
    purchase_date: '2024-03-01',
    purchase_price: 1199.0,
    retailer: 'PhoneMart Flagship',
    invoice_number: 'INV-2024-1182',
    warranty_months: 12,
    warranty_start_date: '2024-03-01',
    warranty_expiry_date: '2025-02-28',
    extended_warranty: false,
    status: 'expired',
  },
  {
    id: 4,
    product_code: 'AX26-00004',
    user_id: 1,
    catalog_id: 4,
    product_name: 'UltraSharp 27 4K Monitor',
    brand: 'Dell',
    model_number: 'U2724D',
    serial_number: 'CN-0M27D-128',
    purchase_date: '2026-01-15',
    purchase_price: 620.0,
    retailer: 'DigiPro Electronics',
    invoice_number: 'INV-2026-0312',
    warranty_months: 36,
    warranty_start_date: '2026-01-15',
    warranty_expiry_date: '2029-01-14',
    extended_warranty: true,
    status: 'active',
  },
  {
    id: 5,
    product_code: 'AX26-00005',
    user_id: 2,
    catalog_id: 5,
    product_name: 'LaserJet Pro MFP 4103fdw',
    brand: 'HP',
    model_number: '4103fdw',
    serial_number: 'VNB3K9821',
    purchase_date: '2025-06-20',
    purchase_price: 480.0,
    retailer: 'OfficeDepot Vietnam',
    invoice_number: 'INV-2025-7721',
    warranty_months: 12,
    warranty_start_date: '2025-06-20',
    warranty_expiry_date: '2026-06-19',
    extended_warranty: false,
    status: 'active',
  },
]


export function lookupSoldProduct(productCode) {
  if (!productCode) return null
  const cleaned = productCode.trim().toUpperCase()
  const sold = DEMO_SOLD_PRODUCTS.find(
    (p) => p.product_code.toUpperCase() === cleaned || p.serial_number.toUpperCase() === cleaned
  )
  if (!sold) return null

  const user = DEMO_USERS.find((u) => u.id === sold.user_id)
  const catalog = DEMO_CATALOG.find((c) => c.id === sold.catalog_id)

  return {
    ...sold,
    user_code: user?.user_code || 'CUS0001',
    customer_name: user?.full_name || 'Bui Ngoc Mai',
    customer_email: user?.email || 'ngoc.mai07@example.com',
    customer_phone: user?.phone || '0912345678',
    customer_address: user?.address || 'Hanoi',
    category: catalog?.category || 'Electronics',
    standard_warranty_months: catalog?.standard_warranty_months || 24,
    warranty_provider: catalog?.warranty_provider || 'AssureX Official Care',
  }
}





export function derive14Features(input, product) {
  const now = new Date()
  const incidentDate = input?.incident_date ? new Date(input.incident_date) : now
  const purchaseDate = product?.purchase_date ? new Date(product.purchase_date) : null
  const expiryDate = product?.warranty_expiry_date ? new Date(product.warranty_expiry_date) : null


  const diffTime = now.getTime() - incidentDate.getTime()
  const ClaimReportingDelayDays = Math.max(0, Math.floor(diffTime / (1000 * 60 * 60 * 24)))


  let WarrantyRemainingDays = 180
  if (expiryDate) {
    const remainingTime = expiryDate.getTime() - now.getTime()
    WarrantyRemainingDays = Math.floor(remainingTime / (1000 * 60 * 60 * 24))
  }


  const ClaimReportingWithinPeriod = ClaimReportingDelayDays <= 30 ? 'Yes' : 'No'


  const desc = `${input?.problem_category || ''} ${input?.fault_description || ''}`.toLowerCase()
  const isExcluded =
    /water|liquid|dropped|falling|shattered|broken screen|physical impact|spilled|tampered|cracked glass|spill|surge|pest|foreign object|non-oem|improper/.test(
      desc
    )
  const FaultCovered = isExcluded ? 'No' : 'Yes'


  let RepairAuthorized = 'Not Applicable'
  if (input?.previous_repair === 'Yes') {
    const centre = (input?.repair_centre || '').toLowerCase()
    const isAuthorizedCentre =
      /assurex|official|authorized|authorised|lenovo|dell|samsung|apple|hp|premier/.test(centre)
    RepairAuthorized = isAuthorizedCentre ? 'Yes' : 'No'
  }


  const SerialNumberMatch = product?.serial_number ? 'Yes' : 'No'


  const ProductModelConsistent = product?.model_number ? 'Yes' : 'No'


  const OCRConfidence = product ? 0.95 : 0.60


  const OCRQualityBand = OCRConfidence >= 0.85 ? 'High' : OCRConfidence >= 0.7 ? 'Medium' : 'Low'



  const evidenceAnswers = [
    input?.purchase_invoice_available,
    input?.serial_image_available,
    input?.fault_evidence_available,
    ...(input?.previous_repair === 'Yes' ? [input?.repair_report_available] : []),
  ]
  const MissingDocumentCount = evidenceAnswers.filter((value) => value !== 'Yes').length
  const RequiredDocumentsComplete = MissingDocumentCount === 0 ? 'Yes' : 'No'


  const DuplicateClaimIndicator = 'No'


  let ContradictionIndicator = 'No'
  if (purchaseDate && incidentDate < purchaseDate) {
    ContradictionIndicator = 'Yes'
  }
  if (incidentDate > now) {
    ContradictionIndicator = 'Yes'
  }


  const ProductIdentityMatch =
    SerialNumberMatch === 'Yes' && ProductModelConsistent === 'Yes' ? 'Yes' : 'No'

  return {
    RepairAuthorized,
    SerialNumberMatch,
    ProductModelConsistent,
    DuplicateClaimIndicator,
    ContradictionIndicator,
    OCRConfidence,
    ClaimReportingDelayDays,
    WarrantyRemainingDays,
    ClaimReportingWithinPeriod,
    FaultCovered,
    RequiredDocumentsComplete,
    MissingDocumentCount,
    ProductIdentityMatch,
    OCRQualityBand,
  }
}





export function predictModelV3(features) {

  if (
    features.FaultCovered === 'No' ||
    features.WarrantyRemainingDays < 0 ||
    features.ProductIdentityMatch === 'No' ||
    features.ContradictionIndicator === 'Yes'
  ) {
    let reason = 'Claim ineligible under policy terms'
    if (features.FaultCovered === 'No')
      reason = 'Defect excluded: physical impact, liquid ingress, or user abuse'
    else if (features.WarrantyRemainingDays < 0)
      reason = `Warranty expired (${Math.abs(features.WarrantyRemainingDays)} days ago)`
    else if (features.ProductIdentityMatch === 'No')
      reason = 'Serial number or product model discrepancy'
    else if (features.ContradictionIndicator === 'Yes')
      reason = 'Timeline contradiction detected in dates'

    return {
      prediction: 'NOT_WARRANTY',
      confidence: 0.98,
      reason,
      advice: 'Defect is excluded or policy is expired. Claim rejected by policy rules.',
    }
  }


  if (
    features.MissingDocumentCount > 0 ||
    features.OCRConfidence < 0.8 ||
    features.RepairAuthorized === 'No' ||
    features.ClaimReportingWithinPeriod === 'No'
  ) {
    let reason = 'Manual inspection required'
    if (features.RepairAuthorized === 'No')
      reason = 'Prior unauthorized third-party repair detected'
    else if (features.MissingDocumentCount > 0)
      reason = `${features.MissingDocumentCount} required document(s) missing`
    else if (features.ClaimReportingWithinPeriod === 'No')
      reason = `Reporting delay exceeds 30-day window (${features.ClaimReportingDelayDays} days)`
    else if (features.OCRConfidence < 0.8)
      reason = 'Low OCR document scan confidence'

    return {
      prediction: 'REVIEW_REQUIRED',
      confidence: 0.78,
      reason,
      advice:
        'Flagged for human reviewer examination due to verification discrepancy or incomplete documents.',
    }
  }


  return {
    prediction: 'WARRANTY',
    confidence: 0.95,
    reason: 'Standard OEM manufacturing defect verified under active warranty coverage',
    advice:
      'High model confidence. Claim verified eligible under standard warranty coverage.',
  }
}




export const claim14FieldGroups = [
  {
    title: 'Product & Identity Verification',
    description: 'Verify product identity, serial number consistency, and equipment authenticity',
    fields: [
      {
        name: 'ProductIdentityMatch',
        label: 'Product Identity Match',
        type: 'select',
        options: ['Yes', 'No'],
        help: 'Combined verification of serial, model, OCR and database record',
      },
      {
        name: 'SerialNumberMatch',
        label: 'Serial Number Match',
        type: 'select',
        options: ['Yes', 'No', 'Unknown'],
        help: 'Device serial tag OCR matching sold_products.serial_number',
      },
      {
        name: 'ProductModelConsistent',
        label: 'Product Model Consistent',
        type: 'select',
        options: ['Yes', 'No'],
        help: 'Product model in evidence matches catalog model specifications',
      },
    ],
  },
  {
    title: 'Warranty Status & Coverage',
    description: 'Remaining warranty period, policy coverage scope, and reporting timeliness',
    fields: [
      {
        name: 'WarrantyRemainingDays',
        label: 'Warranty Remaining Days',
        type: 'number',
        help: 'WarrantyExpiryDate − ClaimCreatedAt (>= 0 active, < 0 expired)',
      },
      {
        name: 'FaultCovered',
        label: 'Fault Covered by Policy',
        type: 'select',
        options: ['Yes', 'No', 'Unknown'],
        help: 'Manufacturer hardware defect (Yes) vs accidental damage / liquid (No)',
      },
      {
        name: 'ClaimReportingDelayDays',
        label: 'Reporting Delay Days',
        type: 'number',
        help: 'ClaimCreatedAt − IncidentDate (days elapsed)',
      },
      {
        name: 'ClaimReportingWithinPeriod',
        label: 'Claim Reporting Within Period',
        type: 'select',
        options: ['Yes', 'No', 'Unknown'],
        help: 'Claim reported within the statutory 30-day window',
      },
    ],
  },
  {
    title: 'Repair History & Integrity',
    description: 'Service center authorization and fraud/anomaly indicators',
    fields: [
      {
        name: 'RepairAuthorized',
        label: 'Repair Authorized',
        type: 'select',
        options: ['Yes', 'No', 'Not Applicable', 'Unknown'],
        help: 'Prior service performed by authorized center with valid repair report',
      },
      {
        name: 'DuplicateClaimIndicator',
        label: 'Duplicate Claim Indicator',
        type: 'select',
        options: ['No', 'Yes'],
        help: 'Automated detection flag for duplicate claim filings',
      },
      {
        name: 'ContradictionIndicator',
        label: 'Contradiction Indicator',
        type: 'select',
        options: ['No', 'Yes'],
        help: 'Discrepancies detected between incident dates, purchase dates, and records',
      },
    ],
  },
  {
    title: 'Documents & OCR Quality',
    description: 'Document completeness and automated OCR extraction confidence',
    fields: [
      {
        name: 'RequiredDocumentsComplete',
        label: 'Required Documents Complete',
        type: 'select',
        options: ['Yes', 'No', 'Unknown'],
        help: 'Mandatory proof of purchase and defect evidence files provided',
      },
      {
        name: 'MissingDocumentCount',
        label: 'Missing Document Count',
        type: 'number',
        help: 'Count of mandatory documentation items missing',
      },
      {
        name: 'OCRConfidence',
        label: 'OCR / Document Confidence Score',
        type: 'number',
        help: 'Document text recognition and invoice stamp verification score (0.0 - 1.0)',
      },
      {
        name: 'OCRQualityBand',
        label: 'OCR Quality Band',
        type: 'select',
        options: ['High', 'Medium', 'Low', 'Missing'],
        help: 'Clarity rating: High (>= 0.85), Medium (0.70 - 0.84), Low (< 0.70)',
      },
    ],
  },
]

export const claimFieldGroups = claim14FieldGroups




export const CLAIM_PRESETS = [
  {
    id: 'valid',
    badge: 'Valid',
    name: 'Valid Claim (Standard OEM)',
    tone: 'success',
    description:
      'NovaBook 14, active warranty, screen flicker defect, complete evidence. Derives active V3 features -> Predicts WARRANTY.',
    customer: {
      customer_name: 'Bui Ngoc Mai',
      email: 'ngoc.mai07@example.com',
      phone_number: '0912345678',
    },
    product_code: 'AX26-00001',
    claim: {
      incident_date: new Date(Date.now() - 3 * 86400000).toISOString().split('T')[0],
      problem_category: 'Display Failure',
      fault_description:
        'Screen displays horizontal flickering lines continuously upon boot. No physical drop, impact, or liquid exposure.',
      previous_repair: 'No',
      repair_centre: '',
      repair_date: '',
    },
    evidence: {
      purchase_invoice: { filename: 'Invoice_NovaStore_9021.pdf', size: '245 KB' },
      serial_image: { filename: 'Serial_Tag_NB142026.jpg', size: '1.2 MB' },
      fault_evidence: { filename: 'Screen_Flicker_Video.mp4', size: '4.8 MB' },
      repair_report: null,
    },
  },
  {
    id: 'review',
    badge: 'Review',
    name: 'Manual Review (Requires Examination)',
    tone: 'warning',
    description:
      'ThinkPad T14, prior 3rd-party repair, missing repair report. Derives RepairAuthorized: No -> Predicts REVIEW_REQUIRED.',
    customer: {
      customer_name: 'Nguyen Van An',
      email: 'an.nguyen@example.com',
      phone_number: '0987654321',
    },
    product_code: 'AX26-00002',
    claim: {
      incident_date: new Date(Date.now() - 10 * 86400000).toISOString().split('T')[0],
      problem_category: 'Keyboard & Trackpad Failure',
      fault_description:
        'Keyboard keys (E, R, T) intermittently stop responding during normal typing. Device previously serviced at local third-party shop.',
      previous_repair: 'Yes',
      repair_centre: 'FastFix Independent Tech Shop',
      repair_date: new Date(Date.now() - 60 * 86400000).toISOString().split('T')[0],
    },
    evidence: {
      purchase_invoice: { filename: 'TechWorld_Receipt_4491.pdf', size: '310 KB' },
      serial_image: { filename: 'ThinkPad_Serial_Photo.jpg', size: '980 KB' },
      fault_evidence: { filename: 'Keyboard_Tester_Log.png', size: '640 KB' },
      repair_report: null,
    },
  },
  {
    id: 'invalid',
    badge: 'Reject',
    name: 'Invalid Claim (Policy Exclusion / Expired)',
    tone: 'danger',
    description:
      'Galaxy S24 Ultra, expired warranty, liquid ingress/water damage. Derives FaultCovered: No -> Predicts NOT_WARRANTY.',
    customer: {
      customer_name: 'Tran Thi Lan',
      email: 'lan.tran@example.com',
      phone_number: '0901234567',
    },
    product_code: 'AX26-00003',
    claim: {
      incident_date: new Date(Date.now() - 45 * 86400000).toISOString().split('T')[0],
      problem_category: 'Liquid Damage',
      fault_description:
        'Phone fell into water pool, screen shattered with liquid ingress behind display glass. Unit fails to power on.',
      previous_repair: 'No',
      repair_centre: '',
      repair_date: '',
    },
    evidence: {
      purchase_invoice: { filename: 'PhoneMart_Receipt_1182.pdf', size: '180 KB' },
      serial_image: { filename: 'Serial_Backplate.jpg', size: '890 KB' },
      fault_evidence: { filename: 'Liquid_Damage_Photo.jpg', size: '1.5 MB' },
      repair_report: null,
    },
  },
]
