from setuptools import setup
import src.arachne_dbus as arachne_dbus

setup(
    name = "Arachne DBUS",
    version = arachne_dbus.__version__,
    author = "Claas Nieslony",
    license = "GPVv3",
    package_dir = {
        "": "src"
        },
)