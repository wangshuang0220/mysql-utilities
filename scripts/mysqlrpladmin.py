#!/usr/bin/env python
#
# Copyright (c) 2012, 2013, Oracle and/or its affiliates. All rights reserved.
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
This file contains the replication slave administration utility. It is used to
perform replication operations on one or more slaves.
"""

from mysql.utilities.common.tools import check_python_version

# Check Python version compatibility
check_python_version()

import logging
import os.path
import sys

from mysql.utilities.exception import UtilError, UtilRplError
from mysql.utilities.common.ip_parser import parse_connection
from mysql.utilities.common.messages import SCRIPT_THRESHOLD_WARNING
from mysql.utilities.common.options import add_format_option, add_verbosity
from mysql.utilities.common.options import add_failover_options, add_rpl_user
from mysql.utilities.common.options import check_server_lists
from mysql.utilities.common.options import CaseInsensitiveChoicesOption
from mysql.utilities.common.messages import (PARSE_ERR_OPT_INVALID_CMD_TIP,
                                             PARSE_ERR_OPTS_REQ_BY_CMD,
                                             PARSE_ERR_SLAVE_DISCO_REQ,
                                             PARSE_ERR_SLAVE_DISCO_EXC,
                                             WARN_OPT_NOT_REQUIRED,
                                             WARN_OPT_NOT_REQUIRED_ONLY_FOR,
                                             ERROR_SAME_MASTER,
                                             ERROR_MASTER_IN_SLAVES,
                                             SLAVES, CANDIDATES)
from mysql.utilities.common.options import UtilitiesParser
from mysql.utilities.common.server import Server, check_hostname_alias
from mysql.utilities.common.topology import parse_failover_connections
from mysql.utilities.command.rpl_admin import RplCommands, purge_log
from mysql.utilities.command.rpl_admin import get_valid_rpl_commands
from mysql.utilities.command.rpl_admin import get_valid_rpl_command_text
from mysql.utilities.exception import FormatError
from mysql.utilities import VERSION_FRM


class MyParser(UtilitiesParser):
    def format_epilog(self, formatter):
        return self.epilog

# Constants
NAME = "MySQL Utilities - mysqlrpladmin "
DESCRIPTION = "mysqlrpladmin - administration utility for MySQL replication"
USAGE = "%prog --slaves=root@localhost:3306 <command>"
_DATE_FORMAT = '%Y-%m-%d %H:%M:%S %p'

# Setup the command parser
parser = MyParser(
    version=VERSION_FRM.format(program=os.path.basename(sys.argv[0])),
    description=DESCRIPTION,
    usage=USAGE,
    add_help_option=False,
    option_class=CaseInsensitiveChoicesOption,
    epilog=get_valid_rpl_command_text())

# Default option to provide help information
parser.add_option("--help", action="help", help="display this help message "
                  "and exit")

# Setup utility-specific options:
add_failover_options(parser)

# Connection information for the master
# Connect information for candidate server for switchover
parser.add_option("--new-master", action="store", dest="new_master", default=None,
                  type="string", help="connection information for the "
                  "slave to be used to replace the master for switchover, "
                  "in the form: <user>[:<password>]@<host>[:<port>][:<socket>]"
                  " or <login-path>[:<port>][:<socket>]. Valid only with "
                  "switchover command.")

# Force the execution of the command, ignoring some errors
parser.add_option("--force", action="store_true", dest="force",
                  help="ignore prerequisite check results or some "
                  "inconsistencies found (e.g. errant transactions on slaves) "
                  "and execute action")

# Output format
add_format_option(parser, "display the output in either grid (default), "
                  "tab, csv, or vertical format", None)

# Add demote option
parser.add_option("--demote-master", action="store_true", dest="demote",
                  help="make master a slave after switchover.")

# Add no-health option
parser.add_option("--no-health", action="store_true", dest="no_health",
                  help="turn off health report after switchover or failover.")

# Add verbosity mode
add_verbosity(parser, True)

# Replication user and password
add_rpl_user(parser, None)

# Now we process the rest of the arguments.
opt, args = parser.parse_args()

# Check for invalid command
if len(args) > 1:
    parser.error("You can only specify one command to execute at a time.")
elif len(args) == 0:
    parser.error("You must specify a command to execute.")

# At least one of the options --discover-slaves-login or --slaves is required.
if not opt.discover and not opt.slaves:
    parser.error(PARSE_ERR_SLAVE_DISCO_REQ)

# --discover-slaves-login and --slaves cannot be used simultaneously (only one)
if opt.discover and opt.slaves:
    parser.error(PARSE_ERR_SLAVE_DISCO_EXC)

# Check slaves list
check_server_lists(parser, opt.master, opt.slaves)

# The value for --timeout needs to be an integer > 0.
try:
    if int(opt.timeout) <= 0:
        parser.error("The --timeout option requires a value greater than 0.")
except ValueError:
    parser.error("The --timeout option requires an integer value.")

# Check errors and warnings of options and combinations.

command = args[0].lower()
if not command in get_valid_rpl_commands():
    parser.error("'%s' is not a valid command." % command)

# --master and --new-master options are required by 'switchover'
if command == 'switchover' and (not opt.new_master or not opt.master):
    req_opts = '--master and --new-master'
    parser.error(PARSE_ERR_OPTS_REQ_BY_CMD.format(cmd=command, opts=req_opts))

# --master and either --slaves or --discover-slaves-login options are required
# by 'elect', 'health' and 'gtid'
if command in ['elect', 'health', 'gtid'] and not opt.master and \
   (not opt.slaves or not opt.discover):
    req_opts = '--master and either --slaves or --discover-slaves-login'
    parser.error(PARSE_ERR_OPTS_REQ_BY_CMD.format(cmd=command, opts=req_opts))

# --slaves options are required by 'start', 'stop' and 'reset'
# --master is optional
if command in ['start', 'stop', 'reset'] and not opt.slaves:
    req_opts = '--slaves'
    parser.error(PARSE_ERR_OPTS_REQ_BY_CMD.format(cmd=command, opts=req_opts))

# Validate the required options for the failover command
if command == 'failover':
    # --discover-slaves-login is invalid (as it will require a master)
    # instead --slaves needs to be used.
    if opt.discover:
        invalid_opt = '--discover-slaves-login'
        parser.error(PARSE_ERR_OPT_INVALID_CMD_TIP.format(opt=invalid_opt,
                                                          cmd=command,
                                                          opt_tip='--slaves'))
    # --master will be ignored
    if opt.master:
        print(WARN_OPT_NOT_REQUIRED.format(opt='--master', cmd=command))
        opt.master = None

# --ping only used by 'health' command
if opt.ping and not command == 'health':
    print(WARN_OPT_NOT_REQUIRED_ONLY_FOR.format(opt='--ping', cmd=command,
                                                only_cmd='health'))
    opt.ping = None

# --exec-after only used by 'failover' or 'switchover' command
if opt.exec_after and command not in ['switchover', 'failover']:
    only_used_cmds = 'failover or switchover'
    print(WARN_OPT_NOT_REQUIRED_ONLY_FOR.format(opt='--exec-after',
                                                cmd=command,
                                                only_cmd=only_used_cmds))
    opt.exec_after = None

# --exec-before only used by 'failover' or 'switchover' command
if opt.exec_before and command not in ['switchover', 'failover']:
    only_used_cmds = 'failover or switchover'
    print(WARN_OPT_NOT_REQUIRED_ONLY_FOR.format(opt='--exec-before',
                                                cmd=command,
                                                only_cmd=only_used_cmds))
    opt.exec_before = None

# --new-master only required for 'switchover' command
if opt.new_master and command != 'switchover':
    print(WARN_OPT_NOT_REQUIRED_ONLY_FOR.format(opt='--new-master',
                                                cmd=command,
                                                only_cmd='switchover'))
    opt.new_master = None

# --candidates only used by 'failover' or 'elect' command
if opt.candidates and command not in ['elect', 'failover']:
    only_used_cmds = 'failover or elect'
    print(WARN_OPT_NOT_REQUIRED_ONLY_FOR.format(opt='--candidates',
                                                cmd=command,
                                                only_cmd=only_used_cmds))
    opt.candidates = None

# --format only used by 'health' or 'gtid' command
if opt.format and command not in ['health', 'gtid']:
    only_used_cmds = 'health or gtid'
    print(WARN_OPT_NOT_REQUIRED_ONLY_FOR.format(opt='--format',
                                                cmd=command,
                                                only_cmd=only_used_cmds))
    opt.format = None

# Parse the --new-master connection string
if opt.new_master:
    try:
        new_master_val = parse_connection(opt.new_master, None, opt)
    except FormatError:
        _, err, _ = sys.exc_info()
        parser.error("New master connection values invalid: %s." % err)
    except UtilError:
        _, err, _ = sys.exc_info()
        parser.error("New master connection values invalid: %s." % err.errmsg)
else:
    new_master_val = None

# Parse the master, slaves, and candidates connection parameters
try:
    master_val, slaves_val, candidates_val = parse_failover_connections(opt)
except UtilRplError:
    _, e, _ = sys.exc_info()
    print("ERROR: %s" % e.errmsg)
    sys.exit(1)

# Check hostname alias
if new_master_val:
    if check_hostname_alias(master_val, new_master_val):
        master = Server({'conn_info' : master_val})
        new_master = Server({'conn_info' : new_master_val})
        parser.error(ERROR_SAME_MASTER.format(n_master_host=new_master.host,
                                              n_master_port=new_master.port,
                                              master_host=master.host,
                                              master_port=master.port))

if master_val:
    for slave_val in slaves_val:
        if check_hostname_alias(master_val, slave_val):
            master = Server({'conn_info' : master_val})
            slave = Server({'conn_info' : slave_val})
            msg = ERROR_MASTER_IN_SLAVES.format(master_host=master.host,
                                                master_port=master.port,
                                                slaves_candidates=SLAVES,
                                                slave_host=slave.host,
                                                slave_port=slave.port)
            parser.error(msg)
    for cand_val in candidates_val:
        if check_hostname_alias(master_val, cand_val):
            master = Server({'conn_info' : master_val})
            candidate = Server({'conn_info' : cand_val})
            msg = ERROR_MASTER_IN_SLAVES.format(master_host=master.host,
                                                master_port=master.port,
                                                slaves_candidates=CANDIDATES,
                                                slave_host=candidate.host,
                                                slave_port=candidate.port)
            parser.error(msg)

# Create dictionary of options
options = {
    'new_master'       : new_master_val,
    'candidates'       : candidates_val,
    'ping'             : 3 if opt.ping is None else opt.ping,
    'format'           : opt.format,
    'verbosity'        : 0 if opt.verbosity is None else opt.verbosity,
    'before'           : opt.exec_before,
    'after'            : opt.exec_after,
    'force'            : opt.force,
    'max_position'     : opt.max_position,
    'max_delay'        : opt.max_delay,
    'discover'         : opt.discover,
    'timeout'          : int(opt.timeout),
    'demote'           : opt.demote,
    'quiet'            : opt.quiet,
    'logging'          : opt.log_file is not None,
    'log_file'         : opt.log_file,
    'no_health'        : opt.no_health,
    'rpl_user'         : opt.rpl_user,
    'script_threshold' : opt.script_threshold,
}

# If command = HEALTH, turn on --force
if command == 'health' or command == 'gtid':
    options['force'] = True

# Purge log file of old data
if opt.log_file is not None and not purge_log(opt.log_file, opt.log_age):
    parser.error("Error purging log file.")

# Warn user about script threshold checking.
if opt.script_threshold:
    print(SCRIPT_THRESHOLD_WARNING)

# Setup log file
try:
    logging.basicConfig(filename=opt.log_file, level=logging.INFO,
                        format='%(asctime)s %(levelname)s %(message)s',
                        datefmt=_DATE_FORMAT)
except IOError:
    _, e, _ = sys.exc_info()
    parser.error("Error opening log file: %s" % str(e.args[1]))

try:
    rpl_cmds = RplCommands(master_val, slaves_val, options)
    rpl_cmds.execute_command(command, options)
except UtilError:
    _, e, _ = sys.exc_info()
    print("ERROR: %s" % e.errmsg)
    sys.exit(1)

sys.exit(0)
