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
copy_db_errors test.
"""
from __future__ import absolute_import

import os
import re

import copy_db

from mysql.utilities.exception import MUTLibError, UtilError


class test(copy_db.test):
    """check errors for copy db
    This test ensures the known error conditions are tested. It uses the
    copy_db test as a parent for setup and teardown methods.
    """

    def check_prerequisites(self):
        return copy_db.test.check_prerequisites(self)

    def setup(self, spawn_servers=True):
        res = copy_db.test.setup(self)
        if not res:
            return res
            # Create users for privilege testing

        version_str = self.server1.get_version()
        if version_str is not None:
            match = re.match(r'^(\d+\.\d+(\.\d+)*).*$', version_str.strip())
            if match:
                version = [int(x) for x in match.group(1).split('.')]
                version = (version + [0])[:3]  # Ensure a 3 elements list
                version_str = "{0:02d}{1:02d}{2:02d}".format(version[0],version[1],version[2])
            else:
                version_str = "000000"
        else:
            version_str = "000000"
        self.server1.version = version_str
        
        version_str = self.server2.get_version()
        if version_str is not None:
            match = re.match(r'^(\d+\.\d+(\.\d+)*).*$', version_str.strip())
            if match:
                version = [int(x) for x in match.group(1).split('.')]
                version = (version + [0])[:3]  # Ensure a 3 elements list
                version_str = "{0:02d}{1:02d}{2:02d}".format(version[0],version[1],version[2])
            else:
                version_str = "000000"
        else:
            version_str = "000000"
        self.server2.version = version_str

        self.server1.server_type = self.server1.get_server_type()
        self.server2.server_type = self.server2.get_server_type()

        self.drop_users()
        self.server1.exec_query("CREATE USER 'joe'@'localhost'")
        self.server1.exec_query("CREATE USER 'sam'@'localhost'")
        self.server1.exec_query("GRANT SELECT on mysql.* TO 'sam'@'localhost'")
        self.server1.exec_query("GRANT SELECT on util_test.* "
                                "TO 'sam'@'localhost'")
        self.server1.exec_query("GRANT SELECT, EVENT, TRIGGER ON util_test.* "
                                "TO 'joe'@'localhost'")
        self.server1.exec_query(
            "GRANT SELECT ON mysql.* TO 'joe'@'localhost'")
        self.server1.exec_query(
            "GRANT SHOW VIEW ON util_test.* TO 'joe'@'localhost'")

        self.server2.exec_query("CREATE USER 'joe'@'localhost'")
        self.server2.exec_query("CREATE USER 'sam'@'localhost'")
        self.server2.exec_query("GRANT SELECT on mysql.* TO 'sam'@'localhost'")
        self.server2.exec_query("GRANT ALL PRIVILEGES ON *.* TO "
                                "'joe'@'localhost' WITH GRANT OPTION")
        self.server2.exec_query("GRANT SUPER ON *.* TO 'joe'@'localhost'")
        if self.server2.get_server_type() == 'MySQL' and \
            self.server2.check_version_compat(8,0,0):
            # because MySQL 8.0 devs are boneheads, need SYSTEM_USER for
            # creating procedures with DEFINER, but need SUPER for creating
            # functions with DEFINER. They call it 'not a bug'
            self.server2.exec_query("GRANT SYSTEM_USER,SET_USER_ID ON *.* TO "
                                    "'joe'@'localhost'")

#        self.server2.exec_query("GRANT CREATE USER ON *.* TO "
#                                "'joe'@'localhost'")

#        self.server2.exec_query("GRANT SELECT ON *.* TO "
#                                "'joe'@'localhost'")
        return True

    def run(self):
        self.res_fname = "result.txt"

        from_conn = "--source={0}".format(
            self.build_connection_string(self.server1)
        )
        to_conn = "--destination={0}".format(
            self.build_connection_string(self.server2)
        )

        cmd = "mysqldbcopy.py --skip-gtid {0}".format(from_conn)

        test_num = 1
        comment = ("Test case {0} - error: no destination "
                   "specified").format(test_num)
        cmd_str = "{0} util_test:util_db_clone".format(cmd)
        res = self.run_test_case(2, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        cmd = "mysqldbcopy.py --skip-gtid {0} {1}".format(from_conn, to_conn)

        test_num += 1
        comment = ("Test case {0} - error: no database "
                   "specified").format(test_num)
        res = self.run_test_case(2, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - error: cannot parse database "
                   "list").format(test_num)
        cmd_str = "{0} wax\t::sad".format(cmd)
        res = self.run_test_case(2, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - error: old database doesn't "
                   "exist").format(test_num)
        cmd_str = "{0} NOT_THERE_AT_ALL:util_db_clone".format(cmd)
        res = self.run_test_case(1, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        cmd = ("mysqldbcopy.py --skip-gtid {0} "
               "--source=nope:nada@localhost:3306").format(to_conn)

        test_num += 1
        comment = ("Test case {0} - error: cannot connect to "
                   "source").format(test_num)
        cmd_str = "{0} util_test:util_db_clone".format(cmd)
        res = self.run_test_case(1, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        cmd = ("mysqldbcopy.py --skip-gtid {0} "
               "--destination=nope:nada@localhost:3306").format(from_conn)

        test_num += 1
        comment = ("Test case {0} - error: cannot connect to "
                   "destination").format(test_num)
        cmd_str = "{0} util_test:util_db_clone".format(cmd)
        res = self.run_test_case(1, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        from_conn = "--source=sam@localhost:{0}".format(self.server1.port)
        # Watchout for Windows: it doesn't use sockets!
        if os.name == "posix" and self.server2.socket is not None:
            to_conn = ("--destination=sam@localhost:{0}:"
                       "{1}").format(self.server2.port, self.server2.socket)
        else:
            to_conn = ("--destination=sam@localhost:"
                       "{0}").format(self.server2.port)

        cmd = "mysqldbcopy.py --skip-gtid {0} {1}".format(from_conn, to_conn)

        test_num += 1
        comment = ("Test case {0} - users with minimal "
                   "privileges").format(test_num)
        cmd_str = "{0} util_test:util_db_clone".format(cmd)
        res = self.run_test_case(1, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        self.server1.exec_query("GRANT SELECT ON util_test.* TO 'sam'@'localhost'")
        from_conn = "--source=sam@localhost:{0}".format(self.server1.port)
        if os.name == "posix" and self.server2.socket is not None:
            to_conn = ("--destination=joe@localhost:{0}:"
                       "{1}").format(self.server2.port, self.server2.socket)
        else:
            to_conn = ("--destination=joe@localhost:"
                       "{0}").format(self.server2.port)
        cmd = "mysqldbcopy.py --skip-gtid {0} {1}".format(from_conn, to_conn)

        self.server1.exec_query("GRANT SHOW VIEW ON util_test.* TO 'sam'@'localhost'")

        test_num += 1
        comment = ("Test case {0} - source user not enough privileges "
                   "needed").format(test_num)
        cmd_str = "{0} util_test:util_db_clone --drop-first".format(cmd)
        res = self.run_test_case(1, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Give Sam some privileges on source and retest until copy works
        self.server1.exec_query("GRANT SELECT ON "
                                "*.* TO 'sam'@'localhost'")

        test_num += 1
        comment = ("Test case {0} - source user has some privileges "
                   "needed").format(test_num)
        res = self.run_test_case(1, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        self.server1.exec_query("GRANT TRIGGER ON util_test.* "
                                "TO 'sam'@'localhost'")

        test_num += 1
        comment = ("Test case {0} - source user has some privileges "
                   "needed").format(test_num)
        res = self.run_test_case(1, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        self.server1.exec_query("GRANT EVENT ON util_test.* "
                                "TO 'sam'@'localhost'")
        
        test_num += 1
        comment = ("Test case {0} - source user has privileges "
                   "needed").format(test_num)
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        to_conn = ("--destination=sam@localhost:"
                   "{0}").format(self.server2.port)
        cmd = "mysqldbcopy.py --skip-gtid {0} {1}".format(from_conn, to_conn)

        self.server2.exec_query("GRANT SELECT ON *.* "
                                "TO 'sam'@'localhost'")
        test_num += 1
        comment = ("Test case {0} - dest user not enough privileges "
                   "needed").format(test_num)
        cmd_str = "{0} util_test:util_db_clone --drop-first".format(cmd)
        res = self.run_test_case(1, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Give some privileges on source and retest until copy works
        self.server2.exec_query("GRANT CREATE USER ON *.* TO "
                                "'sam'@'localhost'")

        test_num += 1
        comment = ("Test case {0} - dest user has some privileges "
                   "needed").format(test_num)
        res = self.run_test_case(1, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        self.server2.exec_query("GRANT EVENT, TRIGGER ON *.* TO "
                                "'sam'@'localhost' WITH GRANT OPTION")

        test_num += 1
        comment = ("Test case {0} - dest user has some privileges "
                   "needed").format(test_num)
        res = self.run_test_case(1, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        self.server2.exec_query("GRANT ALL PRIVILEGES ON util_db_clone.* TO "
                                "'sam'@'localhost' WITH GRANT OPTION")
        self.server2.exec_query("GRANT SUPER ON *.* TO 'sam'@'localhost'")
        if self.server2.get_server_type() == 'MySQL' and \
            self.server2.check_version_compat(8,0,0):
            self.server2.exec_query("GRANT SET_USER_ID, SYSTEM_USER ON *.* "
                                    "TO 'sam'@'localhost'")

        test_num += 1
        comment = ("Test case {0} - dest user has privileges "
                   "needed").format(test_num)
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = "Test case {0} - cannot parse --source".format(test_num)
        cmd_str = ("mysqldbcopy.py --skip-gtid --source=rocks_rocks_rocks {0}"
                   " util_test:util_db_clone --drop-first").format(to_conn)
        res = self.run_test_case(2, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = "Test case {0} - cannot parse --destination".format(test_num)
        cmd_str = ("mysqldbcopy.py --skip-gtid {0} util_test:util_db_clone "
                   "--destination=rocks_rocks_rocks --drop-first"
                   "").format(from_conn)
        res = self.run_test_case(2, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = "Test case {0} - no destination specified".format(test_num)
        cmd_str = ("mysqldbcopy.py --skip-gtid --source=rocks_rocks_rocks "
                   "util_test:util_db_clone --drop-first")
        res = self.run_test_case(2, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = "Test case {0} - no database specified".format(test_num)
        cmd_str = "mysqldbcopy.py --skip-gtid {0} {1}".format(to_conn,
                                                              from_conn)
        res = self.run_test_case(2, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = "Test case {0} - new storage engine missing".format(test_num)
        cmd_str = ("mysqldbcopy.py --skip-gtid {0} {1} util_test:util_db_clone"
                   " --drop-first --new-storage-engine=NOTTHERE"
                   "").format(to_conn, from_conn)
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - default storage engine "
                   "missing").format(test_num)
        cmd_str = ("mysqldbcopy.py --skip-gtid {0} {1} util_test:util_db_clone"
                   " --default-storage-engine=NOPENOTHERE"
                   " --drop-first").format(to_conn, from_conn)
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = "Test case {0} - database listed and --all".format(test_num)
        cmd_str = ("mysqldbcopy.py --skip-gtid {0} {1} util_test:util_db_clone"
                   " --drop-first --all").format(to_conn, from_conn)
        res = self.run_test_case(2, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        cmd = "mysqldbcopy.py --skip-gtid {0} {1} util_test".format(to_conn,
                                                                    from_conn)

        # Check --rpl option errors
        test_num += 1
        comment = ("Test case {0} - error: {1} but no "
                   "--rpl").format(test_num, "--rpl-user=root")
        cmd_str = "{0} --rpl-user=root".format(cmd)
        res = self.run_test_case(2, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = "Test case {0} - Invalid --character-set".format(test_num)
        cmd_str = ("mysqldbcopy.py {0} {1} --all "
                   "--character-set=unsupported_charset"
                   "".format(from_conn, to_conn))
        res = self.run_test_case(1, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - error: invalid multiprocess "
                   "value.").format(test_num)
        cmd_str = "{0} --multiprocess=0.5".format(cmd)
        res = self.run_test_case(2, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - error: multiprocess value smaller than "
                   "zero.").format(test_num)
        cmd_str = "{0} --multiprocess=-1".format(cmd)
        res = self.run_test_case(2, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        try:
            # Revoke all privileges to joe@localhost in destination db
            self.server2.exec_query("REVOKE ALL PRIVILEGES, GRANT OPTION FROM "
                                    "'joe'@'localhost'")
            # Add all privileges needed for joe@localhost in destination db
            self.server2.exec_query("GRANT SELECT, CREATE, ALTER, INSERT, "
                                    "UPDATE, EXECUTE, DROP, REFERENCES, "
                                    "LOCK TABLES ON `util_db_clone`.* TO "
                                    "'joe'@'localhost'")
            self.server1.exec_query("GRANT SELECT ON *.* TO 'joe'@'localhost'")
        except UtilError as err:
            raise MUTLibError("Failed to execute query: "
                              "{0}".format(err.errmsg))
        from_conn = "--source=joe@localhost:{0}".format(self.server1.port)
        to_conn = "--destination=joe@localhost:{0}".format(self.server2.port)
        comment = ("Test case {0} - error: dest user is missing SUPER "
                   "privilege").format(test_num)
        cmd = ("mysqldbcopy.py --skip-gtid --skip=grants --drop-first {0} "
               "{1} util_test:util_db_clone".format(from_conn, to_conn))
        res = self.run_test_case(1, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        try:
            self.server2.exec_query("GRANT SUPER ON *.* TO 'joe'@'localhost'")
            if self.server2.get_server_type() == 'MySQL' and \
               self.server2.check_version_compat(8,0,0):
                self.server2.exec_query("GRANT SYSTEM_USER,SET_USER_ID ON *.* "
                                        "TO 'joe'@'localhost'")

        except UtilError as err:
            raise MUTLibError("Failed to execute query: "
                              "{0}".format(err.errmsg))
        comment = ("Test case {0} - error: dest user is missing CREATE VIEW "
                   "privilege").format(test_num)
        res = self.run_test_case(1, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        try:
            self.server2.exec_query("GRANT CREATE VIEW ON "
                                    "`util_db_clone`.* TO 'joe'@'localhost'")
        except UtilError as err:
            raise MUTLibError("Failed to execute query: "
                              "{0}".format(err.errmsg))
        comment = ("Test case {0} - error: dest user is missing CREATE "
                   "ROUTINE privilege").format(test_num)
        res = self.run_test_case(1, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        try:
            self.server2.exec_query("GRANT CREATE ROUTINE ON "
                                    "`util_db_clone`.* TO 'joe'@'localhost'")
        except UtilError as err:
            raise MUTLibError("Failed to execute query: "
                              "{0}".format(err.errmsg))
        comment = ("Test case {0} - error: dest user is missing EVENT "
                   "privilege").format(test_num)
        res = self.run_test_case(1, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        try:
            self.server2.exec_query("GRANT EVENT ON "
                                    "`util_db_clone`.* TO 'joe'@'localhost'")
        except UtilError as err:
            raise MUTLibError("Failed to execute query: "
                              "{0}".format(err.errmsg))
        comment = ("Test case {0} - error: dest user is missing TRIGGER "
                   "privilege").format(test_num)
        res = self.run_test_case(1, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        try:
            self.server2.exec_query("GRANT TRIGGER ON `util_db_clone`.* TO "
                                    "'joe'@'localhost'")
        except UtilError as err:
            raise MUTLibError("Failed to execute query: "
                              "{0}".format(err.errmsg))
        comment = ("Test case {0} - dest user has privileges "
                   "needed").format(test_num)
        
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        try:
            self.server1.exec_query("CREATE TABLE util_test.b1 (a int not null"
                                    ", blobby tinytext not null)")
            
        except UtilError as err:
            raise MUTLibError("Failed to execute query: "
                              "{0}".format(err.errmsg))
        comment = "Test case {0} - blobs with not null".format(test_num)
        res = self.run_test_case(1, cmd, comment) #
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        to_conn = "--destination={0}".format(
            self.build_connection_string(self.server2)
        )
        cmd = ("mysqldbcopy.py --skip-gtid --skip=grants --drop-first {0} "
               "{1} util_test:util_db_clone --not".format(from_conn, to_conn))
        comment = "Test case {0} - allow blobs with not null".format(test_num)
        res = self.run_test_case(0, cmd, comment)  
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Mask socket for destination server
        self.replace_result("# Destination: root@localhost:",
                            "# Destination: root@localhost:[] ... connected\n")
        self.replace_result("# Destination: joe@localhost:",
                            "# Destination: joe@localhost:[] ... connected\n")
        self.replace_result("# Destination: sam@localhost:",
                            "# Destination: sam@localhost:[] ... connected\n")

        # Mask known source and destination host name.
        self.replace_substring("on localhost", "on XXXX-XXXX")
        self.replace_substring("on [::1]", "on XXXX-XXXX")

        self.replace_any_result(["ERROR: Can't connect",
                                 "ERROR: Access denied for user"],
                                "ERROR: Can't connect to XXXX\n")
        # Replace error code.
        self.replace_any_result(["Error 1045", "Error 2003",
                                 "Error Can't connect to MySQL server on",
                                 "Error Access denied for user"],
                                "Error XXXX: Access denied\n")

        # Ignore GTID messages (skipping GTIDs in this test)
        self.remove_result("# WARNING: The server supports GTIDs")

        # Replace connection errors
        self.replace_result("mysqldbcopy: error: Source connection "
                            "values invalid",
                            "mysqldbcopy: error: Source connection "
                            "values invalid\n")
        self.replace_result("mysqldbcopy: error: Destination connection "
                            "values invalid",
                            "mysqldbcopy: error: Destination connection "
                            "values invalid\n")
        return True

    def get_result(self):
        return self.compare_pp(__name__, self.results,
                               self.server1, self.server2)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def drop_users(self):
        """Drops all users created.
        """
        try:
            self.server1.exec_query("DROP USER 'joe'@'localhost'")
        except UtilError:
            pass
        try:
            self.server1.exec_query("DROP USER 'sam'@'localhost'")
        except UtilError:
            pass
        try:
            self.server2.exec_query("DROP USER 'joe'@'localhost'")
        except UtilError:
            pass
        try:
            self.server2.exec_query("DROP USER 'sam'@'localhost'")
        except UtilError:
            pass

    def cleanup(self):
        self.drop_users()
        res = copy_db.test.cleanup(self)
        return res
