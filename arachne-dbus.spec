Name: arachne-dbus
Version: 0.0.1
Release: 0%{?dist}
License: GPLv3
Summary: DBUS interface for openVPN and arachne
Source0: %{name}-%{version}.tar.gz

BuildArch: noarch

BuildRequires: python3-devel
BuildRequires: python3-setuptools

%description
DBUS interface for openVPN and arachne

%prep
%autosetup

%build
%py3_build

%install
%py3_install
mkdir -pv /usr/share/polkit-1/actions
mkdir -pv /etc/dbus-1/system.d
install -v at.nieslony.Arachne.policy /usr/share/polkit-1/actions
install -v at.nieslony.Arachne /etc/dbus-1/system.d

%files
%doc README.md
%license LICENSE
%{python3_sitelib}/arachne_dbus-*.egg-info/
%{python3_sitelib}/arachne_dbus/

%changelog
* Fri Jan 26 2024 Claas Nieslony <github@nieslony.at> 0.0.1
- Initial version
