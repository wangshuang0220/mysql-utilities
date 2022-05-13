DROP DATABASE IF EXISTS util_test;
CREATE DATABASE util_test;
CREATE USER `joe_nopass`@`user`;
CREATE USER `joe_pass`@`user` IDENTIFIED BY 'dumb';
CREATE USER `amy_nopass`@`user`;
GRANT ALL ON util_test.* TO `joe_nopass`@`user`;
# #if (server != "MySQL") or (int(version) < 80000)
GRANT SELECT ON util_test.* TO `joe_pass`@`user` IDENTIFIED BY 'dumb';
# #else
GRANT SELECT ON util_test.* TO `joe_pass`@`user` ;
GRANT ALL ON util_test.* TO root@localhost;
-- above is a misfeature of mysql 8.0 grant definition
# #endif
GRANT INSERT ON util_test.* TO `amy_nopass`@`user`;
CREATE USER `remote`@`%` IDENTIFIED BY 'away_from_work';
GRANT SELECT ON util_test.* TO `remote`@`%`;
