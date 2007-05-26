##########################################################################
# Set default freevo parameters
%define geometry 800x600
%define display  x11

##########################################################################


%if %{?_without_us_defaults:0}%{!?_without_us_defaults:1}
%define tv_norm  ntsc
%define chanlist us-cable
%else
%define tv_norm  pal
%define chanlist europe-west
%endif

##########################################################################
%define pkgname freevo
%define version 1.7.0
%define release 2.fc5
%define _cachedir /var/cache
%define _logdir /var/log
%define _contribdir /usr/share/freevo/contrib
%define _freevosharedir /usr/share/freevo
%define _localedir /usr/share/locale

Summary:        Freevo
Name: %{pkgname}17
Version: %{version}
Release: %{release}
Source0: %{pkgname}-%{version}.tar.gz
Source1: redhat-boot_config
License: gpl
Group: Applications/Multimedia
BuildArch: noarch
BuildRoot: %{_tmppath}/%{pkgname}-buildroot
# SVN version
#BuildRequires: docbook-utils, wget
BuildRequires: pygame, python-twisted 
BuildRequires: python-kaa-base, python-kaa-metadata
Requires: SDL >= 1.2.6, SDL_image >= 1.2.3, SDL_ttf >= 2.0.6, SDL_mixer >= 1.2.5
Requires: smpeg >= 0.4.4, freetype >= 2.1.4, util-linux
Requires: python >= 2.4, pygame >= 1.6, PyXML
Requires: python-kaa-base, python-kaa-metadata
Requires: python-kaa-imlib2
Requires: mx >= 2.0.5, python-numeric >= 23.1,
Requires: libjpeg >= 6b, libexif >= 0.5.10
Requires: python-twisted >= 1.3.0
Requires: lsdvd >= 0.16
Requires: python-elementtree
Obsoletes: freevo < 1.7.0
Prefix: %{_prefix}
URL:            http://freevo.sourceforge.net/

%description
Freevo is a Linux application that turns a PC with a TV capture card
and/or TV-out into a standalone multimedia jukebox/VCR. It builds on
other applications such as xine, mplayer, tvtime and mencoder to play
and record video and audio.

Available rpmbuild rebuild options :
--without: us_defaults use_sysapps compile_obj

%package boot
Summary: Files to enable a standalone Freevo system (started from initscript)
Group: Applications/Multimedia
Requires:       %{name}
Obsoletes: %{pkgname}-boot < 1.7.0

%description boot
Freevo is a Linux application that turns a PC with a TV capture card
and/or TV-out into a standalone multimedia jukebox/VCR. It builds on
other applications such as mplayer and mencoder to play and record
video and audio.

Note: This installs the initscripts necessary for a standalone Freevo system.

%prep
rm -rf $RPM_BUILD_ROOT
%setup -n freevo-%{version}

%build
find . -name CVS | xargs rm -rf
find . -name .svn | xargs rm -rf
find . -name ".cvsignore" |xargs rm -f
find . -name "*.pyc" |xargs rm -f
find . -name "*.pyo" |xargs rm -f
find . -name "*.py" |xargs chmod 644

# Used for SVN version only
#./autogen.sh


env CFLAGS="$RPM_OPT_FLAGS" python setup.py build

mkdir -p %{buildroot}%{_sysconfdir}/freevo
# The following is needed to let RPM know that the files should be backed up
touch %{buildroot}%{_sysconfdir}/freevo/freevo.conf

# boot scripts
mkdir -p %{buildroot}%{_sysconfdir}/rc.d/init.d
mkdir -p %{buildroot}%{_bindir}
install -m 755 boot/freevo %{buildroot}%{_sysconfdir}/rc.d/init.d
#install -m 755 boot/freevo_dep %{buildroot}%{_sysconfdir}/rc.d/init.d
install -m 755 boot/recordserver %{buildroot}%{_sysconfdir}/rc.d/init.d/freevo_recordserver
install -m 755 boot/webserver %{buildroot}%{_sysconfdir}/rc.d/init.d/freevo_webserver
install -m 755 boot/recordserver_init %{buildroot}%{_bindir}/freevo_recordserver_init
install -m 755 boot/webserver_init %{buildroot}%{_bindir}/freevo_webserver_init
install -m 644 -D %{SOURCE1} %{buildroot}%{_sysconfdir}/freevo/boot_config

# cache and log directories
mkdir -p %{buildroot}%{_logdir}/freevo
mkdir -p %{buildroot}%{_cachedir}/freevo
mkdir -p %{buildroot}%{_cachedir}/freevo/{thumbnails,audio}
mkdir -p %{buildroot}%{_cachedir}/xmltv/logos
chmod 777 %{buildroot}%{_cachedir}/{freevo,freevo/thumbnails,freevo/audio,xmltv,xmltv/logos}
chmod 777 %{buildroot}%{_logdir}/freevo

%install
python setup.py install %{?_without_compile_obj:--no-compile} \
		--root=$RPM_BUILD_ROOT --record=INSTALLED_FILES

mkdir -p %{buildroot}%{_contribdir}
cp -av contrib/lirc %{buildroot}%{_contribdir}
cp -av contrib/plugins %{buildroot}%{_contribdir}
cp -av contrib/video %{buildroot}%{_contribdir}

# Need to copy the example config file to the doc directory
cp local_conf.py.example %{buildroot}%{_docdir}/%{pkgname}-%{version}/

%post
# Make backup of old freevo.conf here
if [ -s %{_sysconfdir}/freevo/freevo.conf ]; then
   cp %{_sysconfdir}/freevo/freevo.conf %{_sysconfdir}/freevo/freevo.conf.rpmsave
fi

# Copy old local_conf.py to replace dummy file
%{_bindir}/freevo setup --geometry=%{geometry} --display=%{display} \
        --tv=%{tv_norm} --chanlist=%{chanlist} \
	%{!?_without_use_sysapps:--sysfirst}

%preun
# Not safe to run this when upgrading!
#if [ -s %{_sysconfdir}/freevo/freevo.conf ]; then
#   cp %{_sysconfdir}/freevo/freevo.conf %{_sysconfdir}/freevo/freevo.conf.rpmsave
#fi
if [ -s %{_sysconfdir}/freevo/local_conf.py ]; then
   cp %{_sysconfdir}/freevo/local_conf.py %{_sysconfdir}/freevo/local_conf.py.rpmsave
fi

%clean
rm -rf $RPM_BUILD_ROOT

%files 
%defattr(-,root,root)
#%doc COPYING ChangeLog FAQ INSTALL README local_conf.py.example
#%doc local_conf.py.example
#%doc Docs/CREDITS Docs/NOTES Docs/fxd_files.txt Docs/*.dtd Docs/TODO Docs/plugins Docs/distribution
#%doc Docs/installation Docs/plugin_writing
%{_docdir}/%{pkgname}-%{version}
%attr(755,root,root) %{_bindir}/freevo
%{_libdir}/*
%{_freevosharedir}/*
%{_localedir}/*
%attr(755,root,root) %dir %{_sysconfdir}/freevo
%attr(777,root,root) %dir %{_logdir}/freevo
%attr(777,root,root) %dir %{_cachedir}/freevo
%attr(777,root,root) %dir %{_cachedir}/freevo/audio
%attr(777,root,root) %dir %{_cachedir}/freevo/thumbnails
%attr(777,root,root) %dir %{_cachedir}/xmltv
%attr(777,root,root) %dir %{_cachedir}/xmltv/logos
%attr(644,root,root) %config %{_sysconfdir}/freevo/freevo.conf

%files boot
%defattr(644,root,root,755)
%attr(755,root,root) %{_sysconfdir}/rc.d/init.d
%attr(755,root,root) %{_bindir}/freevo_*
%attr(755,root,root) %dir %{_sysconfdir}/freevo
%attr(644,root,root) %config %{_sysconfdir}/freevo/boot_config

%post boot
# Add the service if not present, but don't automatically invoke it
# user has to enable it via ntsysv
if [ -x /sbin/chkconfig ]; then
  if [ `chkconfig --list freevo 2> /dev/null |fgrep -c freevo` -eq 0 ]; then
     chkconfig --add freevo
     chkconfig --levels 234 freevo off
  fi
  if [ `chkconfig --list freevo_recordserver 2> /dev/null |fgrep -c freevo_recordserver` -eq 0 ]; then
     chkconfig --add freevo_recordserver
     chkconfig --levels 234 freevo_recordserver off
  fi
  if [ `chkconfig --list freevo_webserver 2> /dev/null |fgrep -c freevo_webserver` -eq 0 ]; then
     chkconfig --add freevo_webserver
     chkconfig --levels 234 freevo_webserver off
  fi
fi
depmod -a

%preun boot
if [ "$1" == 0 ] ; then
  if [ -x /sbin/chkconfig ]; then
     chkconfig --del freevo
     chkconfig --del freevo_recordserver
     chkconfig --del freevo_webserver
  fi
fi

%changelog
* Mon Feb 26 2007 TC Wan <tcwan@cs.usm.my>
- Built 1.7.0 for FC5 

* Wed Nov 29 2006 TC Wan <tcwan@cs.usm.my>
- Built 1.6.1 for FC5 

* Mon Oct 30 2006 TC Wan <tcwan@cs.usm.my>
- Built 1.6.0 for FC5 

* Tue May  2 2006 TC Wan <tcwan@cs.usm.my>
- Rebuilt 1.5.4 for FC5 
