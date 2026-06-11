# Code signing Snoper

The CI pipeline signs both `Snoper.exe` and `Snoper-Setup.exe` automatically **if**
two GitHub secrets are present. Without them, builds still succeed — just unsigned.

## Secrets to add

In the repo: **Settings → Secrets and variables → Actions → New repository secret**

| Secret | Value |
|---|---|
| `SIGNING_PFX_BASE64` | base64 of your code-signing `.pfx` |
| `SIGNING_PFX_PASSWORD` | the `.pfx` password |

Once set, the next tagged release is signed. Remove them to go back to unsigned.

## Option A — Real certificate (removes SmartScreen warnings for everyone)

Buy an **OV or EV code-signing certificate** from a trusted CA (Sectigo, DigiCert,
SSL.com, etc.). OV is ~$200–400/yr; EV (~$400–600/yr, hardware token) builds
SmartScreen reputation fastest.

1. Complete the CA's identity verification.
2. Export the issued cert + private key as a `.pfx`.
3. Convert to base64 and add the two secrets:
   ```powershell
   [Convert]::ToBase64String([IO.File]::ReadAllBytes("mycert.pfx")) | Set-Clipboard
   ```
   (EV certs on a hardware token can't be exported to `.pfx`; those need the CA's
   cloud-signing or a self-hosted runner with the token attached — ask and I'll
   adapt the workflow.)

This is the **only** way to remove the "unknown publisher" / SmartScreen warning
for users who download the app fresh.

## Option B — Self-signed (personal / internal use only)

Removes the warning **only on machines where you install the cert as trusted**. It
does **not** help general distribution.

On a Windows machine:
```powershell
build\make_selfsigned_cert.ps1
```
This creates `snoper-codesign.pfx`, prints the base64, and shows how to trust it
locally. Add the two secrets from its output, and the build will sign with it.

## Verifying a signature

```powershell
signtool verify /pa /v dist\Snoper.exe
# or right-click the exe -> Properties -> Digital Signatures
```
