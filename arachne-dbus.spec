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

%files
%doc README.md
%license LICENSE
%{python3_sitelib}/%{name}-*.egg-info/
%{python3_sitelib}/%{name}/

%changelog
