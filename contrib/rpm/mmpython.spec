%define name mmpython
%define version 0.4.10
%define release 1.fc5

Summary: Module for retrieving information about media files
Name: %{name}
Version: %{version}
Release: %{release}
Source0: %{name}-%{version}.tar.gz
License: GPL
Group: Development/Libraries
BuildRoot: %{_tmppath}/%{name}-buildroot
BuildRequires: glibc-devel 
Requires: lsdvd
Prefix: %{_prefix}
Vendor: Thomas Schueppel, Dirk Meyer <freevo-devel@lists.sourceforge.net>
Url: http://mmpython.sf.net

%description
Module for retrieving information about media files

%prep
%setup

%build
env CFLAGS="$RPM_OPT_FLAGS" python setup.py build 

%install
python setup.py install --root=$RPM_BUILD_ROOT --record=INSTALLED_FILES 

%clean
rm -rf $RPM_BUILD_ROOT

%files 
%defattr(-,root,root)
%{_bindir}/*
%{_libdir}/*
%doc README COPYING CREDITS
