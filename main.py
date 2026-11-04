# CardVault
# Copyright (c) 2026 Gabriel Dobre. All rights reserved.
import sys

# 1) PRIMUL lucru la pornire: blocăm orice acces la rețea (internet ȘI rețea locală),
#    înainte să se încarce orice altă bibliotecă.
from cardvault import netguard

netguard.install()

# 2) Abia apoi restul aplicației.
from cardvault.ui import run  # noqa: E402

if __name__ == "__main__":
    sys.exit(run())
