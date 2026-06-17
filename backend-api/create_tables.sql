-- ==========================================================
-- Taglish Disinformation Detection System
-- MySQL Table Creation Script
-- Database: taglish_db
-- ==========================================================
-- 
-- HOW TO USE:
--   1. Open phpMyAdmin at http://localhost/phpmyadmin
--   2. Click on taglish_db in the sidebar (create it if missing)
--   3. Click the "SQL" tab at the top
--   4. Paste this entire file and click "Go"
-- ==========================================================

CREATE DATABASE IF NOT EXISTS `taglish_db`;
USE `taglish_db`;

-- ---------------------------------------------------------
-- Tables: Users, Models, Predictions, Activity Log
-- Schema updated to match the admin-dashboard ER diagram
-- ---------------------------------------------------------

-- Users table
CREATE TABLE IF NOT EXISTS `tblUsers` (
    `user_id`    INT NOT NULL AUTO_INCREMENT,
    `username`   VARCHAR(50) NOT NULL,
    `password`   VARCHAR(255) NOT NULL,
    `full_name`  VARCHAR(100),
    `role`       VARCHAR(20),
    `is_active`  TINYINT(1) DEFAULT 1,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `last_login` DATETIME,
    PRIMARY KEY (`user_id`),
    UNIQUE KEY `uq_username` (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- Models table
CREATE TABLE IF NOT EXISTS `tblModels` (
    `model_id`         INT NOT NULL AUTO_INCREMENT,
    `model_name`       VARCHAR(100) NOT NULL,
    `model_type`       VARCHAR(50) NOT NULL,
    `accuracy`         FLOAT,
    `precision_macro`  FLOAT,
    `recall_macro`     FLOAT,
    `f1_macro`         FLOAT,
    `avg_inference_ms` FLOAT,
    `file_path`        VARCHAR(255),
    `is_active`        TINYINT(1) DEFAULT 1,
    `trained_at`       DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`model_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- Predictions table
CREATE TABLE IF NOT EXISTS `tblPredictions` (
    `pred_id`          INT NOT NULL AUTO_INCREMENT,
    `user_id`          INT DEFAULT NULL,
    `input_text`       TEXT NOT NULL,
    `predicted_label`  TINYINT NOT NULL,
    `label_text`       VARCHAR(30) NOT NULL,
    `confidence`       FLOAT NOT NULL,
    `cs_ratio`         FLOAT,
    `urgency_count`    INT,
    `particle_count`   INT,
    `punct_intensity`  FLOAT,
    `caps_ratio`       FLOAT,
    `repeat_chars`     INT,
    `emotional_count`  INT,
    `inference_ms`     FLOAT,
    `model_id`         INT DEFAULT NULL,
    `created_at`       DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`pred_id`),
    KEY `idx_user` (`user_id`),
    KEY `idx_model` (`model_id`),
    CONSTRAINT `fk_predictions_user` FOREIGN KEY (`user_id`) REFERENCES `tblUsers`(`user_id`) ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT `fk_predictions_model` FOREIGN KEY (`model_id`) REFERENCES `tblModels`(`model_id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- Activity log table
CREATE TABLE IF NOT EXISTS `tblActivityLog` (
    `log_id`     INT NOT NULL AUTO_INCREMENT,
    `user_id`    INT DEFAULT NULL,
    `action`     VARCHAR(100) NOT NULL,
    `description` TEXT,
    `performed_by` VARCHAR(50) DEFAULT 'system',
    `ip_address`  VARCHAR(45),
    `created_at`  DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`log_id`),
    KEY `idx_activity_user` (`user_id`),
    CONSTRAINT `fk_activity_user` FOREIGN KEY (`user_id`) REFERENCES `tblUsers`(`user_id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
