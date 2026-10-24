-- ==============================================================
-- Village Digital Service & Request Management System
-- Database Schema Setup
-- Database Name: village_service_db
-- ==============================================================

-- Create database if it does not already exist
CREATE DATABASE IF NOT EXISTS village_service_db
CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;

-- Select database for use
USE village_service_db;

-- --------------------------------------------------------------
-- Table Structure: users (Citizen Accounts)
-- --------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    mobile VARCHAR(15) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    address TEXT NOT NULL,
    village_name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_active TINYINT(1) DEFAULT 1
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------------
-- Table Structure: applications (Village Services & Requests)
-- --------------------------------------------------------------
CREATE TABLE IF NOT EXISTS applications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    application_number VARCHAR(30) NOT NULL UNIQUE,
    user_id INT NOT NULL,
    service_category VARCHAR(50) NOT NULL,
    service_type VARCHAR(100) NOT NULL,
    subject VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    applicant_name VARCHAR(100) NOT NULL,
    mobile VARCHAR(15) NOT NULL,
    address TEXT NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'Submitted',
    officer_remarks TEXT DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------------
-- Table Structure: application_documents (Supporting Attachments)
-- --------------------------------------------------------------
CREATE TABLE IF NOT EXISTS application_documents (
    id INT AUTO_INCREMENT PRIMARY KEY,
    application_id INT NOT NULL,
    user_id INT NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    original_name VARCHAR(255) NOT NULL,
    file_size INT NOT NULL,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (application_id) REFERENCES applications(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------------
-- Table Structure: officers (Gram Sevak / Administration Staff)
-- --------------------------------------------------------------
CREATE TABLE IF NOT EXISTS officers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    mobile VARCHAR(15) NOT NULL UNIQUE,
    designation VARCHAR(100) NOT NULL,
    village_name VARCHAR(100) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    is_active TINYINT(1) DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Seed initial Gram Sevak / Officer account (Password: officer123)
INSERT IGNORE INTO officers (id, full_name, email, mobile, designation, village_name, password_hash)
VALUES (
    1,
    'R. K. Patil (Gram Sevak)',
    'officer@village.gov.in',
    '9800112233',
    'Gram Sevak',
    'Sundarpur',
    'scrypt:32768:8:1$MZ51vXfbdFiGcjbv$79466d25af7dc551faeb9034cb91be16c59333220988ae4fdc3f0119a76095333b39a6f21959a6902cccdaff46de43cb389e5afbbfd289f3047ec0889fed057d'
);


-- --------------------------------------------------------------
-- Table Structure: notices (Public Village Announcements)
-- --------------------------------------------------------------
CREATE TABLE IF NOT EXISTS notices (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    category VARCHAR(50) NOT NULL DEFAULT 'General',
    content TEXT NOT NULL,
    posted_by VARCHAR(100) NOT NULL DEFAULT 'Gram Sevak',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active TINYINT(1) DEFAULT 1
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Seed sample village announcements
INSERT IGNORE INTO notices (id, title, category, content, posted_by)
VALUES 
(
    1,
    'ग्रामसभा बैठक आयोजन - माहे ऑक्टोबर २०२६',
    'Meeting',
    'सर्व ग्रामस्थांना कळविण्यात येते की येत्या २५ ऑक्टोबर २०२६ रोजी सकाळी १०:०० वाजता ग्रामपंचायत कार्यालय येथे मासिक ग्रामसभेचे आयोजन करण्यात आले आहे. सर्व नागरिकांनी वेळेवर उपस्थित राहावे.',
    'R. K. Patil (Gram Sevak)'
),
(
    2,
    'पाणीपुरवठा पाईपलाईन दुरुस्ती सूचना - प्रभाग क्र. ३',
    'Alert',
    'प्रभाग क्र. ३ मधील मुख्य पाणीपुरवठा पाईपलाईनच्या दुरुस्तीचे काम हाती घेतले असल्याने उद्या दुपारी १ ते सायंकाळी ६ वाजेपर्यंत पाणीपुरवठा बंद राहील. नागरिकांनी सहकार्य करावे.',
    'Gram Panchayat Water Dept.'
),
(
    3,
    'मोफत आरोग्य व नेत्र तपासणी शिबीर',
    'Health',
    'प्राथमिक आरोग्य केंद्र व ग्रामपंचायत यांच्या संयुक्त विद्यमाने आगामी रविवारी प्राथमिक शाळेमध्ये मोफत आरोग्य व डोळे तपासणी शिबीर आयोजित केले आहे.',
    'Health Officer'
);
