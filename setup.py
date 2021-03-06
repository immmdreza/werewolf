import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="werewolf-immmdreza", # Replace with your own username
    version="0.0.1",
    author="immmdreza",
    author_email="ir310022@gmail.com",
    description="A small package for werewolf",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/immmdreza/werewolf",
    project_urls={
        "Bug Tracker": "https://github.com/immmdreza/werewolf/issues",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    packages=setuptools.find_packages(),
    python_requires=">=3.6",
)
