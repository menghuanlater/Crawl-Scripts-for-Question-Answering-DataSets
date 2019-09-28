/*
Navicat MySQL Data Transfer

Source Server         : localhost_3306
Source Server Version : 80017
Source Host           : localhost:3306
Source Database       : qadb

Target Server Type    : MYSQL
Target Server Version : 80017
File Encoding         : 65001

Date: 2019-09-28 22:43:12
*/

SET FOREIGN_KEY_CHECKS=0;

-- ----------------------------
-- Table structure for `crawl_data`
-- ----------------------------
DROP TABLE IF EXISTS `crawl_data`;
CREATE TABLE `crawl_data` (
  `id` int(11) NOT NULL,
  `url` varchar(255) COLLATE utf8_bin NOT NULL DEFAULT '',
  `crawl_time` datetime NOT NULL,
  `title` varchar(255) CHARACTER SET utf8 COLLATE utf8_bin DEFAULT NULL,
  `passage_text` mediumtext CHARACTER SET utf8 COLLATE utf8_bin NOT NULL,
  `passage_type` varchar(50) COLLATE utf8_bin NOT NULL,
  `passage_length` int(10) NOT NULL DEFAULT '0',
  `source` varchar(20) COLLATE utf8_bin NOT NULL,
  `publish_time` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `for_url_search` (`url`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_bin;

-- ----------------------------
-- Records of crawl_data
-- ----------------------------
