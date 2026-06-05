from setuptools import setup

# Available at setup time due to pyproject.toml
from pybind11.setup_helpers import Pybind11Extension, build_ext

__version__ = "0.0.1"

ext_modules = [
    Pybind11Extension(
        'TronBoard',
        [
            'src/pybind_board.cpp',
            'src/Board.cpp',
            'src/mcmc.cpp'
        ],
        include_dirs=[
            "include/"
        ],
        language='c++',
        # Debug build: -g keeps symbol/line info, -O0 stops the optimizer from
        # reordering/inlining away the breadcrumb path, -rdynamic exports
        # symbols so backtrace_symbols() can name the frames in debug.h.
        extra_compile_args=['-g', '-O3', '-std=c++17'],
        #extra_link_args=['-rdynamic'],
        #extra_compile_args=['-Wno-sign-compare', '-Wno-reorder', '-O3', '-std=c++17']
        ),
]

setup(
    name="TronBoard",
    version=__version__,
    author="Andreas Faust",
    author_email="andreas.s.faust@gmail.com",
    url="",
    description="TronBoard",
    long_description="",
    ext_modules=ext_modules,
    extras_require={"test": "pytest"},
    # Currently, build_ext only provides an optional "highest supported C++
    # level" feature, but in the future it may provide more features.
    cmdclass={"build_ext": build_ext},
    zip_safe=False,
)
