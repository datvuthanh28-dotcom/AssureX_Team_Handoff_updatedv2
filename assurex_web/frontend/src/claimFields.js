// ASSUREX CLAIM ENGINE - MODEL V3 DEFINITIONS & FEATURE ENGINEERING HANDOFF
// Matching Submit Claim form, user/product database, and 14 active Model V3 features

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

// ------------------------------------------------------------------------------
// FAULT CATEGORIES CUSTOMIZED BY REGISTERED PRODUCT CATEGORY
// ------------------------------------------------------------------------------
export const FAULT_CATEGORIES_BY_PRODUCT_CATEGORY = {
  Laptop: [
    {
      value: 'Display Failure',
      label: 'Màn hình & Hiển thị (Display Failure)',
      isCovered: true,
      description: 'Sọc màn hình, đốm sáng, chớp nháy, tối đen không lên hình (kính không nứt vỡ).',
    },
    {
      value: 'Power Failure',
      label: 'Nguồn & Bo mạch chính (Power / Motherboard Failure)',
      isCovered: true,
      description: 'Không lên nguồn, máy tự sập nguồn đột ngột, chập chờn khi cắm nguồn sạc.',
    },
    {
      value: 'Battery Problem',
      label: 'Pin & Hệ thống sạc (Battery & Charging Issue)',
      isCovered: true,
      description: 'Chai pin nhanh bất thường, báo lỗi không nhận sạc, phồng pin.',
    },
    {
      value: 'Keyboard & Trackpad Failure',
      label: 'Bàn phím & Touchpad (Keyboard & Touchpad Defect)',
      isCovered: true,
      description: 'Liệt phím, kẹt phím, touchpad loạn cảm ứng hoặc không nhận chuột.',
    },
    {
      value: 'Overheating',
      label: 'Hệ thống tản nhiệt (Overheating / Fan Noise)',
      isCovered: true,
      description: 'Quạt tản nhiệt kêu to bất thường, quạt không quay, máy quá nhiệt tự ngắt.',
    },
    {
      value: 'Connectivity Issue',
      label: 'Cổng kết nối & Wi-Fi (Connectivity / Ports Issue)',
      isCovered: true,
      description: 'Mất kết nối Wi-Fi/Bluetooth, hỏng cổng Type-C, USB hoặc HDMI.',
    },
    {
      value: 'Audio Failure',
      label: 'Âm thanh & Loa (Audio & Speaker Failure)',
      isCovered: true,
      description: 'Loa rè, méo tiếng, mất âm thanh hoàn toàn.',
    },
    {
      value: 'Physical Damage',
      label: 'Rơi vỡ / Va đập vật lý (Physical Impact / Screen Crack) [Không BH]',
      isCovered: false,
      description: 'Nứt vỡ màn hình, móp méo vỏ máy do ngoại lực hoặc rơi rớt.',
    },
    {
      value: 'Liquid Damage',
      label: 'Vào nước / Đổ chất lỏng (Liquid / Water Ingress) [Không BH]',
      isCovered: false,
      description: 'Đổ nước, ngấm chất lỏng vào bàn phím hoặc bo mạch máy.',
    },
  ],
  Smartphone: [
    {
      value: 'Display Failure',
      label: 'Màn hình & Cảm ứng (Display & Touchscreen Failure)',
      isCovered: true,
      description: 'Loạn cảm ứng, chết điểm cảm ứng, sọc màn hình, chảy mực màn trong (kính không nứt).',
    },
    {
      value: 'Power Failure',
      label: 'Nguồn & Khởi động (Power & Bootloop Failure)',
      isCovered: true,
      description: 'Treo logo, sập nguồn liên tục, bật nguồn không rung/không khởi động.',
    },
    {
      value: 'Battery Problem',
      label: 'Pin & Cổng sạc (Battery & Charging Port)',
      isCovered: true,
      description: 'Sạc không vào điện, nóng máy bất thường khi sạc, sụt pin nhanh.',
    },
    {
      value: 'Camera Failure',
      label: 'Camera & Lấy nét (Camera / Lens Defect)',
      isCovered: true,
      description: 'Camera mờ, rung ống kính chống rung OIS, lỗi cảm biến camera.',
    },
    {
      value: 'Connectivity Issue',
      label: 'Sóng & Kết nối (Cellular / Wi-Fi / Bluetooth)',
      isCovered: true,
      description: 'Mất sóng di động, không nhận thẻ SIM, mất kết nối Wi-Fi hoặc Bluetooth.',
    },
    {
      value: 'Audio Failure',
      label: 'Loa & Microphone (Speaker & Mic Failure)',
      isCovered: true,
      description: 'Không nghe thấy người gọi, mic không thu âm, loa ngoài bị rè/mất tiếng.',
    },
    {
      value: 'Physical Damage',
      label: 'Rơi vỡ nứt kính (Screen / Back Glass Crack) [Không BH]',
      isCovered: false,
      description: 'Nứt vỡ mặt kính trước hoặc kính lưng do rơi rớt va đập.',
    },
    {
      value: 'Liquid Damage',
      label: 'Ngấm nước / Ẩm chân sạc (Liquid Ingress / Moisture) [Không BH]',
      isCovered: false,
      description: 'Báo lỗi phát hiện độ ẩm cổng sạc, máy rơi nước.',
    },
  ],
  Tablet: [
    {
      value: 'Display Failure',
      label: 'Màn hình & Cảm ứng (Display & Touchscreen Failure)',
      isCovered: true,
      description: 'Loạn cảm ứng, đốm sáng, sọc hiển thị, không nhận bút cảm ứng.',
    },
    {
      value: 'Power Failure',
      label: 'Nguồn & Bo mạch (Power Failure)',
      isCovered: true,
      description: 'Không khởi động được, máy tự tắt nguồn.',
    },
    {
      value: 'Battery Problem',
      label: 'Pin & Cổng sạc (Battery & Charging Issue)',
      isCovered: true,
      description: 'Không nhận sạc, pin tụt nhanh, phồng pin.',
    },
    {
      value: 'Connectivity Issue',
      label: 'Kết nối Wi-Fi & Bluetooth (Connectivity Issue)',
      isCovered: true,
      description: 'Không dò được mạng Wi-Fi, mất kết nối thiết bị ngoại vi.',
    },
    {
      value: 'Physical Damage',
      label: 'Rơi vỡ nứt màn hình (Physical / Screen Crack) [Không BH]',
      isCovered: false,
      description: 'Màn hình bị nứt vỡ do va chạm vật lý.',
    },
    {
      value: 'Liquid Damage',
      label: 'Vào nước / Đổ chất lỏng (Liquid Damage) [Không BH]',
      isCovered: false,
      description: 'Thiết bị bị ngấm nước hoặc dung dịch lỏng.',
    },
  ],
  Television: [
    {
      value: 'Display Failure',
      label: 'Màn hình & Panel hiển thị (Panel & Display Defect)',
      isCovered: true,
      description: 'Kẻ sọc dọc/ngang panel, đốm đen, chớp nháy liên tục, mất đèn nền LED (có tiếng mất hình).',
    },
    {
      value: 'Power Failure',
      label: 'Bo nguồn & Khởi động (Power Board Failure)',
      isCovered: true,
      description: 'Không có đèn báo nguồn, bật không lên, chớp đèn đỏ báo lỗi bo nguồn.',
    },
    {
      value: 'Audio Failure',
      label: 'Âm thanh & Loa (Audio & Speaker Failure)',
      isCovered: true,
      description: 'Loa rè, méo tiếng, mất tiếng hoàn toàn khi xem TV.',
    },
    {
      value: 'Connectivity Issue',
      label: 'Cổng tín hiệu & Kết nối (Signal & Port Issue)',
      isCovered: true,
      description: 'Không nhận cổng HDMI, không kết nối được mạng LAN hoặc Wi-Fi.',
    },
    {
      value: 'Physical Damage',
      label: 'Nứt vỡ Panel do va đập (Panel Impact / Crack) [Không BH]',
      isCovered: false,
      description: 'Panel màn hình bị nứt vỡ do va đập ngoại lực.',
    },
    {
      value: 'Electrical Surge',
      label: 'Sét đánh / Sốc điện quá áp (Power Surge / Lightning) [Không BH]',
      isCovered: false,
      description: 'Cháy nổ bo mạch do xung sét đánh hoặc nguồn điện ngoài tăng áp đột ngột.',
    },
  ],
  Monitor: [
    {
      value: 'Display Failure',
      label: 'Panel & Hiển thị (Panel & Display Defect)',
      isCovered: true,
      description: 'Sọc màn hình, chết điểm ảnh, chớp nháy, mất tín hiệu hiển thị.',
    },
    {
      value: 'Power Failure',
      label: 'Nguồn & Adapter (Power Failure)',
      isCovered: true,
      description: 'Màn hình không sáng đèn nguồn, bật không lên.',
    },
    {
      value: 'Connectivity Issue',
      label: 'Cổng DisplayPort / HDMI (Port Defect)',
      isCovered: true,
      description: 'Không nhận tín hiệu từ máy tính qua cáp HDMI / DisplayPort.',
    },
    {
      value: 'Physical Damage',
      label: 'Màn hình nứt vỡ do va đập (Screen Impact) [Không BH]',
      isCovered: false,
      description: 'Vỡ tấm nền do tác động ngoại lực.',
    },
  ],
  Refrigerator: [
    {
      value: 'Cooling Failure',
      label: 'Hệ thống làm lạnh (Cooling System Failure)',
      isCovered: true,
      description: 'Ngăn đông không đông đá, ngăn mát không đủ lạnh để bảo quản thực phẩm.',
    },
    {
      value: 'Compressor Failure',
      label: 'Máy nén / Block (Compressor Defect)',
      isCovered: true,
      description: 'Block máy nén không chạy, phát ra tiếng kêu gõ lớn bất thường.',
    },
    {
      value: 'Power Failure',
      label: 'Nguồn & Bảng điều khiển (Power & Control Board)',
      isCovered: true,
      description: 'Mất nguồn hoàn toàn, bảng điều khiển nhấp nháy báo lỗi cảm biến.',
    },
    {
      value: 'Water Leakage',
      label: 'Rò rỉ nước / Đóng tuyết bất thường (Water Leak / Frost)',
      isCovered: true,
      description: 'Đóng đá bít đường gió, rò rỉ nước ra đáy hoặc sàn tủ.',
    },
    {
      value: 'Noise',
      label: 'Tiếng ồn động cơ / Quạt gió (Excessive Noise)',
      isCovered: true,
      description: 'Quạt đối lưu kêu to, rung lắc mạnh khi vận hành.',
    },
    {
      value: 'Improper Voltage',
      label: 'Cháy do điện áp sai quy định (Improper Voltage Supply) [Không BH]',
      isCovered: false,
      description: 'Cháy nổ bo mạch hoặc block do cấp điện sai thông số kỹ thuật.',
    },
    {
      value: 'Physical Damage',
      label: 'Thủng dàn / Móp méo ngoại lực (Physical Damage) [Không BH]',
      isCovered: false,
      description: 'Thủng dàn lạnh do vật nhọn cạy đá, móp méo do va chạm mạnh.',
    },
  ],
  'Washing Machine': [
    {
      value: 'Motor Failure',
      label: 'Động cơ & Chế độ vắt (Motor & Spin Failure)',
      isCovered: true,
      description: 'Lồng giặt không quay, không vắt khô được quần áo.',
    },
    {
      value: 'Water Leakage',
      label: 'Rò rỉ nước & Cấp xả (Water Leak / Valve Defect)',
      isCovered: true,
      description: 'Không cấp nước, không xả nước hoặc chảy nước dưới đáy máy.',
    },
    {
      value: 'Power Failure',
      label: 'Bảng mạch điều khiển (Main PCB Board Failure)',
      isCovered: true,
      description: 'Liệt phím bấm, máy không nhận lệnh giặt, báo mã lỗi bo mạch.',
    },
    {
      value: 'Mechanical Failure',
      label: 'Rung lắc & Ổ bi giảm sóc (Bearing & Suspension Defect)',
      isCovered: true,
      description: 'Kêu rít lớn khi vắt, rung lắc chồm máy bất thường do hỏng thụt/bi.',
    },
    {
      value: 'Noise',
      label: 'Tiếng ồn cơ khí bất thường (Abnormal Operating Noise)',
      isCovered: true,
      description: 'Tiếng kêu va chạm kim loại trong lồng giặt trong chu trình hoạt động.',
    },
    {
      value: 'Foreign Object Damage',
      label: 'Kẹt dị vật / Giặt quá tải trọng lượng (Foreign Object / Overloading) [Không BH]',
      isCovered: false,
      description: 'Dị vật nhọn làm rách gioăng cao su hoặc giặt quá tải gây gãy chảng ba lồng giặt.',
    },
    {
      value: 'Pest Damage',
      label: 'Côn trùng / Chuột cắn phá (Pest / Rodent Damage) [Không BH]',
      isCovered: false,
      description: 'Đứt dây điện, hỏng van do chuột hoặc côn trùng xâm nhập cắn phá.',
    },
  ],
  'Air Conditioner': [
    {
      value: 'Cooling Failure',
      label: 'Khả năng làm lạnh (Cooling Performance Failure)',
      isCovered: true,
      description: 'Có gió thổi nhưng không lạnh, làm lạnh rất yếu, dàn lạnh đóng tuyết.',
    },
    {
      value: 'Compressor Failure',
      label: 'Cục nóng & Máy nén (Outdoor Unit & Compressor Defect)',
      isCovered: true,
      description: 'Cục nóng không chạy, quạt dàn nóng không quay, máy nén gằn ngắt liên tục.',
    },
    {
      value: 'Water Leakage',
      label: 'Dàn lạnh chảy nước (Indoor Unit Water Leakage)',
      isCovered: true,
      description: 'Máng nước bị tắc nghẽn hoặc chảy nước tràn ra tường/sàn phòng.',
    },
    {
      value: 'Power Failure',
      label: 'Mạch điện & Cảm biến (PCB Board & Sensor Issue)',
      isCovered: true,
      description: 'Đèn timer nhấp nháy báo lỗi bo mạch, máy không nhận tín hiệu remote.',
    },
    {
      value: 'Noise',
      label: 'Tiếng ồn quạt lồng sóc / Cục nóng (Excessive Operating Noise)',
      isCovered: true,
      description: 'Quạt lồng sóc bị cọ kêu rít hoặc cục nóng rung lắc gây ồn.',
    },
    {
      value: 'Improper Installation',
      label: 'Lỗi rò rỉ gas do lắp đặt sai kỹ thuật (Improper Installation) [Cần kiểm tra]',
      isCovered: false,
      description: 'Xì gas tại đầu tán rắc co, gập ống đồng do thao tác lắp đặt của thợ ngoài.',
    },
    {
      value: 'Power Surge',
      label: 'Chập cháy do nguồn điện ngoài (External Power Surge) [Không BH]',
      isCovered: false,
      description: 'Cháy nổ tụ và bo mạch biến tần do xung sét hoặc nguồn điện không đạt chuẩn.',
    },
  ],
  Camera: [
    {
      value: 'Lens Failure',
      label: 'Ống kính & Hệ thống lấy nét (Lens & Autofocus Failure)',
      isCovered: true,
      description: 'Kẹt zoom, động cơ AF không lấy nét, báo lỗi khẩu độ Err01/Err99.',
    },
    {
      value: 'Sensor Failure',
      label: 'Cảm biến ảnh & Màn trập (Sensor & Shutter Defect)',
      isCovered: true,
      description: 'Kẹt màn trập, xuất hiện vệt sọc hoặc điểm chết cảm biến trên ảnh chụp.',
    },
    {
      value: 'Power Failure',
      label: 'Nguồn & Mainboard (Power & Circuit Failure)',
      isCovered: true,
      description: 'Không khởi động được, máy tự tắt khi chụp, quá nóng khi quay phim.',
    },
    {
      value: 'Display Failure',
      label: 'Màn hình LCD & Kính ngắm (Display & EVF Defect)',
      isCovered: true,
      description: 'Màn hình bị đen, sọc hiển thị hoặc mất tín hiệu kính ngắm điện tử.',
    },
    {
      value: 'Physical Damage',
      label: 'Rơi vỡ va đập thấu kính (Lens Impact / Drop Damage) [Không BH]',
      isCovered: false,
      description: 'Nứt vỡ thấu kính, cong vênh ngàm hoặc móp thân máy do va chạm.',
    },
    {
      value: 'Liquid Damage',
      label: 'Ẩm mốc / Ngấm nước (Moisture / Fungus / Liquid) [Không BH]',
      isCovered: false,
      description: 'Cảm biến hoặc kính bị rễ tre nấm mốc do bảo quản ẩm, hoặc máy rơi nước.',
    },
  ],
  Printer: [
    {
      value: 'Paper Feed Failure',
      label: 'Kéo giấy & Khay nạp (Paper Feed & Roller Failure)',
      isCovered: true,
      description: 'Kẹt giấy liên tục, con lăn cao su không kéo giấy hoặc kéo nhiều tờ cùng lúc.',
    },
    {
      value: 'Printhead Failure',
      label: 'Đầu in & Chất lượng bản in (Printhead & Print Quality)',
      isCovered: true,
      description: 'Bản in bị sọc trắng, mất tia mực, mất màu (khi dùng mực in chính hãng).',
    },
    {
      value: 'Mechanical Failure',
      label: 'Cụm sấy & Cơ khí (Fuser & Mechanical Failure)',
      isCovered: true,
      description: 'Bản in bị sống mực, kẹt sấy, bánh răng hộp cơ kêu cạch cạch to bất thường.',
    },
    {
      value: 'Power Failure',
      label: 'Nguồn & Bo mạch kết nối (Power & Formatter Board)',
      isCovered: true,
      description: 'Không lên nguồn, máy tính không nhận diện cổng USB hoặc mạng LAN/Wi-Fi.',
    },
    {
      value: 'Non-OEM Ink Damage',
      label: 'Dùng mực không chính hãng / Tràn mực (Non-OEM Ink Damage) [Không BH]',
      isCovered: false,
      description: 'Tắc đầu in do mực ngoài, mực tràn làm chập bo nguồn hoặc đầu phun.',
    },
    {
      value: 'Foreign Object Damage',
      label: 'Dị vật rơi vào cụm cuốn (Foreign Object Obstruction) [Không BH]',
      isCovered: false,
      description: 'Ghim bấm, kẹp giấy rơi vào máy làm rách bao lụa cụm sấy.',
    },
  ],
  Other: [
    {
      value: 'Power Failure',
      label: 'Lỗi nguồn / Khởi động (Power / Startup Failure)',
      isCovered: true,
      description: 'Thiết bị không lên nguồn hoặc tự ngắt khi đang hoạt động.',
    },
    {
      value: 'Operational Failure',
      label: 'Lỗi chức năng hoạt động chính (Operational Failure)',
      isCovered: true,
      description: 'Thiết bị không thực hiện được tính năng thiết kế tiêu chuẩn.',
    },
    {
      value: 'Internal Component Defect',
      label: 'Lỗi bo mạch điện tử bên trong (Internal PCB Defect)',
      isCovered: true,
      description: 'Cháy hỏng linh kiện điện tử nguyên nhân do lỗi sản xuất linh kiện.',
    },
    {
      value: 'Physical Damage',
      label: 'Rơi vỡ / Va đập ngoại lực (Physical Impact Damage) [Không BH]',
      isCovered: false,
      description: 'Hỏng hóc, nứt vỡ do tác động ngoại lực.',
    },
    {
      value: 'Liquid Damage',
      label: 'Vào nước / Ẩm ướt (Liquid / Water Ingress) [Không BH]',
      isCovered: false,
      description: 'Chập hỏng do ngấm nước hoặc môi trường ẩm ướt.',
    },
  ],
}

export function getFaultCategoriesForProduct(category) {
  if (!category) return FAULT_CATEGORIES_BY_PRODUCT_CATEGORY.Other
  const normalized = category.trim()
  return (
    FAULT_CATEGORIES_BY_PRODUCT_CATEGORY[normalized] ||
    FAULT_CATEGORIES_BY_PRODUCT_CATEGORY.Other
  )
}

// ------------------------------------------------------------------------------
// 1. DEMO DATABASE BUNDLE (Matching SRS & Section 4 of Spec)
// ------------------------------------------------------------------------------
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
    warranty_expiry_date: '2025-02-28', // Expired
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

// Lookup helper simulating Backend JOIN query (Section 5)
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

// ------------------------------------------------------------------------------
// 2. FEATURE ENGINEERING ENGINE (Section 7 of Spec)
// Derives the 14 ML Model features from raw customer inputs + database + evidence
// ------------------------------------------------------------------------------
export function derive14Features(input, product) {
  const now = new Date()
  const incidentDate = input?.incident_date ? new Date(input.incident_date) : now
  const purchaseDate = product?.purchase_date ? new Date(product.purchase_date) : null
  const expiryDate = product?.warranty_expiry_date ? new Date(product.warranty_expiry_date) : null

  // 1. ClaimReportingDelayDays = ClaimCreatedAt - IncidentDate
  const diffTime = now.getTime() - incidentDate.getTime()
  const ClaimReportingDelayDays = Math.max(0, Math.floor(diffTime / (1000 * 60 * 60 * 24)))

  // 2. WarrantyRemainingDays = WarrantyExpiryDate - ClaimCreatedAt
  let WarrantyRemainingDays = 180
  if (expiryDate) {
    const remainingTime = expiryDate.getTime() - now.getTime()
    WarrantyRemainingDays = Math.floor(remainingTime / (1000 * 60 * 60 * 24))
  }

  // 3. ClaimReportingWithinPeriod: within statutory 30-day reporting window
  const ClaimReportingWithinPeriod = ClaimReportingDelayDays <= 30 ? 'Yes' : 'No'

  // 4. FaultCovered: based on FaultDescription + warranty coverage/exclusion rules
  const desc = (input?.fault_description || '').toLowerCase()
  const isExcluded =
    /water|liquid|dropped|falling|shattered|broken screen|physical impact|spilled|tampered|cracked glass|spill/.test(
      desc
    )
  const FaultCovered = isExcluded ? 'No' : 'Yes'

  // 5. RepairAuthorized: PreviousRepair + RepairCentre authorization
  let RepairAuthorized = 'Not Applicable'
  if (input?.previous_repair === 'Yes') {
    const centre = (input?.repair_centre || '').toLowerCase()
    const isAuthorizedCentre =
      /assurex|official|authorized|authorised|lenovo|dell|samsung|apple|hp|premier/.test(centre)
    RepairAuthorized = isAuthorizedCentre ? 'Yes' : 'No'
  }

  // 6. SerialNumberMatch: verified against sold_products database
  const SerialNumberMatch = product?.serial_number ? 'Yes' : 'No'

  // 7. ProductModelConsistent: product/model verified in product_catalog
  const ProductModelConsistent = product?.model_number ? 'Yes' : 'No'

  // 8. OCRConfidence: Automated identity verification confidence score
  const OCRConfidence = product ? 0.95 : 0.60

  // 9. OCRQualityBand: band derived from OCRConfidence
  const OCRQualityBand = OCRConfidence >= 0.85 ? 'High' : OCRConfidence >= 0.7 ? 'Medium' : 'Low'

  // 10. RequiredDocumentsComplete & MissingDocumentCount
  // Pure form-based submission: Customer data complete in form
  const isFormComplete = Boolean(
    input?.incident_date &&
    input?.fault_description?.trim() &&
    (input?.previous_repair !== 'Yes' || input?.repair_centre?.trim())
  )
  const MissingDocumentCount = isFormComplete ? 0 : 1
  const RequiredDocumentsComplete = isFormComplete ? 'Yes' : 'No'

  // 11. DuplicateClaimIndicator
  const DuplicateClaimIndicator = 'No'

  // 12. ContradictionIndicator: rule check contradictions between dates
  let ContradictionIndicator = 'No'
  if (purchaseDate && incidentDate < purchaseDate) {
    ContradictionIndicator = 'Yes' // Incident reported before product was purchased
  }
  if (incidentDate > now) {
    ContradictionIndicator = 'Yes' // Incident date is in the future
  }

  // 13. ProductIdentityMatch: combined serial/model/database verification
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

// ------------------------------------------------------------------------------
// 3. PYTHON MODEL V3 PREDICTION LOGIC
// Client-side policy preview for the active 14 engineered features
// ------------------------------------------------------------------------------
export function predictModelV3(features) {
  // Reject / Ineligible under warranty policy
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

  // Review Required / Examination needed
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

  // Warranty Valid
  return {
    prediction: 'WARRANTY',
    confidence: 0.95,
    reason: 'Standard OEM manufacturing defect verified under active warranty coverage',
    advice:
      'High model confidence. Claim verified eligible under standard warranty coverage.',
  }
}

// ------------------------------------------------------------------------------
// 4. REVIEWER AUDIT DISPLAY METADATA FOR 14 FEATURES
// ------------------------------------------------------------------------------
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

// ------------------------------------------------------------------------------
// 5. TEST PRESETS (Using natural customer inputs)
// ------------------------------------------------------------------------------
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
      repair_report: null, // Missing repair report -> triggers manual review
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
