from setuptools import setup, find_packages

setup(
    name="netfi",
    version="0.1.0",
    description="A Python package for network emulation and packet loss modeling",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="Hamid Reza Roodabeh",
    author_email="hr.roodabeh@gmail.com",
    url="https://github.com/hamidrezaro/NetFI",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "numpy>=1.18.0",
        "matplotlib>=3.2.0",
        "scipy>=1.5.0",
        # Add other dependencies from your requirements.py if needed
    ],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: Telecommunications Industry",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
    python_requires=">=3.7",
    extras_require={
        "test": [
            "pytest>=6.0",
            "pytest-cov>=2.0",
        ]
    },
)
