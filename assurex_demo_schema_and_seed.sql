-- ==============================================================================
-- ASSUREX CLAIM ENGINE - DEMO SCHEMA & SEED DATA (SQLITE / POSTGRESQL COMPATIBLE)
-- Submit Claim Data & Database Handoff
-- User input -> Product lookup -> Feature engineering -> Python Model V3
-- ==============================================================================

DROP TABLE IF EXISTS sold_products;
DROP TABLE IF EXISTS product_catalog;
DROP TABLE IF EXISTS users;

-- 1. USERS (20 Demo Customers)
CREATE TABLE users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_code VARCHAR(20) UNIQUE NOT NULL,
  full_name VARCHAR(120) NOT NULL,
  email VARCHAR(150) UNIQUE NOT NULL,
  phone VARCHAR(30),
  address VARCHAR(255),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO users (id, user_code, full_name, email, phone, address) VALUES
(1, 'CUS0001', 'Bui Ngoc Mai', 'ngoc.mai07@example.com', '0912345678', '123 Kim Ma, Ba Dinh, Hanoi'),
(2, 'CUS0002', 'Nguyen Van An', 'an.nguyen@example.com', '0987654321', '45 Le Duan, District 1, Ho Chi Minh City'),
(3, 'CUS0003', 'Tran Thi Lan', 'lan.tran@example.com', '0901234567', '78 Tran Phu, Hai Chau, Da Nang'),
(4, 'CUS0004', 'Le Hoang Nam', 'nam.le@example.com', '0934567890', '12 Nguyen Thi Minh Khai, Hue'),
(5, 'CUS0005', 'Pham Minh Tu', 'tu.pham@example.com', '0945678901', '89 Nguyen Trai, Thanh Xuan, Hanoi'),
(6, 'CUS0006', 'Do Quoc Huy', 'huy.do@example.com', '0956789012', '56 Quang Trung, Hai Ba Trung, Hanoi'),
(7, 'CUS0007', 'Vu Thuy Linh', 'linh.vu@example.com', '0967890123', '23 Phan Chu Trinh, Hoan Kiem, Hanoi'),
(8, 'CUS0008', 'Hoang Gia Bao', 'bao.hoang@example.com', '0978901234', '101 Vo Van Tan, District 3, HCMC'),
(9, 'CUS0009', 'Ngo Thanh Dat', 'dat.ngo@example.com', '0989012345', '14 Bach Dang, Tan Binh, HCMC'),
(10, 'CUS0010', 'Dinh Phuong Thao', 'thao.dinh@example.com', '0990123456', '67 Hung Vuong, Da Nang'),
(11, 'CUS0011', 'Trinh Duc Minh', 'minh.trinh@example.com', '0911223344', '88 Hoang Dieu, Hai Chau, Da Nang'),
(12, 'CUS0012', 'Ly My Duyen', 'duyen.ly@example.com', '0922334455', '32 Tran Hung Dao, Nha Trang'),
(13, 'CUS0013', 'Cao Van Cuong', 'cuong.cao@example.com', '0933445566', '55 Le Loi, Vung Tau'),
(14, 'CUS0014', 'Mai Kim Ngan', 'ngan.mai@example.com', '0944556677', '90 Nguyen Hue, Can Tho'),
(15, 'CUS0015', 'Duong Van Tan', 'tan.duong@example.com', '0955667788', '11 Hai Ba Trung, Dalat'),
(16, 'CUS0016', 'Bui Thi Huong', 'huong.bui@example.com', '0966778899', '44 Dien Bien Phu, Binh Thanh, HCMC'),
(17, 'CUS0017', 'Phan Anh Tuan', 'tuan.phan@example.com', '0977889900', '18 Nguyen Chi Thanh, Ba Dinh, Hanoi'),
(18, 'CUS0018', 'Nguyen Thao My', 'my.nguyen@example.com', '0988990011', '72 Cach Mang Thang 8, District 10, HCMC'),
(19, 'CUS0019', 'Luu Tuan Kiet', 'kiet.luu@example.com', '0999001122', '35 Ly Tu Trong, District 1, HCMC'),
(20, 'CUS0020', 'Vo Thi Bich', 'bich.vo@example.com', '0910111213', '29 Dong Khoi, District 1, HCMC');

-- 2. PRODUCT_CATALOG (10 Product Models)
CREATE TABLE product_catalog (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  catalog_code VARCHAR(30) UNIQUE NOT NULL,
  product_name VARCHAR(150) NOT NULL,
  category VARCHAR(80) NOT NULL,
  brand VARCHAR(100) NOT NULL,
  model_number VARCHAR(100) UNIQUE NOT NULL,
  standard_warranty_months INTEGER NOT NULL,
  warranty_provider VARCHAR(120),
  active BOOLEAN DEFAULT 1
);

INSERT INTO product_catalog (id, catalog_code, product_name, category, brand, model_number, standard_warranty_months, warranty_provider, active) VALUES
(1, 'CAT-NB14', 'NovaBook 14 Ultra', 'Laptop', 'NovaTech', 'NB14-2026', 24, 'NovaTech Official Care', 1),
(2, 'CAT-TPT14', 'ThinkPad T14 Gen 4', 'Laptop', 'Lenovo', '21HD0001US', 24, 'Lenovo Premier Support', 1),
(3, 'CAT-S24U', 'Galaxy S24 Ultra', 'Smartphone', 'Samsung', 'SM-S928B', 12, 'Samsung Care+', 1),
(4, 'CAT-U2724D', 'UltraSharp 27 4K Monitor', 'Monitor', 'Dell', 'U2724D', 36, 'Dell Advanced Exchange', 1),
(5, 'CAT-LJ4103', 'LaserJet Pro MFP 4103fdw', 'Printer', 'HP', '4103fdw', 12, 'HP Commercial Support', 1),
(6, 'CAT-IP16P', 'iPhone 16 Pro Max', 'Smartphone', 'Apple', 'A3297', 12, 'AppleCare Service', 1),
(7, 'CAT-MBP16', 'MacBook Pro 16 M3 Max', 'Laptop', 'Apple', 'A2991', 12, 'AppleCare Service', 1),
(8, 'CAT-XPS15', 'Dell XPS 15 9530', 'Laptop', 'Dell', 'XPS9530', 24, 'Dell ProSupport', 1),
(9, 'CAT-IPAD11', 'iPad Pro 11-inch M4', 'Tablet', 'Apple', 'A2836', 12, 'AppleCare Service', 1),
(10, 'CAT-TAB9', 'Galaxy Tab S9 Ultra', 'Tablet', 'Samsung', 'SM-X910', 12, 'Samsung Care+', 1);

-- 3. SOLD_PRODUCTS (50 Sold Product Units)
CREATE TABLE sold_products (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  product_code VARCHAR(30) UNIQUE NOT NULL,
  user_id INTEGER NOT NULL,
  catalog_id INTEGER NOT NULL,
  serial_number VARCHAR(100) UNIQUE NOT NULL,
  purchase_date DATE NOT NULL,
  purchase_price DECIMAL(12,2),
  retailer VARCHAR(150),
  invoice_number VARCHAR(100),
  warranty_months INTEGER NOT NULL,
  warranty_start_date DATE NOT NULL,
  warranty_expiry_date DATE NOT NULL,
  extended_warranty BOOLEAN DEFAULT 0,
  status VARCHAR(30) DEFAULT 'active',
  FOREIGN KEY (user_id) REFERENCES users(id),
  FOREIGN KEY (catalog_id) REFERENCES product_catalog(id)
);

INSERT INTO sold_products (id, product_code, user_id, catalog_id, serial_number, purchase_date, purchase_price, retailer, invoice_number, warranty_months, warranty_start_date, warranty_expiry_date, extended_warranty, status) VALUES
(1, 'AX26-00001', 1, 1, 'NB142026-00001', '2026-07-17', 1299.00, 'NovaStore Central', 'INV-2026-9021', 24, '2026-07-17', '2028-07-16', 0, 'active'),
(2, 'AX26-00002', 2, 2, 'PF4X9812', '2025-11-10', 1450.00, 'TechWorld Store', 'INV-2025-4491', 24, '2025-11-10', '2027-11-09', 0, 'active'),
(3, 'AX26-00003', 3, 3, 'R5CW109K', '2024-03-01', 1199.00, 'PhoneMart Flagship', 'INV-2024-1182', 12, '2024-03-01', '2025-02-28', 0, 'expired'),
(4, 'AX26-00004', 1, 4, 'CN-0M27D-128', '2026-01-15', 620.00, 'DigiPro Electronics', 'INV-2026-0312', 36, '2026-01-15', '2029-01-14', 1, 'active'),
(5, 'AX26-00005', 2, 5, 'VNB3K9821', '2025-06-20', 480.00, 'OfficeDepot Vietnam', 'INV-2025-7721', 12, '2025-06-20', '2026-06-19', 0, 'active'),
(6, 'AX26-00006', 4, 6, 'FK2N89A120', '2025-12-01', 1399.00, 'Apple Store Online', 'INV-2025-9901', 12, '2025-12-01', '2026-11-30', 0, 'active'),
(7, 'AX26-00007', 5, 7, 'C02G899KLM', '2025-08-15', 3499.00, 'Apple Store Online', 'INV-2025-6612', 12, '2025-08-15', '2026-08-14', 0, 'active'),
(8, 'AX26-00008', 6, 8, '8H7J92XPS', '2026-02-10', 2199.00, 'Dell Store Vietnam', 'INV-2026-1044', 24, '2026-02-10', '2028-02-09', 0, 'active'),
(9, 'AX26-00009', 7, 9, 'DLXN4091M4', '2025-09-05', 999.00, 'FPT Shop', 'INV-2025-8812', 12, '2025-09-05', '2026-09-04', 0, 'active'),
(10, 'AX26-00010', 8, 10, 'R52X801TAB', '2025-10-18', 1099.00, 'CellphoneS', 'INV-2025-5431', 12, '2025-10-18', '2026-10-17', 0, 'active'),
(11, 'AX26-00011', 9, 1, 'NB142026-00011', '2026-05-12', 1299.00, 'NovaStore Central', 'INV-2026-4432', 24, '2026-05-12', '2028-05-11', 0, 'active'),
(12, 'AX26-00012', 10, 2, 'PF4X9813', '2025-07-01', 1450.00, 'TechWorld Store', 'INV-2025-3310', 24, '2025-07-01', '2027-06-30', 0, 'active'),
(13, 'AX26-00013', 11, 3, 'R5CW109L', '2024-04-15', 1199.00, 'PhoneMart Flagship', 'INV-2024-2201', 12, '2024-04-15', '2025-04-14', 0, 'expired'),
(14, 'AX26-00014', 12, 4, 'CN-0M27D-129', '2025-11-20', 620.00, 'DigiPro Electronics', 'INV-2025-9118', 36, '2025-11-20', '2028-11-19', 0, 'active'),
(15, 'AX26-00015', 13, 5, 'VNB3K9822', '2025-03-10', 480.00, 'OfficeDepot Vietnam', 'INV-2025-1188', 12, '2025-03-10', '2026-03-09', 0, 'active'),
(16, 'AX26-00016', 14, 6, 'FK2N89A121', '2026-01-22', 1399.00, 'The Gioi Di Dong', 'INV-2026-0199', 12, '2026-01-22', '2027-01-21', 0, 'active'),
(17, 'AX26-00017', 15, 7, 'C02G899KLN', '2025-12-14', 3499.00, 'FPT Shop', 'INV-2025-9988', 12, '2025-12-14', '2026-12-13', 0, 'active'),
(18, 'AX26-00018', 16, 8, '8H7J92XPT', '2025-09-30', 2199.00, 'An Phat Computer', 'INV-2025-7890', 24, '2025-09-30', '2027-09-29', 0, 'active'),
(19, 'AX26-00019', 17, 9, 'DLXN4091M5', '2026-03-18', 999.00, 'Apple Store Online', 'INV-2026-3011', 12, '2026-03-18', '2027-03-17', 0, 'active'),
(20, 'AX26-00020', 18, 10, 'R52X801TAC', '2025-08-25', 1099.00, 'Viettel Store', 'INV-2025-6677', 12, '2025-08-25', '2026-08-24', 0, 'active'),
(21, 'AX26-00021', 19, 1, 'NB142026-00021', '2026-08-01', 1299.00, 'NovaStore Central', 'INV-2026-8001', 24, '2026-08-01', '2028-07-31', 0, 'active'),
(22, 'AX26-00022', 20, 2, 'PF4X9814', '2025-10-05', 1450.00, 'Hanoicomputer', 'INV-2025-5050', 24, '2025-10-05', '2027-10-04', 0, 'active'),
(23, 'AX26-00023', 1, 3, 'R5CW109M', '2025-04-10', 1199.00, 'CellphoneS', 'INV-2025-4100', 12, '2025-04-10', '2026-04-09', 0, 'active'),
(24, 'AX26-00024', 2, 4, 'CN-0M27D-130', '2026-04-12', 620.00, 'GearVN', 'INV-2026-4122', 36, '2026-04-12', '2029-04-11', 0, 'active'),
(25, 'AX26-00025', 3, 5, 'VNB3K9823', '2025-08-19', 480.00, 'Phong Vu', 'INV-2025-8199', 12, '2025-08-19', '2026-08-18', 0, 'active'),
(26, 'AX26-00026', 4, 6, 'FK2N89A122', '2026-02-14', 1399.00, 'Apple Store Online', 'INV-2026-2144', 12, '2026-02-14', '2027-02-13', 0, 'active'),
(27, 'AX26-00027', 5, 7, 'C02G899KLP', '2025-11-01', 3499.00, 'Hoang Ha Mobile', 'INV-2025-1101', 12, '2025-11-01', '2026-10-31', 0, 'active'),
(28, 'AX26-00028', 6, 8, '8H7J92XPU', '2026-01-08', 2199.00, 'Dell Store Vietnam', 'INV-2026-0108', 24, '2026-01-08', '2028-01-07', 0, 'active'),
(29, 'AX26-00029', 7, 9, 'DLXN4091M6', '2025-07-28', 999.00, 'FPT Shop', 'INV-2025-7288', 12, '2025-07-28', '2026-07-27', 0, 'active'),
(30, 'AX26-00030', 8, 10, 'R52X801TAD', '2025-09-12', 1099.00, 'The Gioi Di Dong', 'INV-2025-9122', 12, '2025-09-12', '2026-09-11', 0, 'active'),
(31, 'AX26-00031', 9, 1, 'NB142026-00031', '2026-06-15', 1299.00, 'NovaStore Central', 'INV-2026-6155', 24, '2026-06-15', '2028-06-14', 0, 'active'),
(32, 'AX26-00032', 10, 2, 'PF4X9815', '2025-12-08', 1450.00, 'TechWorld Store', 'INV-2025-1208', 24, '2025-12-08', '2027-12-07', 0, 'active'),
(33, 'AX26-00033', 11, 3, 'R5CW109N', '2024-05-20', 1199.00, 'PhoneMart Flagship', 'INV-2024-5200', 12, '2024-05-20', '2025-05-19', 0, 'expired'),
(34, 'AX26-00034', 12, 4, 'CN-0M27D-131', '2026-03-01', 620.00, 'DigiPro Electronics', 'INV-2026-3010', 36, '2026-03-01', '2029-02-28', 0, 'active'),
(35, 'AX26-00035', 13, 5, 'VNB3K9824', '2025-10-10', 480.00, 'OfficeDepot Vietnam', 'INV-2025-1010', 12, '2025-10-10', '2026-10-09', 0, 'active'),
(36, 'AX26-00036', 14, 6, 'FK2N89A123', '2025-11-25', 1399.00, 'Apple Store Online', 'INV-2025-1125', 12, '2025-11-25', '2026-11-24', 0, 'active'),
(37, 'AX26-00037', 15, 7, 'C02G899KLQ', '2026-01-10', 3499.00, 'Apple Store Online', 'INV-2026-1100', 12, '2026-01-10', '2027-01-09', 0, 'active'),
(38, 'AX26-00038', 16, 8, '8H7J92XPV', '2025-08-04', 2199.00, 'GearVN', 'INV-2025-8044', 24, '2025-08-04', '2027-08-03', 0, 'active'),
(39, 'AX26-00039', 17, 9, 'DLXN4091M7', '2026-04-05', 999.00, 'CellphoneS', 'INV-2026-4055', 12, '2026-04-05', '2027-04-04', 0, 'active'),
(40, 'AX26-00040', 18, 10, 'R52X801TAE', '2025-06-11', 1099.00, 'Samsung Store', 'INV-2025-6111', 12, '2025-06-11', '2026-06-10', 0, 'active'),
(41, 'AX26-00041', 19, 1, 'NB142026-00041', '2026-07-02', 1299.00, 'NovaStore Central', 'INV-2026-7022', 24, '2026-07-02', '2028-07-01', 0, 'active'),
(42, 'AX26-00042', 20, 2, 'PF4X9816', '2025-05-19', 1450.00, 'TechWorld Store', 'INV-2025-5199', 24, '2025-05-19', '2027-05-18', 0, 'active'),
(43, 'AX26-00043', 1, 3, 'R5CW109P', '2024-02-14', 1199.00, 'PhoneMart Flagship', 'INV-2024-2144', 12, '2024-02-14', '2025-02-13', 0, 'expired'),
(44, 'AX26-00044', 2, 4, 'CN-0M27D-132', '2025-12-28', 620.00, 'DigiPro Electronics', 'INV-2025-1228', 36, '2025-12-28', '2028-12-27', 0, 'active'),
(45, 'AX26-00045', 3, 5, 'VNB3K9825', '2026-02-02', 480.00, 'OfficeDepot Vietnam', 'INV-2026-2022', 12, '2026-02-02', '2027-02-01', 0, 'active'),
(46, 'AX26-00046', 4, 6, 'FK2N89A124', '2025-10-30', 1399.00, 'Apple Store Online', 'INV-2025-1030', 12, '2025-10-30', '2026-10-29', 0, 'active'),
(47, 'AX26-00047', 5, 7, 'C02G899KLR', '2026-03-25', 3499.00, 'Apple Store Online', 'INV-2026-3255', 12, '2026-03-25', '2027-03-24', 0, 'active'),
(48, 'AX26-00048', 6, 8, '8H7J92XPW', '2025-11-15', 2199.00, 'An Phat Computer', 'INV-2025-1115', 24, '2025-11-15', '2027-11-14', 0, 'active'),
(49, 'AX26-00049', 7, 9, 'DLXN4091M8', '2026-05-09', 999.00, 'Viettel Store', 'INV-2026-5099', 12, '2026-05-09', '2027-05-08', 0, 'active'),
(50, 'AX26-00050', 8, 10, 'R52X801TAF', '2025-07-16', 1099.00, 'FPT Shop', 'INV-2025-7166', 12, '2025-07-16', '2026-07-15', 0, 'active');
