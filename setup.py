from setuptools import setup, find_packages

setup(
    name='bigraph',
    version='0.0.1',
    description='a python interface to Robin Milner\'s bigraph formalism',
    author='Ryan Spangler',
    author_email='ryan.spangler@gmail.com',
    url='https://github.com/prismofeverything/bigraph',
    packages=find_packages(include=['bigraph', 'bigraph.*']),
    install_requires=[
        'fire',
        'parsimonious',
        'networkx',
    ],
    extras_require={'plotting': ['matplotlib>=2.2.0', 'jupyter']},
    setup_requires=['pytest-runner', 'flake8'],
    tests_require=['pytest'],
    entry_points={
        'console_scripts': ['bigraph=bigraph.bigraph:main']
    },
    # package_data={'bigraph': ['data/schema.json']}
)
