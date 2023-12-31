from setuptools import setup

# Available at setup time due to pyproject.toml
from pybind11.setup_helpers import Pybind11Extension, build_ext

__version__ = "0.0.1"

ext_modules = [
    Pybind11Extension(
        'TronGamer',
        [
            'src/pybind_tron.cpp',
            'src/TronListener.cpp',
            'src/TronAI.cpp',
            'src/Player.cpp',
            'src/TronSimulator.cpp',
            'src/vec.cpp'
        ],
        include_dirs=[
            "include/"
        ],
        language='c++',
        #extra_compile_args=['-Wno-sign-compare', '-Wno-reorder', '-O3', '-std=c++17']
        ),
]

setup(
    name="TronGamer",
    version=__version__,
    author="Andreas Faust",
    author_email="andreas.s.faust@gmail.com",
    url="",
    description="TronGamer",
    long_description="",
    ext_modules=ext_modules,
    extras_require={"test": "pytest"},
    # Currently, build_ext only provides an optional "highest supported C++
    # level" feature, but in the future it may provide more features.
    cmdclass={"build_ext": build_ext},
    zip_safe=False,
)
