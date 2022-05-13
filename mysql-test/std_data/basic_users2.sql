# #if (server == "MySQL") and (int(version) >= 80000)
GRANT ALL ON util_test.* TO root@localhost;
-- above is a misfeature of mysql 8.0 grant definition
# #endif
