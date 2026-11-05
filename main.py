# CardVault
# Copyright (c) 2026 Gabriel Dobre. All rights reserved.
import sys

# 1) FIRST thing at startup: block all network access (internet AND local network)
#    before any other library is loaded.
from cardvault import netguard

netguard.install()

# 2) Only then load the rest of the application.
from cardvault.ui import run  # noqa: E402

if __name__ == "__main__":
    sys.exit(run())
