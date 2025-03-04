#
# Copyright (c) 2010, 2016, Oracle and/or its affiliates. All rights reserved.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA 02110-1301 USA
#

"""
copy_db test.
"""

from builtins import range
import os

import mutlib

from mysql.utilities.common.sql_transform import quote_with_backticks
from mysql.utilities.exception import MUTLibError
from mysql.utilities.exception import UtilDBError
from mysql.utilities.exception import UtilError


class test(mutlib.System_test):
    """simple db copy
    This test executes copy database test cases among two servers.
    """

    server1 = None
    server2 = None
    need_server = False

    def check_prerequisites(self):
        self.check_gtid_unsafe()
        # Need at least one server.
        self.server1 = None
        self.server2 = None
        try:
            self.servers.spawn_new_servers(3)
        except MUTLibError as err:
            raise MUTLibError("Cannot spawn needed servers: {0}"
                              "".format(err.errmsg))

        self.server1 = self.servers.get_server(1)
        self.server2 = self.servers.get_server(2)
        
        return self.server1 and self.server2

    # pylint: disable=W0221
    def setup(self, spawn_servers=True):
        self.drop_all()
        data_file = os.path.normpath("./std_data/basic_data.sql")
        try:
            self.server1.read_and_exec_SQL(data_file, self.debug)
        except UtilError as err:
            raise MUTLibError("Failed to read commands from file {0}: {1}"
                              "".format(data_file, err.errmsg))

        # Create backtick database (with weird names)
        data_file_backticks = os.path.normpath("./std_data/backtick_data.sql")
        try:
            self.server1.read_and_exec_SQL(data_file_backticks, self.debug)
        except UtilError as err:
            raise MUTLibError("Failed to read commands from file {0}: {1}"
                              "".format(data_file_backticks, err.errmsg))

        # Create database with test VIEWS.
        data_file_views = os.path.normpath("./std_data/db_copy_views.sql")
        try:
            self.server1.read_and_exec_SQL(data_file_views, self.debug)
        except UtilError as err:
            raise MUTLibError("Failed to read commands from file "
                              "{0}: {1}".format(data_file_views, err.errmsg))

        # Load database with with blobs and insert data.
        data_file_blobs = os.path.normpath("./std_data/blob_data.sql")
        try:
            self.server1.read_and_exec_SQL(data_file_blobs, self.debug)
        except UtilError as err:
            raise MUTLibError("Failed to read commands from file {0}: {1}"
                              "".format(data_file_blobs, err.errmsg))

        # Create user 'joe'@'localhost' in source server
        try:
            self.server1.exec_query("CREATE USER 'joe'@'localhost'")
        except UtilError as err:
            raise MUTLibError("Failed to create user: {0}".format(err.errmsg))

        # Create user 'joe'@'localhost' in destination server
        try:
            self.server2.exec_query("CREATE USER 'joe'@'localhost'")
        except UtilError as err:
            raise MUTLibError("Failed to create user: {0}".format(err.errmsg))

        return True

    def run(self):
        self.res_fname = "result.txt"

        from_conn = "--source={0}".format(
            self.build_connection_string(self.server1)
        )
        to_conn = "--destination={0}".format(
            self.build_connection_string(self.server2)
        )

        cmd = "mysqldbcopy.py --skip-gtid {0} {1} ".format(from_conn, to_conn)

        test_num = 1
        comment = ("Test case {0} - copy a sample database X:Y"
                   "").format(test_num)
        cmd_str = "{0} util_test:util_db_clone".format(cmd)
        res = self.exec_util(cmd_str, self.res_fname)
        self.results.append(res)
        if res != 0:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = "Test case {0} - copy a sample database X".format(test_num)
        cmd_str = "{0} util_test".format(cmd)
        res = self.exec_util(cmd_str, self.res_fname)
        self.results.append(res)
        if res != 0:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - copy a sample database with blobs "
                   "X:Y".format(test_num))
        cmd_str = "{0} blob_test:blob_test_clone".format(cmd)
        res = self.exec_util(cmd_str, self.res_fname)
        self.results.append(res)
        if res != 0:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - copy using different engine"
                   "").format(test_num)
        cmd_str = ("{0} util_test:util_db_clone --drop-first "
                   "--new-storage-engine=MEMORY").format(cmd)
        res = self.exec_util(cmd_str, self.res_fname)
        self.results.append(res)
        if res != 0:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - copy using "
                   "multiprocessing").format(test_num)
        cmd_str = "{0} util_test:util_test_multi --multiprocess=2".format(cmd)
        res = self.exec_util(cmd_str, self.res_fname)
        self.results.append(res)
        if res != 0:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - copy blobs using "
                   "multiprocessing").format(test_num)
        cmd_str = "{0} blob_test:blob_test_multi --multiprocess=2".format(cmd)
        res = self.exec_util(cmd_str, self.res_fname)
        self.results.append(res)
        if res != 0:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - copy a sample database X:Y with weird "
                   "names (backticks)".format(test_num))
        # Set input parameter with appropriate quotes for the OS
        if os.name == 'posix':
            cmd_arg = "'`db``:db`:`db``:db_clone`'"
        else:
            cmd_arg = '"`db``:db`:`db``:db_clone`"'
        cmd = "mysqldbcopy.py {0} {1} {2}".format(from_conn, to_conn, cmd_arg)
        res = self.exec_util(cmd, self.res_fname)
        self.results.append(res)
        if res != 0:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - copy a sample database X with weird "
                   "names (backticks)".format(test_num))
        # Set input parameter with appropriate quotes for the OS
        if os.name == 'posix':
            cmd_arg = "'`db``:db`'"
        else:
            cmd_arg = '"`db``:db`"'
        cmd = "mysqldbcopy.py {0} {1} {2}".format(from_conn, to_conn, cmd_arg)
        res = self.exec_util(cmd, self.res_fname)
        self.results.append(res)
        if res != 0:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - copy a sample database with views"
                   "".format(test_num))
        cmd = "mysqldbcopy.py {0} {1} {2}".format(
            from_conn, to_conn, "views_test:views_test_clone")
        res = self.exec_util(cmd, self.res_fname)
        self.results.append(res)
        if res != 0:
            raise MUTLibError("{0}: failed".format(comment))

        # These two DB and tables does not contains any row, and are used
        # to test DB copy of default character set and collation.
        # was not move to ./std_data/basic_data.sql to avoid warning
        # "A partial copy from a server that has GTIDs.." messages
        # when setup is invoke from subclasses and other tests and
        # to avoid the creation of an additional file.
        queries = [("CREATE DATABASE util_test_default_collation "
                    "DEFAULT COLLATE utf8_general_ci"),
                   ("CREATE TABLE util_test_default_collation.t1 "
                    "(a char(30)) ENGINE=MEMORY"),
                   ("CREATE DATABASE util_test_default_charset "
                    "DEFAULT CHARACTER SET utf8"),
                   ("CREATE TABLE util_test_default_charset.t1 "
                    "(a char(30)) ENGINE=MEMORY")]
        for query in queries:
            self.server1.exec_query(query)

        test_num += 1
        dest_c = "--destination={0}".format(
            self.build_connection_string(self.server1))
        comment = "Test case {0} - copydb default collation".format(test_num)
        dbs = ("util_test_default_collation:"
               "util_test_default_collation_copy")
        cmd = ("mysqldbcopy.py --skip-gtid {0} {1} {2}"
               "".format(from_conn, dest_c, dbs))
        res = self.exec_util(cmd, self.res_fname)
        self.results.append(res)
        if res != 0:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = "Test case {0} - copydb default charset".format(test_num)
        dbs = ("util_test_default_charset:"
               "util_test_default_charset_copy")
        cmd = ("mysqldbcopy.py --skip-gtid {0} {1} {2}"
               "".format(from_conn, dest_c, dbs))
        res = self.exec_util(cmd, self.res_fname)
        self.results.append(res)
        if res != 0:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        try:
            # Grant ALL on `util_test` for user 'joe'@'localhost' on source
            self.server1.exec_query("GRANT ALL PRIVILEGES ON `util_test`.* "
                                    "TO 'joe'@'localhost'")

            # Revoke all privileges to 'joe'@'localhost' in destination
            self.server2.exec_query("REVOKE ALL PRIVILEGES, GRANT OPTION FROM "
                                    "'joe'@'localhost'")

            # Add all privileges needed for 'joe'@'localhost' in destination db
            self.server2.exec_query("GRANT SELECT, CREATE, ALTER, INSERT, "
                                    "UPDATE, EXECUTE, DROP, LOCK TABLES, "
                                    "EVENT, TRIGGER, CREATE ROUTINE, "
                                    "REFERENCES, CREATE VIEW ON "
                                    "`util_db_privileges`.* TO "
                                    "'joe'@'localhost'")
            
            # Change DEFINER in procedures and functions on the source server
            # for mysql 8.0 cannot alter/update DEFINER, have to re-define (ugh)
            self.server1.exec_query("DROP PROCEDURE util_test.p1")
            self.server1.exec_query("CREATE DEFINER=`joe`@`localhost` "
                                    "PROCEDURE util_test.p1(p1 CHAR(20)) "
                                    'INSERT INTO util_test.t1 VALUES ("50")')
            self.server1.exec_query("DROP FUNCTION util_test.f1")
            self.server1.exec_query("CREATE DEFINER=`joe`@`localhost` "
                                    "FUNCTION util_test.f1() "
                                    "RETURNS INT DETERMINISTIC RETURN (SELECT 1)")
            self.server1.exec_query("DROP FUNCTION util_test.f2")
            self.server1.exec_query("CREATE DEFINER=`joe`@`localhost` "
                                    "FUNCTION util_test.f2(base_price DECIMAL(20,2) UNSIGNED, "
                                    "tax_percentage DECIMAL(3,0) UNSIGNED) "
                                    "RETURNS DECIMAL (21,2) UNSIGNED DETERMINISTIC "
                                    "RETURN base_price + base_price*(tax_percentage/100)")
                                
            self.server1.exec_query("DROP EVENT util_test.e1")
            self.server1.exec_query("CREATE DEFINER=`joe`@`localhost` "
                                    "EVENT util_test.e1 "
                                    "ON SCHEDULE EVERY 1 YEAR DISABLE "
                                    'DO DELETE FROM util_test.t1 WHERE a = "not there"')


            # Change DEFINER in the views on the source server
            query = """
                SELECT CONCAT("ALTER DEFINER=`joe`@`localhost` VIEW ",
                table_schema, ".", table_name, " AS ", view_definition)
                FROM information_schema.views WHERE
                table_schema='util_test'
            """
            res = self.server1.exec_query(query)
            for row in res:
                self.server1.exec_query(row[0])

            # Change DEFINER in the triggers on the source server
            self.server1.exec_query("DROP TRIGGER util_test.trg")
            self.server1.exec_query("CREATE DEFINER=`joe`@`localhost` "
                                    "TRIGGER util_test.trg AFTER INSERT ON "
                                    "util_test.t1 FOR EACH ROW INSERT INTO "
                                    "util_test.t2 "
                                    "VALUES('Test objects count')")
        except UtilError as err:
            raise MUTLibError("Failed to execute query: "
                              "{0}".format(err.errmsg))


        self.server2.exec_query("SET GLOBAL log_bin_trust_function_creators=1")
        
        to_conn = "--destination=joe@localhost:{0}".format(self.server2.port)
        comment = ("Test case {0} - copy using a user without SUPER privilege"
                   "").format(test_num)
        cmd = ("mysqldbcopy.py --skip-gtid --skip=grants --drop-first {0} "
               "{1} util_test:util_db_privileges".format(from_conn, to_conn))

        res = self.exec_util(cmd, self.res_fname)
        self.results.append(res)
        if res != 0:
            raise MUTLibError("{0}: failed".format(comment))

        self.server2.exec_query("SET GLOBAL log_bin_trust_function_creators=1")

        
        test_num += 1
        # Change SQL_MODE to 'NO_BACKSLASH_ESCAPES' in the destination server
        try:
            previous_sql_mode = self.server2.select_variable("SQL_MODE")
            self.server2.exec_query("SET @@GLOBAL.SQL_MODE="
                                    "'NO_BACKSLASH_ESCAPES'")
        except UtilError as err:
            raise MUTLibError("Failed to change SQL_MODE: "
                              "{0}".format(err.errmsg))

        comment = ("Test case {0} - Copy database with blobs and the "
                   "destination server with SQL_MODE='NO_BACKSLASH_ESCAPES'"
                   "").format(test_num)
        to_conn = "--destination={0}".format(
            self.build_connection_string(self.server2))
        cmd = ("mysqldbcopy.py --skip-gtid {0} {1} {2}".format(
            from_conn, to_conn, "blob_test:blob_test_no_backslash_escapes"))
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Restore previous SQL_MODE in the destination server
        try:
            self.server2.exec_query("SET @@GLOBAL.SQL_MODE='{0}'"
                                    "".format(previous_sql_mode))
        except UtilError as err:
            raise MUTLibError("Failed to restore SQL_MODE: "
                              "{0}".format(err.errmsg))

        test_num += 1
        # try copying a table with 0 auto_increment value
        try:
            previous_sql_mode = self.server1.select_variable("SQL_MODE")
            self.server1.exec_query("SET @@GLOBAL.SQL_MODE="
                                    "'NO_AUTO_VALUE_ON_ZERO'")
            self.server1.exec_query("CREATE TABLE util_test.tt0 "
                                    "(a int auto_increment primary key, "
                                    "b char(10))")
            self.server1.exec_query("INSERT INTO util_test.tt0 "
                                    "VALUES (0, 'a'), (null, 'b')")
        except UtilError as err:
            raise MUTLibError("Failed to change setup 0 auto_increment: "
                              "{0}".format(err.errmsg))

        comment = ("Test case {0} - Copy database with 0 in the "
                   "auto_increment column").format(test_num)
        to_conn = "--destination={0} --drop --skip=views".format(
            self.build_connection_string(self.server2))
        cmd = ("mysqldbcopy.py --skip-gtid {0} {1} {2}".format(
            from_conn, to_conn, "util_test"))
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        self.server1.exec_query("DROP TABLE util_test.tt0")
        self.server2.exec_query("DROP TABLE util_test.tt0")

        # Restore previous SQL_MODE in the source server
        try:
            self.server1.exec_query("SET @@GLOBAL.SQL_MODE='{0}'"
                                    "".format(previous_sql_mode))
        except UtilError as err:
            raise MUTLibError("Failed to restore SQL_MODE: "
                              "{0}".format(err.errmsg))

        return True

    def get_result(self):
        msg = []
        copied_db_on_server2 = ['util_db_clone', 'util_test',
                                'util_test_multi', 'db`:db_clone',
                                'db`:db', 'views_test_clone',
                                'util_db_privileges', 'blob_test_clone',
                                'blob_test_multi',
                                'blob_test_no_backslash_escapes']
        copied_db_on_server1 = ["util_test_default_collation_copy",
                                "util_test_default_charset_copy"]

        # Check databases existence.
        query = "SHOW DATABASES LIKE '{0}'"
        for db in copied_db_on_server2:
            try:
                res = self.server2.exec_query(query.format(db))
                try:
                    if res[0][0] != db:
                        msg.append("Database {0} not found in {1}.\n"
                                   "".format(db, self.server2.role))
                except IndexError:
                    msg.append("Database {0} not found in {1}.\n"
                               "".format(db, self.server2.role))
            except UtilDBError as err:
                raise MUTLibError(err.errmsg)
        for db in copied_db_on_server1:
            try:
                res = self.server1.exec_query(query.format(db))
                try:
                    if res[0][0] != db:
                        msg.append("Database {0} not found in {1}.\n"
                                   "".format(db, self.server1.role))
                except IndexError:
                    msg.append("Database {0} not found in {1}.\n"
                               "".format(db, self.server1.role))
            except UtilDBError as err:
                raise MUTLibError(err.errmsg)

        # Compare table checksums.
        dbs2compare = [
            ('`util_test`', ('`util_test`', '`util_db_clone`',
                             '`util_test_multi`', '`util_db_privileges`')),
            ('`db``:db`', ('`db``:db`', '`db``:db_clone`')),
            ('`views_test`', ('`views_test_clone`',)),
            ('blob_test', ('blob_test_clone', 'blob_test_multi',
                           'blob_test_no_backslash_escapes'))
        ]
        for cmp_data in dbs2compare:
            self.server1.exec_query("USE {0}".format(cmp_data[0]))
            res = self.server1.exec_query("SHOW TABLES")
            for row in res:
                table = quote_with_backticks(
                    row[0],
                    self.server1.select_variable("SQL_MODE")
                )
                base_checksum = self.server1.exec_query(
                    "CHECKSUM TABLE {0}".format(table)
                )[0][1]
                for i in range(len(cmp_data[1])):
                    tbl_checksum = self.server2.exec_query(
                        "CHECKSUM TABLE {0}.{1}".format(cmp_data[1][i],
                                                        table)
                    )[0][1]
                    if tbl_checksum != base_checksum:
                        msg.append("Different table checksum for table "
                                   "{0}.{1}, got {2} expected "
                                   "{3}.".format(cmp_data[1][i], table,
                                                 tbl_checksum, base_checksum))
                        res1=self.server1.exec_query("SELECT * FROM {0}".format(table))
                        print(" ")
                        print("base:\n",res1)
                        res2=self.server2.exec_query("SELECT * FROM {0}.{1}".format(cmp_data[1][i],table))
                        print("mod:\n",res2)
                                                     

        # Check attributes (character set and collation).
        qry_db = ("SELECT {0} FROM INFORMATION_SCHEMA.SCHEMATA "
                  "WHERE SCHEMA_NAME = '{1}'")
        qry_tb = ("SELECT CCSA.{0} "
                  "FROM information_schema.`TABLES` T, "
                  "information_schema.`COLLATION_CHARACTER_SET_APPLICABILITY`"
                  " CCSA WHERE CCSA.collation_name = T.table_collation "
                  " AND T.table_schema = '{1}' AND T.table_name = 't1'")
        check_db_info_on_server1 = [("util_test_default_collation_copy",
                                     "DEFAULT_COLLATION_NAME",
                                     "utf8_general_ci", "COLLATION_NAME"), (
                                         "util_test_default_charset_copy",
                                         "DEFAULT_CHARACTER_SET_NAME", "utf8",
                                         "CHARACTER_SET_NAME")]
        for db in check_db_info_on_server1:
            try:
                res = self.server1.exec_query(qry_db.format(db[1], db[0]))
                try:
                    if res[0][0] != db[2]:
                        msg.append("For database {0} attribute {1} copy "
                                   "failed, got {2} expected {3}.\n"
                                   "".format(db[0], db[1], res[0][0], db[2]))
                except IndexError:
                    msg.append("For database {0} no value found for attribute "
                               "{1}.\n".format(db[0], db[1]))

                res = self.server1.exec_query(qry_tb.format(db[3], db[0]))
                try:
                    if res[0][0] != db[2]:
                        msg.append("For table {0} attribute {1} copy "
                                   "failed, got {2} expected {3}.\n"
                                   "".format(db[0], db[3], res[0][0], db[2]))
                except IndexError:
                    msg.append("For table {0} no value found for attribute "
                               "{1}.\n".format(db[0], db[3]))
            except UtilDBError as err:
                raise MUTLibError(err.errmsg)
        if msg:
            return False, ("Result failure.\n", "\n".join(msg))
        else:
            return True, ""

    def record(self):
        # Not a comparative test, returning True
        return True

    def drop_all(self):
        """Drops all databases and users created.
        """
        # this DBs may not be created on subclasses.
        db_drops_on_server1 = ["util_test", 'db`:db', 'views_test',
                               "util_test_default_charset",
                               "util_test_default_collation",
                               "util_test_default_charset_copy",
                               "util_test_default_collation_copy",
                               "blob_test"]
        for db in db_drops_on_server1:
            self.drop_db(self.server1, db)

        db_drops_on_server2 = ["util_test", 'db`:db', "util_db_clone",
                               'db`:db_clone', "views_test_clone",
                               "blob_test_clone", "blob_test_multi",
                               "blob_test_no_backslash_escapes"]
        for db in db_drops_on_server2:
            self.drop_db(self.server2, db)

        drop_user = ["DROP USER 'joe'@'user'", "DROP USER 'joe_wildcard'@'%'",
                     "DROP USER 'joe'@'localhost'"]
        for drop in drop_user:
            try:
                self.server1.exec_query(drop)
                self.server2.exec_query(drop)
            except UtilError:
                pass
        return True

    def cleanup(self):
        if self.res_fname:
            os.unlink(self.res_fname)
        return self.drop_all()
