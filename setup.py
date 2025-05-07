from setuptools import setup, find_packages

setup(
    name="zkscript_package",
    version="0.1.0",
    description="A package to generate complex Bitcoin Scripts",
    url="https://github.com/yourusername/zkscript_package",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.12",
)
