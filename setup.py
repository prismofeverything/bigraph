from setuptools import setup, find_packages


VERSION = '0.0.3'


with open('README.md', 'r') as readme:
    description = readme.read()


setup(
    name='bigraphs',
    version=VERSION,
    author='Ryan Spangler',
    author_email='ryan.spangler@gmail.com',
    description='a python interface to Robin Milner\'s bigraph formalism',
    url='https://github.com/prismofeverything/bigraph',
    packages=find_packages(include=['bigraph', 'bigraph.*']),
    python_requires=">=3.6",
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
