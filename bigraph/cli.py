"""Console script for bigraph."""

import fire

def help():
    print("bigraph")
    print("=" * len("bigraph"))
    print("a python implementation of Robin Milner's bigraph formalism")

def main():
    fire.Fire({
        "help": help
    })


if __name__ == "__main__":
    main() # pragma: no cover
