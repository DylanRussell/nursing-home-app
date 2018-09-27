SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS `facility`;
CREATE TABLE `facility` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `name` varchar(255) NOT NULL,
  `address` varchar(255) NOT NULL,
  `city` varchar(80) NOT NULL,
  `state` varchar(50) NOT NULL,
  `zipcode` varchar(80) NOT NULL,
  `phone_number` varchar(80) NOT NULL,
  `active` tinyint(1) NOT NULL DEFAULT '1',
  `num_floors` int(11) NOT NULL,
  `create_user` bigint(20) NOT NULL,
  `update_user` bigint(20) DEFAULT NULL,
  `create_date` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `update_date` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8;


DROP TABLE IF EXISTS `facility_audit_trail`;
CREATE TABLE `facility_audit_trail` (
  `pkey` bigint(20) NOT NULL AUTO_INCREMENT,
  `id` bigint(20) NOT NULL,
  `name` varchar(255) NOT NULL,
  `address` varchar(255) NOT NULL,
  `city` varchar(80) NOT NULL,
  `state` varchar(50) NOT NULL,
  `zipcode` varchar(80) NOT NULL,
  `phone_number` varchar(80) NOT NULL,
  `active` tinyint(1) NOT NULL DEFAULT '1',
  `num_floors` int(11) NOT NULL,
  `create_user` bigint(20) NOT NULL,
  `update_user` bigint(20) DEFAULT NULL,
  `create_date` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `update_date` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`pkey`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8;


DROP TABLE IF EXISTS `notification`;
CREATE TABLE `notification` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `email` varchar(255) DEFAULT NULL,
  `designee_email` varchar(255) DEFAULT NULL,
  `email_notification_on` tinyint(1) NOT NULL DEFAULT '1',
  `notify_designee` tinyint(1) NOT NULL DEFAULT '0',
  `email_every_n_days` int(11) NOT NULL DEFAULT '15',
  `phone` varchar(255) DEFAULT NULL,
  `phone_notification_on` tinyint(1) NOT NULL DEFAULT '1',
  `sms_n_days_advance` int(11) NOT NULL DEFAULT '-1',
  `create_date` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `update_date` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `user_id` bigint(20) NOT NULL,
  `create_user` bigint(20) NOT NULL,
  `update_user` bigint(20) DEFAULT NULL,
  `email_last_sent` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `text_last_sent` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8;


DROP TABLE IF EXISTS `notification_audit_trail`;
CREATE TABLE `notification_audit_trail` (
  `pkey` bigint(20) NOT NULL AUTO_INCREMENT,
  `id` bigint(20) NOT NULL,
  `email` varchar(255) DEFAULT NULL,
  `designee_email` varchar(255) DEFAULT NULL,
  `email_notification_on` tinyint(1) NOT NULL DEFAULT '1',
  `notify_designee` tinyint(1) NOT NULL DEFAULT '0',
  `email_every_n_days` int(11) NOT NULL DEFAULT '15',
  `phone` varchar(255) DEFAULT NULL,
  `phone_notification_on` tinyint(1) NOT NULL DEFAULT '1',
  `sms_n_days_advance` int(11) NOT NULL DEFAULT '-1',
  `create_date` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `update_date` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `user_id` bigint(20) NOT NULL,
  `create_user` bigint(20) NOT NULL,
  `update_user` bigint(20) DEFAULT NULL,
  `email_last_sent` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `text_last_sent` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`pkey`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8;


DROP TABLE IF EXISTS `patient`;
CREATE TABLE `patient` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `first` varchar(255) NOT NULL,
  `last` varchar(255) NOT NULL,
  `room_number` varchar(80) NOT NULL,
  `status` tinyint(3) NOT NULL,
  `NP_id` bigint(20) DEFAULT NULL,
  `MD_id` bigint(20) DEFAULT NULL,
  `admittance_date` date DEFAULT NULL,
  `has_medicaid` tinyint(1) NOT NULL DEFAULT '0',
  `consecutive_skilled_visits` int(11) NOT NULL DEFAULT '0',
  `create_date` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `update_date` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `create_user` bigint(20) NOT NULL,
  `update_user` bigint(20) DEFAULT NULL,
  `facility_id` bigint(20) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `patient_facility_fk` (`facility_id`),
  CONSTRAINT `patient_facility_fk` FOREIGN KEY (`facility_id`) REFERENCES `facility` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8;

DROP TABLE IF EXISTS `patient_audit_trail`;
CREATE TABLE `patient_audit_trail` (
  `pkey` bigint(20) NOT NULL AUTO_INCREMENT,
  `id` bigint(20) NOT NULL,
  `first` varchar(255) NOT NULL,
  `last` varchar(255) NOT NULL,
  `room_number` varchar(80) NOT NULL,
  `status` tinyint(3) NOT NULL,
  `NP_id` bigint(20) DEFAULT NULL,
  `MD_id` bigint(20) DEFAULT NULL,
  `admittance_date` date DEFAULT NULL,
  `has_medicaid` tinyint(1) NOT NULL DEFAULT '0',
  `consecutive_skilled_visits` int(11) NOT NULL DEFAULT '0',
  `create_date` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `update_date` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `create_user` bigint(20) NOT NULL,
  `update_user` bigint(20) DEFAULT NULL,
  `facility_id` bigint(20) NOT NULL,
  PRIMARY KEY (`pkey`) USING BTREE,
  KEY `patient_facility_fk` (`facility_id`),
  CONSTRAINT `patient_audit_trail_ibfk_1` FOREIGN KEY (`facility_id`) REFERENCES `facility` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8;


DROP TABLE IF EXISTS `patient_status`;
CREATE TABLE `patient_status` (
  `id` tinyint(3) NOT NULL,
  `status` varchar(255) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;


DROP TABLE IF EXISTS `permission`;
CREATE TABLE `permission` (
  `bit` bigint(20) NOT NULL,
  `name` varchar(50) NOT NULL,
  PRIMARY KEY (`bit`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;


DROP TABLE IF EXISTS `user`;
CREATE TABLE `user` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `role` varchar(255) NOT NULL,
  `first` varchar(255) NOT NULL,
  `last` varchar(255) NOT NULL,
  `email` varchar(255) NOT NULL,
  `phone` varchar(255) DEFAULT NULL,
  `floor` varchar(255) DEFAULT NULL,
  `password` binary(60) DEFAULT NULL,
  `email_confirmed` tinyint(1) NOT NULL DEFAULT '0',
  `confirmed_on` timestamp NULL DEFAULT NULL,
  `create_date` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `update_date` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `create_user` bigint(20) NOT NULL,
  `update_user` bigint(20) DEFAULT NULL,
  `active` tinyint(1) NOT NULL DEFAULT '1',
  `invitation_last_sent` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8;


DROP TABLE IF EXISTS `user_audit_trail`;
CREATE TABLE `user_audit_trail` (
  `pkey` bigint(20) NOT NULL AUTO_INCREMENT,
  `id` bigint(20) NOT NULL,
  `role` varchar(255) NOT NULL,
  `first` varchar(255) NOT NULL,
  `last` varchar(255) NOT NULL,
  `email` varchar(255) NOT NULL,
  `phone` varchar(255) DEFAULT NULL,
  `floor` varchar(255) DEFAULT NULL,
  `password` binary(60) DEFAULT NULL,
  `email_confirmed` tinyint(1) NOT NULL DEFAULT '0',
  `confirmed_on` timestamp NULL DEFAULT NULL,
  `create_date` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `update_date` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `create_user` bigint(20) NOT NULL,
  `update_user` bigint(20) DEFAULT NULL,
  `active` tinyint(1) NOT NULL DEFAULT '1',
  `invitation_last_sent` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`pkey`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8;

DROP TABLE IF EXISTS `user_role`;
CREATE TABLE `user_role` (
  `role` varchar(255) NOT NULL,
  `role_value` bigint(20) NOT NULL,
  PRIMARY KEY (`role`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;


DROP TABLE IF EXISTS `user_to_facility`;
CREATE TABLE `user_to_facility` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `user_id` bigint(20) NOT NULL,
  `facility_id` bigint(20) NOT NULL,
  `update_date` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `create_date` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `create_user` bigint(20) NOT NULL,
  `update_user` bigint(20) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `user_fk` (`user_id`),
  KEY `facility_fk` (`facility_id`),
  CONSTRAINT `facility_fk` FOREIGN KEY (`facility_id`) REFERENCES `facility` (`id`),
  CONSTRAINT `user_fk` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8 COLLATE=utf8_bin;


DROP TABLE IF EXISTS `visit`;
CREATE TABLE `visit` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `patient_id` bigint(20) NOT NULL,
  `user_id` bigint(20) DEFAULT NULL,
  `visit_date` date NOT NULL,
  `visit_done_by_doctor` tinyint(1) NOT NULL,
  `note_received` tinyint(1) NOT NULL DEFAULT '0',
  `orders_signed` tinyint(1) NOT NULL DEFAULT '0',
  `create_user` bigint(20) NOT NULL,
  `update_user` bigint(20) DEFAULT NULL,
  `create_date` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `update_date` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8;


DROP TABLE IF EXISTS `visit_audit_trail`;
CREATE TABLE `visit_audit_trail` (
  `pkey` bigint(20) NOT NULL AUTO_INCREMENT,
  `id` bigint(20) NOT NULL,
  `patient_id` bigint(20) NOT NULL,
  `user_id` bigint(20) DEFAULT NULL,
  `visit_date` date NOT NULL,
  `visit_done_by_doctor` tinyint(1) NOT NULL,
  `note_received` tinyint(1) NOT NULL DEFAULT '0',
  `orders_signed` tinyint(1) NOT NULL DEFAULT '0',
  `create_user` bigint(20) NOT NULL,
  `update_user` bigint(20) DEFAULT NULL,
  `create_date` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `update_date` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`pkey`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8;

SET FOREIGN_KEY_CHECKS = 1;