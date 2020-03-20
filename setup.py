import fastentrypoints
import setuptools
import versioneer

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="jktool",
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    author="leoetlino",
    author_email="leo@leolam.fr",
    description="Library and tools for MM3D (Joker) formats",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/leoetlino/jktool",
    packages=setuptools.find_packages(),
    classifiers=[
        "License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3 :: Only",
        "Topic :: Software Development :: Libraries",
    ],
    python_requires='>=3.6',
    entry_points = {
        'console_scripts': [
            'gar = jktool.gartool:main',
            'glyttool = jktool.lyttool:main',
        ],
    },
)
