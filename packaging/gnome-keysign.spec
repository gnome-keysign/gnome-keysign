%global commit cfcb137edebd6b1b88a7d5a39c6435561ee27eed
%global shortcommit %(c=%{commit}; echo ${c:0:7})

Name:          gnome-keysign
Version:       0.9.7.2
Release:       0.9.7.2.git.%{shortcommit}%{?dist}
Summary:       GNOME OpenGPG key signing helper

License:       GPLv3+
URL:           https://wiki.gnome.org/GnomeKeysign
Source0:       https://github.com/GNOME-Keysign/gnome-keysign/archive/%{commit}/%{name}-%{version}-%{shortcommit}.tar.gz

BuildRequires: python-devel
BuildRequires: python-babel
BuildRequires: python-babel-BabelGladeExtractor
BuildRequires: /usr/bin/desktop-file-validate
Requires:      python-gobject  gtk3
Requires:      dbus-python
Requires:      gstreamer1-plugins-bad-free-extras gstreamer1-plugins-good
Requires:      python-qrcode
Requires:      python-requests avahi-ui-tools
Requires:      python-twisted
Requires:      pybluez
Requires:      gpgme
BuildArch:     noarch

%description
OpenGPG key signing helper

%prep
%setup -qn gnome-keysign-%{commit}

%build
%{__python} setup.py build

%install
%{__python} setup.py install -O1 --skip-build --root %{buildroot}

%check
desktop-file-validate %{buildroot}%{_datadir}/applications/org.gnome.Keysign.desktop

%files
%doc README.rst
%license COPYING
%{_bindir}/%{name}
%{_bindir}/gks-qrcode
%{_datadir}/applications/org.gnome.Keysign.desktop
%{_datadir}/metainfo/org.gnome.Keysign.appdata.xml
%{_datadir}/icons/hicolor/scalable/apps/org.gnome.Keysign.svg
%{python_sitelib}/keysign/
%{python_sitelib}/gnome_keysign-*.egg-info/

%changelog
* Sat May 26 2018 Tobias Mueller <tobiasmue@gnome.org> - 0.9.7.2
- Attempt to update the version
* Tue Feb 24 2015 Igor Gnatenko <i.gnatenko.brain@gmail.com> - 0.1-0.git.55f95bd
- Initial package
