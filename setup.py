# -*-coding:utf-8-*-
from distutils.core import setup

from setuptools import find_packages

with open("README.md", "rt", encoding="utf8") as f:
    long_description = f.read()

setup(name="TerminalInExplorer",
      version="0.0.1",
      description="",
      long_description=long_description,
      long_description_content_type="text/markdown",
      author="NoCLin",
      author_email="engineelin@gmail.com",
      url="https://github.com/NoCLin/terminal-in-explorer",
      license="MIT Licence",
      install_requires=[
          'pywin32==227',
          'pywinauto==0.6.8',
      ],
      packages=find_packages(),
      zip_safe=False,
      classifiers=[
          'Programming Language :: Python :: 3.5',
          'Programming Language :: Python :: 3.6',
          'Programming Language :: Python :: 3.7',
          'License :: OSI Approved :: MIT License',
          # 'Operating System :: OS Independent'
      ],
      package_data={
      },
      entry_points={
          'console_scripts': [
              'tie = tie.main:main',
          ]
      },
      )
