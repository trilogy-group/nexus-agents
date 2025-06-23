from setuptools import setup, find_packages

setup(
    name="nexus-agents",
    version="0.1.0",
    description="Multi-Agent Deep Research System",
    author="Nexus Team",
    author_email="info@nexus-agents.com",
    packages=find_packages(),
    install_requires=[
        line.strip() for line in open("requirements.txt").readlines()
    ],
    entry_points={
        "console_scripts": [
            "nexus-agents=main:main",
        ],
    },
    python_requires=">=3.12",
)