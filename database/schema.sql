-- ---------------------------------------------------------------------
-- CivicPulse 2.0 - database schema (MySQL 8 / MariaDB, XAMPP friendly)
-- Import with:  mysql -u root -p < database/schema.sql
-- or paste into phpMyAdmin > SQL.
-- ---------------------------------------------------------------------

CREATE DATABASE IF NOT EXISTS civicpulse
  DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE civicpulse;

DROP TABLE IF EXISTS notifications;
DROP TABLE IF EXISTS issue_status_history;
DROP TABLE IF EXISTS ai_analysis;
DROP TABLE IF EXISTS issue_support;
DROP TABLE IF EXISTS issue_images;
DROP TABLE IF EXISTS issue_reports;
DROP TABLE IF EXISTS issues;
DROP TABLE IF EXISTS categories;
DROP TABLE IF EXISTS departments;
DROP TABLE IF EXISTS users;

-- 1. users -------------------------------------------------------------
CREATE TABLE users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(120) NOT NULL,
  email VARCHAR(160) NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  role VARCHAR(20) NOT NULL DEFAULT 'citizen',
  impact_score INT NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT uq_users_email UNIQUE (email)
);

-- 2. departments -------------------------------------------------------
CREATE TABLE departments (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(120) NOT NULL,
  description VARCHAR(255),
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT uq_departments_name UNIQUE (name)
);

-- 3. categories --------------------------------------------------------
CREATE TABLE categories (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(80) NOT NULL,
  icon VARCHAR(60) NOT NULL DEFAULT 'circle-alert',
  description VARCHAR(255),
  CONSTRAINT uq_categories_name UNIQUE (name)
);

-- 4. issues (one real civic problem = one row) -------------------------
CREATE TABLE issues (
  id INT AUTO_INCREMENT PRIMARY KEY,
  title VARCHAR(200) NOT NULL,
  description TEXT,
  category_id INT,
  latitude DECIMAL(10,7) NOT NULL,
  longitude DECIMAL(10,7) NOT NULL,
  address VARCHAR(255),
  severity INT NOT NULL DEFAULT 5,
  safety_risk INT NOT NULL DEFAULT 5,
  impact_level VARCHAR(20) NOT NULL DEFAULT 'Medium',
  priority_score INT NOT NULL DEFAULT 0,
  status VARCHAR(30) NOT NULL DEFAULT 'Reported',
  department_id INT,
  created_by INT,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_issues_category FOREIGN KEY (category_id) REFERENCES categories(id),
  CONSTRAINT fk_issues_department FOREIGN KEY (department_id) REFERENCES departments(id),
  CONSTRAINT fk_issues_user FOREIGN KEY (created_by) REFERENCES users(id)
);

-- 5. issue_reports (each individual citizen report in a cluster) -------
CREATE TABLE issue_reports (
  id INT AUTO_INCREMENT PRIMARY KEY,
  issue_id INT NOT NULL,
  user_id INT,
  description TEXT,
  latitude DECIMAL(10,7) NOT NULL,
  longitude DECIMAL(10,7) NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_reports_issue FOREIGN KEY (issue_id) REFERENCES issues(id) ON DELETE CASCADE,
  CONSTRAINT fk_reports_user FOREIGN KEY (user_id) REFERENCES users(id)
);

-- 6. issue_images ------------------------------------------------------
CREATE TABLE issue_images (
  id INT AUTO_INCREMENT PRIMARY KEY,
  report_id INT NOT NULL,
  image_path VARCHAR(255) NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_images_report FOREIGN KEY (report_id) REFERENCES issue_reports(id) ON DELETE CASCADE
);

-- 7. issue_support -----------------------------------------------------
CREATE TABLE issue_support (
  id INT AUTO_INCREMENT PRIMARY KEY,
  issue_id INT NOT NULL,
  user_id INT NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT uq_support_once UNIQUE (issue_id, user_id),
  CONSTRAINT fk_support_issue FOREIGN KEY (issue_id) REFERENCES issues(id) ON DELETE CASCADE,
  CONSTRAINT fk_support_user FOREIGN KEY (user_id) REFERENCES users(id)
);

-- 8. ai_analysis -------------------------------------------------------
CREATE TABLE ai_analysis (
  id INT AUTO_INCREMENT PRIMARY KEY,
  issue_id INT NOT NULL,
  category VARCHAR(80),
  severity INT,
  safety_risk INT,
  impact_level VARCHAR(20),
  priority_score INT,
  duplicate_summary VARCHAR(255),
  reasoning TEXT,
  recommendation TEXT,
  confidence DECIMAL(4,3),
  source VARCHAR(20) NOT NULL DEFAULT 'fallback',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_ai_issue FOREIGN KEY (issue_id) REFERENCES issues(id) ON DELETE CASCADE
);

-- 9. issue_status_history (powers the timeline) ------------------------
CREATE TABLE issue_status_history (
  id INT AUTO_INCREMENT PRIMARY KEY,
  issue_id INT NOT NULL,
  status VARCHAR(30) NOT NULL,
  changed_by INT,
  note VARCHAR(500),
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_history_issue FOREIGN KEY (issue_id) REFERENCES issues(id) ON DELETE CASCADE,
  CONSTRAINT fk_history_user FOREIGN KEY (changed_by) REFERENCES users(id)
);

-- 10. notifications ----------------------------------------------------
CREATE TABLE notifications (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  issue_id INT,
  message VARCHAR(400) NOT NULL,
  type VARCHAR(40) NOT NULL DEFAULT 'info',
  is_read INT NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_notif_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  CONSTRAINT fk_notif_issue FOREIGN KEY (issue_id) REFERENCES issues(id) ON DELETE CASCADE
);

-- Indexes --------------------------------------------------------------
CREATE INDEX idx_issues_status ON issues (status);
CREATE INDEX idx_issues_priority ON issues (priority_score);
CREATE INDEX idx_issues_category ON issues (category_id);
CREATE INDEX idx_issues_created ON issues (created_at);
CREATE INDEX idx_reports_issue ON issue_reports (issue_id);
CREATE INDEX idx_reports_user ON issue_reports (user_id);
CREATE INDEX idx_support_issue ON issue_support (issue_id);
CREATE INDEX idx_history_issue ON issue_status_history (issue_id);
CREATE INDEX idx_notif_user ON notifications (user_id, is_read);
