# bigraph


<p align="center">
<a href="https://pypi.python.org/pypi/bigraph">
    <img src="https://img.shields.io/pypi/v/bigraph.svg"
        alt = "Release Status">
</a>

<a href="https://github.com/prismofeverything/bigraph/actions">
    <img src="https://github.com/prismofeverything/bigraph/actions/workflows/main.yml/badge.svg?branch=release" alt="CI Status">
</a>

<a href="https://bigraph.readthedocs.io/en/latest/?badge=latest">
    <img src="https://readthedocs.org/projects/bigraph/badge/?version=latest" alt="Documentation Status">
</a>

</p>


a python implementation of Robin Milner's bigraph formalism


* Free software: BSD-3-Clause
* Documentation: <https://bigraph.readthedocs.io>


## Install on Ubuntu

First you have to install bigraph-tools, which requires opam and dune.

To install opam: 

```bash
> sudo add-apt-repository ppa:avsm/ppa
> sudo apt update
> sudo apt install opam --upgrade
> sudo apt install minisat cppo
```

Then to install dune

> opam install dune.2.5.1

The various requirements for bigraph-tools are:

> opam install cmdliner jsonm menhir dune-configurator mtime

Clone the repo and check out the v1.3.4 branch:

```bash
> git clone https://bitbucket.org/uog-bigraph/bigraph-tools.git
> git co v1.3.4
```


## Features

* TODO

