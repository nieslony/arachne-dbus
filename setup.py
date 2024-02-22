from setuptools import setup
import src.arachne_dbus as arachne_dbus

setup(
    name = "arachne_dbus",
    version = arachne_dbus.__version__,
    author = "Claas Nieslony",
    license = "GPVv3",
    packages = ["arachne_dbus"],
    package_dir = {
        "": "src"
        },
    entry_points = {
        'console_scripts': [
            'arachne-dbus = arachne_dbus.arachne_dbus:main',
        ],
    }
)
