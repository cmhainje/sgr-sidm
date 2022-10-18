from setuptools import setup

REQUIREMENTS = ["gtools", "numpy", "torch", "ddks", "tqdm", "astropy"]

setup(
    name="sgrana",
    version="0.1",
    description=".",
    url="https://github.com/cmhainje/sgr-sidm",
    author="Connor Hainje",
    author_email="cmhainje@gmail.com",
    packages=["sgrana"],
    install_requires=REQUIREMENTS,
)
