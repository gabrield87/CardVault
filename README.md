# CardVault

**© Gabriel Dobre. All rights reserved.** (the year updates automatically)

A secure wallet for your bank cards, for Windows 10 (1809+) and Windows 11, **64-bit**. It works **strictly offline** and starts in the operating system's language.

## 100% offline operation

CardVault does not need the network and does not use it. Protection works on three levels:

1. **In code (all editions).** The very first thing at startup (`cardvault/netguard.py`) is an internal lockdown that blocks any attempt to:
   - connect to the internet **or** to the local network (TCP, UDP);
   - perform a DNS lookup or an HTTP request;
   - launch other programs;
   - load Windows networking libraries.

   The lockdown cannot be switched off until the app exits. The status bar shows "● Offline".
2. **In the package.** Unused networking modules (TLS/SSL, e-mail, FTP, servers, Qt Network) are removed from the executable entirely.
3. **In the system (installer edition).** The installer adds two **Windows Firewall** rules that block all traffic of `CardVault.exe`, inbound and outbound, on every network profile. The rules are removed on uninstall.

**Local locations only:** the database can be created, moved, exported or opened only on this computer's drives, USB sticks included.
- Network paths (`\\server\...`) and mapped network drives are rejected.
- The file dialog is the app's own: it loads no Windows shell extensions and has no "Network" section.
- If you pick a folder synced by a cloud service (OneDrive, Google Drive, Dropbox…), the app warns you first.

**Disclaimer:** on first launch the user sees a message explaining all of the above. It can be reopened at any time from *Help → Privacy and offline operation*.

> **Limitations, stated honestly:**
> - The in-code lockdown covers the app's Python code. Native components (Qt, Windows) do not open connections in CardVault, but the system-level guarantee for them comes from the firewall rules of the installer edition.
> - The portable and Store editions have no firewall rules; they rely on the first two levels.
> - Syncing a folder to the cloud is done by that service, not by CardVault. The file stays encrypted either way.

## Features

- **Encrypted, password-protected database.** Every card is encrypted with AES-256-GCM; the key is derived from the master password with scrypt.
- **You choose where the `.cvw` file lives.** You are asked when the wallet is created. Default: `C:\Users\<user>\CardVault\wallet.cvw` — local, not synced, and not deleted on uninstall.
- **File menu:**
  - **Export database…** — saves an encrypted copy.
  - **Move database…** — moves the active file to another place.
  - **Open an existing database…** — e.g. after reinstalling, or from a USB stick.
- **Status bar** shows the version, the database path, the "Offline" badge and the copyright.
- **Issuing banks** (ING, BT, BRD, CEC, Raiffeisen, Revolut) with their colours. Choosing a bank is mandatory.
- **Expiry alert** on startup.
- Sensitive data hidden by default, clipboard cleared after 30 s, automatic lock after 5 minutes.
- **Interface language:** English, Romanian, German, French, Spanish, Italian — picked automatically from Windows (English otherwise), changeable from *Settings → Language*.

## Copyright and version

- The name, author and copyright are defined once, in `cardvault/__init__.py`. The year updates automatically.
- The version **comes from the GitHub Release**: tag `v1.3.0` automatically becomes version `1.3.0` in the app, in the `.exe` details, in the installer and in the Store package.

## Automatic builds on every Release

When you **publish a Release** on GitHub (tag `vX.Y.Z`), two workflows run in parallel:

| Workflow | Produces | Windows warning |
|---|---|---|
| `release.yml` | `CardVault-X.Y.Z-win-x64-portable.zip` + `CardVault-Setup-X.Y.Z.exe` | Yes, unless signed |
| `store.yml` | `CardVault-X.Y.Z-store-x64.msix` (upload it to Partner Center) | **No**: the Microsoft Store signs it |

The files are attached to the Release page automatically. Both workflows can also be run by hand from *Actions → Run workflow*.

### Microsoft Store setup (once)

1. Create a free individual developer account at <https://storedeveloper.microsoft.com> (an ID document and a selfie are required).
2. In Partner Center, **reserve the name** "CardVault" (or another free name) and open *Product management → Product identity*.
3. In the GitHub repository go to **Settings → Secrets and variables → Actions → Variables** and add:
   - `STORE_IDENTITY_NAME` = *Package/Identity/Name*
   - `STORE_PUBLISHER` = *Package/Identity/Publisher* (starts with `CN=`)
   - `STORE_PUBLISHER_DISPLAY_NAME` = *Package/Properties/PublisherDisplayName*
4. On the next Release a `…-store-x64.msix` file appears. Upload it in Partner Center under *Packages*.
   - The `runFullTrust` capability is standard for desktop apps. If the Store asks for a justification: "Win32 (Qt) desktop application, runs locally, no network access".

Until these variables are set, `store.yml` only explains what is missing and does not fail the Release.

In the Store edition, bank logos go in `C:\Users\<user>\CardVault\banks\`, because the app folder is read-only.

### Signing the portable edition and the installer (optional)

If you get a code-signing certificate delivered as a `.pfx` file, add these **Secrets**:
- `CODE_SIGN_PFX_BASE64`
- `CODE_SIGN_PASSWORD`

Modern OV/EV certificates keep the key on a token or in the cloud. For those, replace the contents of `tools/sign.ps1` with the provider's tool.

## Why 64-bit only

PySide6 (Qt for Python) exists only for 64-bit Windows, and Windows 11 is 64-bit only anyway.

## Local build

You need Python 3.12. Run `build.bat`; the result is in `dist\CardVault\` (it uses `tools/build_windows.ps1`, exactly like the workflows).

## Bank logos (optional)

Logos are registered trademarks and are not included. Put PNG files with a transparent background in the `banks` folder next to `CardVault.exe` (`ing.png`, `bt.png`, `brd.png`, `cec.png`, `raiffeisen.png`, `revolut.png`) and the app shows them automatically. Without them, the bank name is shown on the card.
