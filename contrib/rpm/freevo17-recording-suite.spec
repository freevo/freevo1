%define freevoname freevo
%define freevover 1.7
%define freevorel 1.freevo
##############################################################################
Summary: Meta-package for Freevo recording functionality
Name: freevo17-recording-suite
Version: %{freevover}
Release: %{freevorel}
License: GPL
Group: Applications/Multimedia
URL:   http://freevo.sourceforge.net/
Requires: freevo17-core-suite
Requires: python-twisted >= 1.3.0 
Requires: vorbis-tools, libvorbis, lame, cdparanoia
#Requires: mp1e >= 1.9.3
Requires: ffmpeg >= 0.4.9
Requires: %{freevoname}17
Obsoletes: freevo-recording-suite < 1.7.0
BuildArch: noarch


%description
Freevo is a Linux application that turns a PC with a TV capture card
and/or TV-out into a standalone multimedia jukebox/VCR. It builds on
other applications such as xine, mplayer, tvtime and mencoder to play
and record video and audio.

This is a meta-package used by apt to setup all required recording packages
for using freevo to record TV programs.

%prep

%build

%install

%files 
%defattr(-,root,root)

%changelog
* Mon Feb 26 2007 TC Wan <tcwan@cs.usm.my>
- Rebuilt for Freevo 1.7.x FC5 dependencies

* Wed May  3 2006 TC Wan <tcwan@cs.usm.my>
- Rebuilt for FC5 dependencies

* Wed Mar 24 2004 TC Wan <tcwan@cs.usm.my>
- Rebuilt for freevo 1.5

* Wed Oct 15 2003 TC Wan <tcwan@cs.usm.my>
- Moved twisted dependency to core, removed pyao, pyogg, pyvorbis dependencies
  since it's no longer needed

* Thu Sep 18 2003 TC Wan <tcwan@cs.usm.my>
- Added pyao, pyogg, pyvorbis dependencies

* Wed Sep 17 2003 TC Wan <tcwan@cs.usm.my>
- Initial SPEC file for RH 9
