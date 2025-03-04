#
# Copyright (c) 2010, 2016, Oracle and/or its affiliates. All rights
# reserved.
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
This file contains the replicate utility. It is used to establish a
master/slave replication topology among two servers.
"""
from __future__ import print_function

from mysql.utilities.exception import UtilError
from mysql.utilities.common.server import connect_servers
from mysql.utilities.common.replication import Replication
from mysql.utilities.common.replication_ms import ReplicationMultiSource


def setup_replication(master_vals, slave_vals, rpl_user,
                      options, test_db=None):
    """Setup replication among a master and a slave.

    master_vals[in]    Master connection in form user:passwd@host:port:sock
    slave_vals[in]     Slave connection in form user:passwd@host:port:sock
    rpl_user[in]       Replication user in the form user:passwd
    options[in]        dictionary of options (verbosity, quiet, pedantic)
    test_db[in]        Test replication using this database name (optional)
                       default = None
    """
    verbosity = options.get("verbosity", 0)

    conn_options = {
        'src_name': "master",
        'dest_name': 'slave',
        'version': "5.0.0",
        'unique': True,
    }
    servers = connect_servers(master_vals, slave_vals, conn_options)
    master = servers[0]
    slave = servers[1]

    rpl_options = options.copy()
    rpl_options['verbosity'] = verbosity > 0

    # Create an instance of the replication object
    rpl = Replication(master, slave, rpl_options)
    errors = rpl.check_server_ids()
    for error in errors:
        print(error)

    # Check for server_id uniqueness
    if verbosity > 0:
        print("# master id = %s" % master.get_server_id())
        print("#  slave id = %s" % slave.get_server_id())

    errors = rpl.check_server_uuids()
    for error in errors:
        print(error)

    # Check for server_uuid uniqueness
    if verbosity > 0:
        print("# master uuid = %s" % master.get_server_uuid())
        print("#  slave uuid = %s" % slave.get_server_uuid())

    # Check InnoDB compatibility
    if verbosity > 0:
        print("# Checking InnoDB statistics for type and version conflicts.")

    errors = rpl.check_innodb_compatibility(options)
    for error in errors:
        print(error)

    # Checking storage engines
    if verbosity > 0:
        print("# Checking storage engines...")

    errors = rpl.check_storage_engines(options)
    for error in errors:
        print(error)

    # Check master for binary logging
    print("# Checking for binary logging on master...")
    errors = rpl.check_master_binlog()
    if errors != []:
        raise UtilError(errors[0])

    # Setup replication
    print("# Setting up replication...")
    if not rpl.setup(rpl_user, 10):
        raise UtilError("Cannot setup replication.")

    # Test the replication setup.
    if test_db:
        rpl.test(test_db, 10)

    print("# ...done.")


def start_ms_replication(slave_vals, masters_vals, options):
    """Setup replication among a slave and multiple masters.

    slave_vals[in]     Slave server connection dictionary.
    master_vals[in]    List of master server connection dictionaries.
    options[in]        Options dictionary.
    """
    rplms = ReplicationMultiSource(slave_vals, masters_vals, options)
    daemon = options.get("daemon", None)
    if daemon == "start":
        rplms.start()
    elif daemon == "stop":
        rplms.stop()
    elif daemon == "restart":
        rplms.restart()
    else:
        try:
            # Start in foreground
            rplms.start(detach_process=False)
        except KeyboardInterrupt:
            # Stop multi-source replication
            rplms.stop_replication()
