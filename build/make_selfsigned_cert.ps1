# ============================================================
#  Generate a SELF-SIGNED code-signing certificate for Snoper.
#  Run on Windows (PowerShell). Produces snoper-codesign.pfx and
#  prints the base64 + instructions for the GitHub secrets.
#
#  IMPORTANT: a self-signed cert removes the "unknown publisher"
#  warning ONLY on machines where you install this cert into
#  "Trusted Root Certification Authorities" + "Trusted Publishers".
#  It does NOT satisfy Microsoft SmartScreen for public distribution
#  — that needs a cert from a trusted CA (Sectigo/DigiCert, paid).
# ============================================================
param(
  [string]$Subject  = "CN=Snoper",
  [string]$OutPfx   = "snoper-codesign.pfx",
  [string]$Password = ""
)

if ([string]::IsNullOrEmpty($Password)) {
  $sec = Read-Host "Choose a password for the .pfx" -AsSecureString
} else {
  $sec = ConvertTo-SecureString $Password -AsPlainText -Force
}

Write-Host "Creating self-signed code-signing certificate ($Subject)..."
$cert = New-SelfSignedCertificate `
  -Type CodeSigningCert `
  -Subject $Subject `
  -KeyUsage DigitalSignature `
  -KeyExportPolicy Exportable `
  -CertStoreLocation Cert:\CurrentUser\My `
  -NotAfter (Get-Date).AddYears(5)

Export-PfxCertificate -Cert $cert -FilePath $OutPfx -Password $sec | Out-Null
Write-Host "Wrote $OutPfx"

$b64 = [Convert]::ToBase64String([IO.File]::ReadAllBytes($OutPfx))
$b64 | Set-Content "$OutPfx.base64.txt"

Write-Host ""
Write-Host "=== Add these GitHub repo secrets (Settings > Secrets and variables > Actions) ==="
Write-Host "  SIGNING_PFX_BASE64    = (contents of $OutPfx.base64.txt)"
Write-Host "  SIGNING_PFX_PASSWORD  = (the password you just chose)"
Write-Host ""
Write-Host "To trust it on THIS machine (so the warning goes away locally), run as admin:"
Write-Host "  Import-PfxCertificate -FilePath $OutPfx -CertStoreLocation Cert:\LocalMachine\Root -Password `$sec"
Write-Host "  Import-PfxCertificate -FilePath $OutPfx -CertStoreLocation Cert:\LocalMachine\TrustedPublisher -Password `$sec"
