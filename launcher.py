"""Frozen-app entry point.

PyInstaller runs its entry script as the top-level ``__main__`` module with no
package, which breaks the relative imports inside ``snoper/__main__.py``. Using
this launcher as the entry instead imports ``snoper`` as a proper package, so all
relative imports resolve. The build spec points here (not at the package).
"""

import sys

from snoper.__main__ import main

if __name__ == "__main__":
    sys.exit(main())
