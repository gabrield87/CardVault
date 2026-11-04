# CardVault

**© Gabriel Dobre. Toate drepturile rezervate.** (anul se actualizează singur)

Portofel securizat pentru cardurile bancare, pentru Windows 10 (1809+) și Windows 11, pe **64 de biți**. Funcționează **strict offline** și pornește automat în limba sistemului de operare.

## Funcționare 100% offline

CardVault nu are nevoie de rețea și nu o folosește. Protecția are trei niveluri:

1. **În cod (toate variantele).** Primul lucru la pornire (`cardvault/netguard.py`) este un blocaj intern care oprește orice tentativă de:
   - conexiune la internet **sau** la rețeaua locală (TCP, UDP);
   - căutare DNS sau cerere HTTP;
   - lansare a altor programe;
   - încărcare a bibliotecilor Windows de rețea.
   
   Blocajul nu mai poate fi dezactivat până la închiderea aplicației. În bara de jos apare „● Offline”.
2. **În pachet.** Modulele de rețea nefolosite (TLS/SSL, e-mail, FTP, servere, Qt Network) sunt scoase complet din executabil.
3. **În sistem (varianta cu installer).** Installer-ul adaugă două reguli **Windows Firewall**, care blochează orice trafic al `CardVault.exe`, la intrare și la ieșire, pe orice tip de rețea. Regulile se șterg la dezinstalare.

**Doar locații locale:** baza de date poate fi creată, mutată, exportată sau deschisă doar pe discurile acestui calculator, inclusiv pe stick-uri USB.
- Căile de rețea (`\\server\...`) și unitățile mapate din rețea sunt refuzate.
- Dialogul de fișiere este cel intern al aplicației: nu încarcă extensii Windows și nu are secțiunea „Rețea”.
- Dacă alegi un folder sincronizat cu un serviciu cloud (OneDrive, Google Drive, Dropbox…), aplicația te avertizează înainte.

**Disclaimer:** la prima pornire, utilizatorul vede un mesaj care îi explică toate acestea. Mesajul poate fi redeschis oricând din *Ajutor → Confidențialitate și funcționare offline*.

> **Limite, spuse sincer:**
> - Blocajul din cod acoperă codul Python al aplicației. Componentele native (Qt, Windows) nu deschid conexiuni în CardVault, dar garanția la nivel de sistem pentru ele o dau regulile de firewall din varianta cu installer.
> - În varianta portabilă și în cea din Store nu există reguli de firewall; acolo rămân primele două niveluri.
> - Sincronizarea unui folder în cloud o face serviciul respectiv, nu CardVault. Fișierul rămâne oricum criptat.

## Funcții

- **Bază de date criptată, parolată.** Fiecare card este criptat cu AES-256-GCM, iar cheia se obține din parola principală prin scrypt.
- **Alegi unde stă fișierul `.cvw`.** La creare ești întrebat. Implicit: `C:\Users\<utilizator>\CardVault\wallet.cvw`, o locație locală, care nu se sincronizează și nu se șterge la dezinstalare.
- **Meniul *Fișier*:**
  - **Exportă baza de date…** — salvează o copie criptată.
  - **Mută baza de date…** — mută fișierul activ într-un alt loc.
  - **Deschide o bază de date existentă…** — de exemplu după o reinstalare sau de pe un stick USB.
- **Bara de jos** arată versiunea, calea bazei de date, indicatorul „Offline” și copyrightul.
- **Bănci emitente** (ING, BT, BRD, CEC, Raiffeisen, Revolut), cu culorile lor. Banca e obligatorie.
- **Alertă de expirare** la pornire.
- Date sensibile ascunse, clipboard golit automat după 30 s, blocare automată după 5 min.

## Copyright și versiune

- Numele, autorul și copyrightul sunt definite o singură dată, în `cardvault/__init__.py`. Anul se actualizează singur.
- Versiunea **vine din GitHub Release**: tag-ul `v1.3.0` devine automat versiunea `1.3.0` în aplicație, în detaliile `.exe`, în installer și în pachetul pentru Store.

## Build-uri automate la fiecare Release

La **publicarea unui Release** pe GitHub (tag `vX.Y.Z`) pornesc în paralel două workflow-uri:

| Workflow | Produce | Avertisment Windows |
|---|---|---|
| `release.yml` | `CardVault-X.Y.Z-win-x64-portable.zip` + `CardVault-Setup-X.Y.Z.exe` | Da, dacă nu sunt semnate |
| `store.yml` | `CardVault-X.Y.Z-store-x64.msix` (îl urci în Partner Center) | **Nu**: Microsoft Store îl semnează |

Fișierele se atașează automat la pagina Release-ului. Ambele workflow-uri pot fi rulate și manual, din *Actions → Run workflow*.

### Configurare pentru Microsoft Store (o singură dată)

1. Creează-ți cont gratuit de dezvoltator individual: <https://storedeveloper.microsoft.com>. Ai nevoie de un act de identitate și un selfie.
2. În Partner Center, **rezervă numele** „CardVault” (sau altul liber) și deschide *Product management → Product identity*.
3. În repo-ul GitHub mergi la **Settings → Secrets and variables → Actions → Variables** și adaugă:
   - `STORE_IDENTITY_NAME` = *Package/Identity/Name*
   - `STORE_PUBLISHER` = *Package/Identity/Publisher* (începe cu `CN=`)
   - `STORE_PUBLISHER_DISPLAY_NAME` = *Package/Properties/PublisherDisplayName*
4. La următorul Release apare fișierul `…-store-x64.msix`. Îl urci în Partner Center, la *Packages*.
   - Capabilitatea `runFullTrust` e standard pentru aplicațiile desktop. Dacă Store-ul cere o justificare: „aplicație desktop Win32 (Qt), rulează local, fără rețea”.

Până setezi variabilele, `store.yml` doar explică ce lipsește și nu blochează Release-ul.

În versiunea din Store, siglele băncilor se pun în `C:\Users\<utilizator>\CardVault\banks\`, pentru că folderul aplicației e doar-citire.

### Semnare pentru varianta portabilă și installer (opțional)

Dacă vei avea un certificat de code signing livrat ca `.pfx`, adaugă în **Secrets**:
- `CODE_SIGN_PFX_BASE64`;
- `CODE_SIGN_PASSWORD`.

Certificatele moderne OV/EV țin cheia pe token sau în cloud. Pentru ele, înlocuiește conținutul din `tools/sign.ps1` cu instrumentul furnizorului.

## De ce doar 64 de biți

PySide6 (Qt for Python) există doar pe 64 de biți, iar Windows 11 e oricum doar pe 64 de biți.

## Build local

Ai nevoie de Python 3.12. Rulează `build.bat`; rezultatul apare în `dist\CardVault\` (folosește `tools/build_windows.ps1`, la fel ca workflow-urile).
