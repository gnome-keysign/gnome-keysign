%global commit c97ba3c96594592a438fe4fc4a034215a79ebe48
%global shortcommit %(c=%{commit}; echo ${c:0:7})

Name:          gnome-keysign
Version:       0.7
Release:       0.7.git.%{shortcommit}%{?dist}
Summary:       GNOME OpenGPG key signing helper

License:       GPLv3+
URL:           https://wiki.gnome.org/GnomeKeysign
Source0:       https://github.com/muelli/geysigning/archive/%{commit}/%{name}-%{version}-%{shortcommit}.tar.gz

BuildRequires: python-devel
BuildRequires: /usr/bin/desktop-file-validate
Requires:      python-requests dbus-python avahi-ui-tools
Requires:      python-qrcode  python-gobject    python-avahi
Requires:      gstreamer1-plugins-bad-free-extras
BuildArch:     noarch

%description
OpenGPG key signing helper

%prep
%setup -qn geysigning-%{commit}

%build
%{__python} setup.py build

%install
%{__python} setup.py install -O1 --skip-build --root %{buildroot}

%check
desktop-file-validate %{buildroot}%{_datadir}/applications/%{name}.desktop

%files
%doc README.rst
%license COPYING
%{_bindir}/%{name}
%{_bindir}/gks-qrcode
%{_datadir}/applications/%{name}.desktop
%{_datadir}/icons/hicolor/scalable/apps/%{name}.svg
%{python_sitelib}/keysign/
%{python_sitelib}/gnome_keysign-*.egg-info/

%changelog
* Tue Feb 24 2015 Igor Gnatenko <i.gnatenko.brain@gmail.com> - 0.1-0.git.55f95bd
- Initial package
