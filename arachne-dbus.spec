Name:       arachne-dbus
Version:    0.1.3.git240729231401_a0a1ae2
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
mkdir -pv %{buildroot}/%{_unitdir}
mkdir -pv %{buildroot}/%{python3_sitelib}/arachne_dbus
%py3_install
install -v polkit/at.nieslony.Arachne.policy %{buildroot}/%{_datadir}/polkit-1/actions
install -v polkit/at.nieslony.Arachne.conf   %{buildroot}/etc/dbus-1/system.d
install -v arachne-dbus.service              %{buildroot}/%{_unitdir}/%{name}.service

%preun
%systemd_preun %{name}.service

%post
%systemd_post %{name}.service

%postun
%systemd_postun_with_restart %{name}.service

%files
%doc README.md
%license LICENSE
%{python3_sitelib}/arachne_dbus-*.egg-info/
%{python3_sitelib}/arachne_dbus/
/etc/dbus-1/system.d/at.nieslony.Arachne.conf
%{_datadir}/polkit-1/actions/at.nieslony.Arachne.policy
%{_bindir}/arachne-dbus
%{_unitdir}/%{name}.service


%changelog
* Mon Jul 29 2024 Claas Nieslony <github@nieslony.at> 0.1.3.git240729231401_a0a1ae2-1
- Fix: default directory (github@nieslony.at)

* Mon Jul 29 2024 Claas Nieslony <github@nieslony.at> 0.1.3.git240729142557_8cd4dc8-1
- Improve exceptions handling (github@nieslony.at)

* Thu Feb 22 2024 Claas Nieslony <github@nieslony.at>
- Add packages (github@nieslony.at)
- Ignore backups (github@nieslony.at)

* Wed Feb 21 2024 Claas Nieslony <github@nieslony.at>
- Fix: member variable (github@nieslony.at)

* Wed Feb 21 2024 Claas Nieslony <github@nieslony.at>
- Fix: member variable (github@nieslony.at)

* Wed Feb 21 2024 Claas Nieslony <github@nieslony.at>
- Fix: member variable (github@nieslony.at)

* Thu Feb 01 2024 Claas Nieslony <github@nieslony.at> 0.1.3-1
- Fix: typo (github@nieslony.at)

* Thu Feb 01 2024 Claas Nieslony <github@nieslony.at> 0.1.2-1
- Fix: create site-libs (github@nieslony.at)
- Fix: quotes (github@nieslony.at)

* Thu Feb 01 2024 Claas Nieslony <github@nieslony.at> 0.1.1-1
- fixes

* Thu Feb 01 2024 Claas Nieslony <claas@nieslony.at> 0.1-1
- new package built with tito

* Fri Jan 26 2024 Claas Nieslony <github@nieslony.at> 0.0.1
- Initial version
