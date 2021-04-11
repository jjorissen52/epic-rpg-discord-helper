from setuptools import setup
from setuptools_rust import Binding, RustExtension

setup(
    name="materials",
    version="0.0.3",
    packages=["crafting"],
    rust_extensions=[RustExtension("materials", "Cargo.toml", binding=Binding.PyO3)],
    include_package_data=True,
    zip_safe=False,
    test_suite="tests",
)
