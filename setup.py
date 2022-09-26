import setuptools

def main():
    with open("README.md", "r", encoding="utf-8") as fh:
        long_description = fh.read()

    setuptools.setup(
        name="Strawberry tornado",
        description="Integration of strawberry-graphql in to the tornado web framework",
        long_description=long_description,
        long_description_content_type="text/markdown",
        author="Artem Constantinov",
        author_email="y_4ox@yahoo.com",
        url="https://github.com/xenanetworks/open-automation-python-api",
        packages=setuptools.find_packages(),
        license='MIT',
        install_requires = ["strawberry-graphql", "strawberry-graphql"],
        classifiers=[
            "Development Status :: 5 - Production/Stable",
            "Intended Audience :: Developers",
            "Topic :: Software Development :: Libraries :: Python Modules",
            "License :: OSI Approved :: MIT License",
            "Programming Language :: Python :: 3.8",
            "Programming Language :: Python :: 3.9",
            "Programming Language :: Python :: 3.10",
        ],
        python_requires=">=3.8",
    )

if __name__ == '__main__':
    main()