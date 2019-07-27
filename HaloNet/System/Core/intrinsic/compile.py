__author__ = 'metrick'

import sys
sys.argv += ['install', 'build']
from distutils.core import setup
from distutils.extension import Extension
from Cython.Distutils import build_ext

setup(
    cmdclass = {'build_ext': build_ext},
    ext_modules = [
        Extension("Serialization",
                  sources=["Serialization.pyx",
                       ],
                  language="c++",  # remove this if C and /not C++
                  extra_compile_args=["-I./Sources/"],
                  extra_link_args=["-L./C:/Program Files (x86)/Microsoft Visual Studio 14.0/VC/redist/x64/Microsoft.VC140.CRT/"]
             ),

        Extension("_DateTime",
                  sources=["_DateTime.pyx",
                           ],
                  language="c++",  # remove this if C and /not C++
                  extra_compile_args=["-I./Sources/"],
                  extra_link_args=[
                      "-L./C:/Program Files (x86)/Microsoft Visual Studio 14.0/VC/redist/x64/Microsoft.VC140.CRT/"]
                  ),

        Extension("_BasicTypes",
                  sources=["_BasicTypes.pyx",
                           ],
                  language="c++",  # remove this if C and /not C++
                  extra_compile_args=["-I./Sources/"],
                  extra_link_args=[
                      "-L./C:/Program Files (x86)/Microsoft Visual Studio 14.0/VC/redist/x64/Microsoft.VC140.CRT/"]
                  ),
        Extension("TestPyx",
                  sources=["TestPyx.pyx",
                           ],
                  language="c++",  # remove this if C and /not C++
                  extra_compile_args=["-I./Sources/"],
                  extra_link_args=[
                      "-L./C:/Program Files (x86)/Microsoft Visual Studio 14.0/VC/redist/x64/Microsoft.VC140.CRT/"]
                  ),
        ]

)
