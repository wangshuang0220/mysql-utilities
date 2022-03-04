%define version 1.6.5
%define __python /usr/bin/python3
%define NVdir %{name}-%{version} 

Summary:       Collection of utilities used for maintaining and administering MySQL servers
Name:          mysql-utilities
Version:       %{version}
Release:       17%{?dist}
License:       GPLv2
Group:         Development/Libraries
URL:           https://github.com/celane/mysql-utilities
#Source0:       mysql-utilities-#{version}.zip
BuildArch:     noarch
BuildRequires: python3-devel > 3.0
### mysql-connector-python3 should be in /usr/lib64
## and sometimes bad builds put it in the wrong place, this checks
Requires:      mysql-connector-python3 >= 3.0.0
Requires:      %{python3_sitearch}/mysql/connector/__init__.py
BuildRequires: git
#
BuildRoot:     %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
%description

MySQL Utilities provides a collection of command-line utilities that
are used for maintaining and administering MySQL servers, including:
 o Admin Utilities (Clone, Copy, Compare, Diff, Export, Import)
 o Replication Utilities (Setup, Configuration)
 o General Utilities (Disk Usage, Redundant Indexes, Search Meta Data)
 o And many more.

%prep

#### build from git ###
rm -rf %{NVdir}
git clone %{url}.git %{NVdir}
###

# #setup -q

%build
cd %{NVdir}
%{__python} setup.py build

%install
rm -rf %{buildroot}

cd %{NVdir}
%{__python} setup.py install --skip-build \
       --root %{buildroot}  \
     --install-lib %{python3_sitearch}
install -d %{buildroot}%{_exec_prefix}/local/bin/
install  scripts/my_print_defaults  %{buildroot}%{_exec_prefix}/local/bin/

install -d %{buildroot}%{_mandir}/man1
%{__python} setup.py install_man --root %{buildroot}


# Shipped in c/python
rm -f  %{buildroot}%{python3_sitearch}/mysql/__init__.py*
rm -f  %{buildroot}%{python3_sitearch}/mysql/__pycache__/__init__*

echo "find %{buildroot} -->"
find %{buildroot}
echo "end find %{buildroot} <--"

%clean
rm -rf %{buildroot}

%files
%defattr(-, root, root, -)
%doc %{NVdir}/CHANGES.txt  %{NVdir}/LICENSE.txt  %{NVdir}/README.txt
%{_bindir}/mysqlbinlogpurge
%{_bindir}/mysqlbinlogrotate
%{_bindir}/mysqlslavetrx
%{_bindir}/mysqlauditadmin
%{_bindir}/mysqlauditgrep
%{_bindir}/mysqldbcompare
%{_bindir}/mysqldbcopy
%{_bindir}/mysqldbexport
%{_bindir}/mysqldbimport
%{_bindir}/mysqldiff
%{_bindir}/mysqldiskusage
%{_bindir}/mysqlfailover
%{_bindir}/mysqlfrm
%{_bindir}/mysqlindexcheck
%{_bindir}/mysqlmetagrep
%{_bindir}/mysqlprocgrep
%{_bindir}/mysqlreplicate
%{_bindir}/mysqlrpladmin
%{_bindir}/mysqlrplcheck
%{_bindir}/mysqlrplshow
%{_bindir}/mysqlserverclone
%{_bindir}/mysqlserverinfo
%{_bindir}/mysqluc
%{_bindir}/mysqluserclone
%{_bindir}/mysqlrplms
%{_bindir}/mysqlrplsync
%{_bindir}/mysqlbinlogmove
%{_bindir}/mysqlgrants
%{_exec_prefix}/local/bin/my_print_defaults
%{python3_sitearch}/*
%{_mandir}/man1/mysql*.1*

%changelog
* Wed Jan 20 2016 Balasubramanian Kandasamy <balasubramanian.kandasamy@oracle.com> - 1.6.3-1
- Update dist values for sles
- Added mysql_utilities-*.egg-info file for sles12

* Tue Jun 30 2015 Israel Gomez <israel.gomez@oracle.com> - 1.6.2-1
- Removed fabric and extra content.

* Wed Dec 17 2014 Murthy Narkedimilli <murthy.narkedimilli@oracle.com> - 1.6.1
- Added new utilities binaries mysqlbinlogpurge, mysqlbinlogrotate and mysqlslavetrx
- Changed the build prefix for SLES platform.
- Added condition to include the mysql_utilities-*.egg-info file

* Tue Sep 09 2014 Balasubramanian Kandasamy <balasubramanian.kandasamy@oracle.com> - 1.6.0-1
- Added new utilities mysqlgrants and mysqlbinlogmove

* Mon Aug 11 2014 Nelson Goncalves <nelson.goncalves@oracle.com> - 1.6.0
- Updated the Version to 1.6.0

* Mon Aug 11 2014 Chuck Bell <chuck.bell@oracle.com> - 1.5.2
- Updated the Version to 1.5.2

* Tue Jul 01 2014 Chuck Bell <chuck.bell@oracle.com> - 1.5.1
- Updated the Version to 1.5.1

* Mon May 26 2014  Murthy Narkedimilli <murthy.narkedimilli@oracle.com> - 1.5.0
- Updated the Version to 1.5.0

* Wed Feb 26 2014  Balasubramanian Kandasamy <balasubramanian.kandasamy@oracle.com> - 1.4.2-1
- Updated for 1.4.2
- Add extra subpackage

* Fri Jan 03 2014  Balasubramanian Kandasamy <balasubramanian.kandasamy@oracle.com> - 1.3.6-1
- initial package
