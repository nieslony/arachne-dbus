Name:       arachne-dbus
Version:    0.1.1
Release:    1%{?dist}
License:    GPLv3
Summary:    DBUS interface for openVPN and arachne
Source0:    %{name}-%{version}.tar.gz
BuildArch:  noarch

BuildRequires:  python3-devel
BuildRequires:  python3-setuptools
Requires:       python%{python3_pkgversion}-dbus
Requires:       python%{python3_pkgversion}-inotify_simple
%{?python_enable_dependency_generator}

%description
DBUS interface for openVPN and arachne

%prep
%autosetup

%build
%py3_build

%install
mkdir -pv %{buildroot}/%{_datadir}/polkit-1/actions
mkdir -pv %{buildroot}/etc/dbus-1/system.d
mkdir -pv %{buildroot}/%{_prefix}/lib/systemd/system
mkdir -pv %{buildroot}/%{python3_sitelib}/arachne_dbusl
%py3_install
install -v polkit/at.nieslony.Arachne.policy %{buildroot}/%{_datadir}/polkit-1/actions
install -v polkit/at.nieslony.Arachne.conf   %{buildroot}/etc/dbus-1/system.d
install -v arachne-dbus.service              %{buildroot}/%{_prefix}/lib/systemd/system

%files
%doc README.md
%license LICENSE
%{python3_sitelib}/arachne_dbus-*.egg-info/
%{python3_sitelib}/arachne_dbus/
/etc/dbus-1/system.d/at.nieslony.Arachne.conf
%{_datadir}/polkit-1/actions/at.nieslony.Arachne.policy
%{_bindir}/arachne-dbus
%{_prefix}/lib/systemd/system/arachne-dbus.service

%changelog
* Thu Feb 01 2024 Claas Nieslony <github@nieslony.at> 0.1.1-1
- fixes

* Thu Feb 01 2024 Claas Nieslony <claas@nieslony.at> 0.1-1
- new package built with tito

* Fri Jan 26 2024 Claas Nieslony <github@nieslony.at> 0.0.1
- Initial version
