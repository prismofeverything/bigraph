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
* Documentation: <https://prismofeverything.github.io/bigraph>


## Usage

This library is a python interface to [bigraph-tools](https://bitbucket.org/uog-bigraph/bigraph-tools/src/master/) from the [Glasgow Bigraph Team](https://uog-bigraph.bitbucket.io/team.html), and mediates the creation, execution, and parsing of results from that suite of tools. 

## Introduction

[Introduction to Bigraphs](https://prismofeverything.github.io/bigraph): a brief introduction to bigraphs in general and their programmatic API as implemented by this library.

## Install on Ubuntu

First you have to install bigraph-tools, which requires opam and dune.

To install opam: 

(ubuntu)
```bash
 sudo add-apt-repository ppa:avsm/ppa
 sudo apt update
 sudo apt install opam --upgrade
 sudo apt install minisat cppo
```

(arch)
```bash
pacman -S opam
```

Then to install dune

```bash
opam init
opam install dune
```

The various requirements for bigraph-tools are:

```bash
opam install cmdliner.1.0.4 jsonm menhir dune-configurator mtime
```

Clone the `bigrapher-tools` repo:

```bash
 git clone https://bitbucket.org/uog-bigraph/bigraph-tools.git
 cd bigraph-tools
```

In the `dune-project` file update the following line:
```
(using menhir 1.0)
```

to 

```
(using menhir 2.0)
```

Then build the bigraph-tools:
```bash
dune build --profile=release
```

