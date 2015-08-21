%global commit 901247227887a1e5d34a8c8c2da33e98da694000
%global shortcommit %(c=%{commit}; echo ${c:0:7})

Name:          gnome-keysign
Version:       0.3
Release:       0.git.%{shortcommit}%{?dist}
Summary:       GNOME OpenGPG key signing helper

License:       GPLv3+
URL:           https://wiki.gnome.org/GnomeKeysign
Source0:       https://github.com/muelli/geysigning/archive/%{commit}/%{name}-%{version}-%{shortcommit}.tar.gz

BuildRequires: python-devel
BuildRequires: /usr/bin/desktop-file-validate
Requires:      python-requests dbus-python avahi-ui-tools
Requires:      python-qrencode monkeysign gstreamer1(element-zbar)
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
