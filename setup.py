from setuptools import setup

setup(
    name="dedupgenie",
    version="1.0.0",
    description="Desktop duplicate file finder with forensic-grade detection",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="Marc Gagnon",
    author_email="marc@marcgagnon.ca",
    url="https://github.com/lemarcgagnon/DuplicateFinder",
    license="MIT",
    py_modules=["app"],
    python_requires=">=3.8",
    install_requires=["PyQt5>=5.15"],
    entry_points={
        "gui_scripts": ["dedupgenie=app:main"],
    },
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: X11 Applications :: Qt",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
    ],
)
