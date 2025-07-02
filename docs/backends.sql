-- phpMyAdmin SQL Dump
-- version 4.0.10deb1
-- http://www.phpmyadmin.net
--
-- Host: localhost
-- Generation Time: Nov 12, 2017 at 01:29 PM
-- Server version: 5.5.53-0ubuntu0.14.04.1
-- PHP Version: 5.6.23-1+deprecated+dontuse+deb.sury.org~trusty+1

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8 */;

--
-- Database: `vl2`
--

--
-- Dumping data for table `backend_appendix_categories`
--

INSERT INTO `backend_appendix_categories` (`id`, `category`) VALUES
(1, 'ARV Adherence'),
(3, 'ARV Regimens'),
(2, 'Failure Reasons'),
(6, 'Indication for Treatment Initiation'),
(4, 'Sample Rejection Reasons'),
(5, 'TB Treatment Phase'),
(7, 'Treatment Line'),
(8, 'Viral Load Tesing');

--
-- Dumping data for table `backend_appendices`
--

INSERT INTO `backend_appendices` (`id`, `code`, `appendix`, `tag`, `appendix_category_id`) VALUES
(1, '1', 'Good > 95%', '', 1),
(2, '2', 'Fair 85 - 94%', '', 1),
(3, '3', '< 85%', '', 1),
(4, '1', 'Virological', '', 2),
(5, '2', 'Clinical', '', 2),
(6, '3', 'Immunological', '', 2),
(7, '4', 'N/A', '', 2),
(8, '1', '1c = AZT-3TC-NVP', '1', 3),
(9, '2', '1d = AZT-3TC-EFV', '1', 3),
(10, '3', '1e = TDF-3TC-NVP', '1', 3),
(11, '4', '1f = TDF-3TC-EFV', '1', 3),
(12, '5', '1g = TDF-FTC-NVP', '1', 3),
(13, '6', '1h = TDF-FTC-EFV', '1', 3),
(14, '7', '1i = ABC-3TC-EFV', '1', 3),
(15, '8', '1j = ABC-3TC-NVP', '1', 3),
(16, '11', '2b = TDF-3TC-LPV/r', '2', 3),
(17, '12', '2c = TDF-FTC-LPV/r', '2', 3),
(18, '13', '2e = AZT-3TC-LPV/r', '2', 3),
(19, '14', '2f = TDF-FTC-ATV/r', '2', 3),
(20, '15', '2g = TDF-3TC-ATV/r', '2', 3),
(21, '16', '2h = AZT-3TC-ATV/r', '2', 3),
(22, '17', '2i = ABC-3TC-LPV/r', '2', 3),
(23, '18', '2j = ABC-3TC-ATV/r', '2', 3),
(24, '19', '4a = d4T-3TC-NVP', '1', 3),
(25, '20', '4b = d4T-3TC-EFV', '1', 3),
(26, '21', '4c = AZT-3TC-NVP', '1', 3),
(27, '22', '4d = AZT-3TC-EFV', '1', 3),
(28, '23', '4e = ABC-3TC-NVP', '1', 3),
(29, '24', '4f = ABC-3TC-EFV', '1', 3),
(30, '25', '5d = TDF-3TC-LPV/r', '2', 3),
(31, '26', '5e = TDF-FTC-LPV/r', '2', 3),
(32, '27', '5g = AZT-ABC-LPV/r', '2', 3),
(33, '28', '5i = AZT-3TC-ATV/r', '2', 3),
(34, '29', '5j = ABC-3TC-LPV/r', '2', 3),
(35, '30', '5k = ABC-3TC-ATV/r', '2', 3),
(36, '31', 'Left Blank', '4', 3),
(37, '71', 'Other Regimen', '5', 3),
(38, '1', 'Specimen sent to CPHL Laboratory was  less than 0.75ml', 'P,sample_quality', 4),
(39, '2', 'Specimen sent to CPHL was haemolysed', 'P,sample_quality', 4),
(40, '3', 'Mismatching Specimen identifiers on request form and sample', 'P,data_quality', 4),
(41, '4', 'Well labeled DBS card without any blood spots', 'D,sample_quality', 4),
(42, '5', 'Blood spots were collected onto a dirty/soiled DBS card,compromising the specimen integrity', 'D,data_quality', 4),
(43, '6', 'Sample not recieved at CPHL Lab(only the request form was recieved at the testing Lab)', 'P,sample_quality', 4),
(44, '7', 'All Dry Blood Spots on the card were less than the required size i.e not filling the perforated area', 'D,sample_quality', 4),
(45, '8', 'DBS sample sent on wrong Card', 'D,sample_quality', 4),
(46, '9', 'Patient has been on ARVs for less than 6 months(doesn''t qualify for Viral Load testing as per Algorithm)', 'P,eligibility', 4),
(47, '10', 'Dry Blood sample sent with less than 2 spots', 'D,sample_quality', 4),
(48, '11', 'DBS Sample older than 3 weeks,VL test can''t be done on DBS older than 3 weeks.', 'D,sample_quality', 4),
(49, '12', 'Mismatching ART number between sample and form', 'D,data_quality', 4),
(50, '13', 'Well labeled cryo viral container without any sample in it was sent to CPHL Lab', 'P,sample_quality', 4),
(51, '14', 'Sample not recieved at CPHL Lab(only the request form was recieved at the testing Lab)', 'D,sample_quality', 4),
(52, '15', 'Patient has been on ARVs for less than 6 months(doesn''t qualify for Viral Load testing as per Algorithm)', 'D,eligibility', 4),
(53, '16', 'Patient had viral load results above 1000cp/ml in less than 6 months ago (Refer to testing Algorithm)', 'D,eligibility', 4),
(54, '17', 'Patient has wrong date of treatment initiation i.e date earlier than ART role out', 'D,data_quality', 4),
(55, '18', 'Patient has wrong date of treatment initiation i.e date earlier than ART role out', 'P,data_quality', 4),
(56, '19', 'Patient''s date of treatment initiation not included on the form thus failed to determine VL testing eligibility', 'D,data_quality', 4),
(57, '20', 'Patient''s date of treatment initiation not included on the form thus failed to determine VL testing eligibility', 'P,data_quality', 4),
(58, '21', 'Sample was sent in wrong container thus compromising the sample integrity', 'P,sample_quality', 4),
(59, '22', 'Wrong sample type was sent to CPHL-Laboratories,Only Plasma and Dried Blood Spots(DBS) are required', 'D,sample_quality', 4),
(60, '23', 'DBS sample was sent on non-perforated card(not able to get the right spot size during sample processing)', 'D,sample_quality', 4),
(61, '24', 'DBS sample was wet and or had moulds thus compromising with the sample integrity', 'D,sample_quality', 4),
(62, '25', 'Sample was sent in a damaged container', 'P,sample_quality', 4),
(63, '26', 'Patient has not yet been initiated on ART(doesn''t qualify for Viral Load testing as per Algorithm)', 'D,eligibility', 4),
(64, '27', 'Patient has not yet been initiated on ART(doesn''t qualify for Viral Load testing as per Algorithm)', 'P,eligibility', 4),
(65, '28', 'Patient''s dispatch form sent without patient''s identifications(ART number or Other number)', 'D,data_quality', 4),
(66, '29', 'Patient''s dispatch form sent without patient''s identification(ART number or Other number)', 'P,data_quality', 4),
(67, '30', 'Two forms were sent for the same sample(only dispatched results for one form)', 'D,data_quality', 4),
(68, '31', 'Two forms were sent for the same sample(only dispatched results for one form)', 'P,data_quality', 4),
(69, '32', 'Recieved an empty DBS card', 'D,data_quality', 4),
(70, '33', 'Sample was delivered under wrong storage container thus compromising the sample integrity', 'P,sample_quality', 4),
(71, '34', 'DBS card with presence of serum rings i.e improper drying(affecting the specimen integrity)', 'D,sample_quality', 4),
(72, '35', 'DBS Card without ART and form number details(DBS card cannot be linked to request form)', 'D,data_quality', 4),
(73, '36', 'Patient has wrong date of treatment initiation i.e date is beyond the current calender date.', 'P,data_quality', 4),
(74, '37', 'Patient has wrong date of treatment initiation i.e date is beyond the current calendar date', 'D,data_quality', 4),
(75, '38', 'Patient had viral load results less than 1000cp/ml or Not Detected in less than 12 months ago.Refer to testing algorithm.', 'D,eligibility', 4),
(76, '39', 'Plasma sample container without ART and form number details (sample cannot be linked to request form)', 'P,data_quality', 4),
(77, '40', 'Patient had viral load results less than 1000cp/ml or Not Detected in less than 12 months ago.Refer to testing algorithm.', 'P,eligibility', 4),
(78, '41', 'Wrong sample type sent to CPHL-Laboratories,Only Plasma and Dried Blood Spots(DBS) are required', 'P,sample_quality', 4),
(79, '42', 'ART Number details are shared by different patients from the same facility.', 'P,data_quality', 4),
(80, '43', 'ART Number details are shared by different patients from the same facility.', 'D,data_quality', 4),
(81, '44', 'Patient had viral load results above 1000cp/ml in less than 6 months ago (Refer to testing Algorithm)', 'P,eligibility', 4),
(82, '5', 'Initiation Phase', '', 5),
(83, '6', 'Continuation Phase', '', 5),
(84, '1', 'PMTCT/Option B+', '', 6),
(85, '2', 'Child Under 5', '', 6),
(86, '3', 'CD4 < 500', '', 6),
(87, '4', 'TB Infection', '', 6),
(88, '5', 'Other', '', 6),
(89, '1', 'First Line', '', 7),
(90, '2', 'Second Line', '', 7),
(91, '4', 'Left Blank', '', 7),
(92, '5', 'Other Regimen', '', 7),
(93, '1', 'Routine Monitoring', '', 8),
(94, '2', 'Repeat Viral Load', '', 8),
(95, '3', 'Suspected Treatment Failure', '', 8),
(96, '4', 'Left Blank', '', 8),
(97, '5', '6 months after ART initiation', '5', 8),
(98, '6', '12 months after ART initiation', '6', 8),
(99, '7', 'Repeat (after IAC)', '7', 8),
(100, '8', '1st ANC For PMTCT', '8', 8),
(101, '9', 'CCLAD Entry', '9', 8);

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
