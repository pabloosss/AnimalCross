"""Stop only a verified local API listener, never all Python processes."""
import json
import os
import subprocess
from urllib.parse import urlsplit


def stop_service(url, kind):
    if os.name != 'nt': raise RuntimeError('Zatrzymywanie usług obsługiwane jest na Windows.')
    parsed=urlsplit(url)
    if parsed.hostname not in ('localhost','127.0.0.1') or not parsed.port:
        raise ValueError('Zatrzymywanie wymaga lokalnego adresu i portu.')
    if kind not in ('ollama','comfy'): raise ValueError('Nieznana usługa.')
    # The only interpolated values are a validated integer and a closed enum.
    script = """
$ErrorActionPreference='Stop'
$ids=@(Get-NetTCPConnection -State Listen -LocalPort PORTVALUE -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique)
$stopped=@()
foreach($processId in $ids){
 $p=Get-CimInstance Win32_Process -Filter "ProcessId=$processId"
 $valid=$false
 if('KINDVALUE' -eq 'ollama'){ $valid=($p.Name -ieq 'ollama.exe') }
 else { $valid=($p.Name -match '^python(w)?\\.exe$' -and $p.CommandLine -match 'ComfyUI[\\\\/]main\\.py') }
 if(-not $valid){ throw "Nie rozpoznano procesu na porcie. Nie zatrzymano PID $processId." }
 Stop-Process -Id $processId -ErrorAction Stop
 $stopped+=$processId
}
ConvertTo-Json -Compress -InputObject @{stopped=$stopped}
""".replace('PORTVALUE',str(parsed.port)).replace('KINDVALUE',kind)
    result=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',script],capture_output=True,text=True,timeout=20,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if result.returncode: raise RuntimeError(result.stderr.strip() or 'Windows odmówił zatrzymania procesu.')
    return json.loads(result.stdout)

