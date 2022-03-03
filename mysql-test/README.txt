need to have a mysql server running,
.my.cnf in root account (need root for doing stop/start servers?)
  with just the password, no ssl stuff?


note that the mysql-utilities look for info in $HOME/.mylogin.cnf
by mysql etc look in $HOME/.my.cnf
but since myhsql-utilities seems to demand --server=... options
in all circumstance, not clear how much .mylogin.cnf is actually
used.

MySQL >= 8.0 has moved some stuff between the mysql database and
the information_schema database, with some rename of various
columns.

In particular, the mysql/proc table -> information_schema/routines

in server.py:   server.has_mysqlproc() returns boolean to indicate
if the 'old style' mysql.proc is used: which is the case for
MySQL < 8.0
MariaDB
Percona

also server.get_server_type()
returns one of
        MySQL   MariaDB   Percona

which can be used to deal with differences. 

mysqlauditadmin: needs the 'audit' plugin on MySQL, which maybe needs
the 'enterprise' version of MySQL? 
