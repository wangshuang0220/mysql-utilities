#!/bin/bash
# get the world database used for (some) test
wget https://downloads.mysql.com/docs/world-db.tar.gz
tar xzvf world-db.tar.gz
mv world-db/world.sql std_data/world_innodb.sql
rm -rf world-db world-db.tar.gz
mysql <echo 'drop database `world` if exists;'
mysql <std_data/world_innodb.sql
exit 0
