ALTER TABLE `vl_forms_clinicalrequest`  ADD  `migrated` ENUM(  'YES',  'NO' ) NOT NULL DEFAULT  'NO';
ALTER TABLE `vl_samples`  ADD  `migrated` ENUM(  'YES',  'NO' ) NOT NULL DEFAULT  'NO';