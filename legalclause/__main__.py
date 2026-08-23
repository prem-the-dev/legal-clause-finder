"""`python -m legalclause` entry point — delegates to cli.main()."""
from legalclause.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
