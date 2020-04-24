import re
import sys

from PyQt5.uic.pyuic import main

if __name__ == '__main__':
    sys.argv[0] = re.sub(r'(-script\.pyw?|\.exe)?$', '', sys.argv[0])
    sys.argv = [sys.argv[0]] + ["mainwindow.ui", "-o", "mainwindow_ui.py"]
    sys.exit(main())
