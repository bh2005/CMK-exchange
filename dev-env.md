# Checkmk Plug-in Development Environment – Windows (WSL2 + Debian)

**Ziel:** Lokale, saubere Checkmk-Test-Instanz + komfortable Plug-in-Entwicklung (Checks, Agent-Plug-ins)  
**Betriebssystem:** Windows 10/11  
**Empfohlener Stack:** WSL2 + Debian + Docker + VS Code (Dev Containers)  
**Warum so?** Checkmk ist Linux-nativ → WSL2 vermeidet Windows-Pfad-/Python-Probleme. Docker + Dev Containers = reproduzierbar, schnell, IntelliSense + Debugging top.

## Voraussetzungen

- Windows 10/11 (Build ≥ 19041 für WSL2)
- ~8–16 GB RAM empfohlen (für Container + mehrere Sites)
- Internet für Downloads

## 1. WSL2 + Debian installieren

PowerShell (Admin):
```powershell
wsl --install -d Debian
```
→ Neustart falls gefragt. Danach Debian aus Startmenü öffnen → Username + Passwort setzen.

Debian updaten & Basics installieren:
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install curl git wget ca-certificates sudo build-essential -y
```

**Optional: systemd aktivieren** (sehr empfohlen für Docker/Services):
```bash
sudo bash -c 'echo -e "[boot]\nsystemd=true" >> /etc/wsl.conf'
wsl --shutdown   # aus PowerShell
```
Debian neu starten → `systemctl --version` prüfen.

## 2. Docker in Debian installieren

```bash
sudo apt install docker.io docker-compose -y
sudo usermod -aG docker $USER
newgrp docker   # oder logout + login
```

**Alternative (besser für GUI/Integration):**  
Docker Desktop auf Windows installieren → Settings → Resources → WSL Integration → Debian aktivieren.  
Dann nutzt du Docker aus WSL heraus nahtlos.

## 3. VS Code einrichten (auf Windows)

Installiere:
- [Visual Studio Code](https://code.visualstudio.com/)
- Extensions:
  - Remote – WSL
  - Dev Containers
  - Python (Microsoft)
  - Pylance
  - Ruff (oder mypy)
  - Optional: Docker, GitLens

## 4. Dev-Setup aufbauen (zwei Varianten)

### Variante A: Empfohlen – Dev Container (am komfortabelsten)

1. Checkmk-Repo oder Dev-Template klonen (in Debian):
   ```bash
   cd ~
   git clone https://github.com/Checkmk/checkmk.git   # offizielles Repo (master/2.4.0 etc.)
   # Oder ein Community-Dev-Template (oft empfohlen im Forum):
   # git clone https://github.com/<user>/checkmk-dev-template   # z. B. Jiuka-ähnlich – im Forum nachschauen
   cd checkmk   # oder dein Template-Ordner
   ```

2. VS Code starten:
   ```bash
   code .
   ```
   → „Reopen in Container?“ → **Yes**  
   (Falls `.devcontainer/devcontainer.json` vorhanden → baut Checkmk-Container automatisch)

3. Im Container bist du drin:
   - Checkmk läuft (meist Site `cmk` oder `mysite`)
   - Plug-ins: `~/local/lib/python3/cmk_addons/plugins/<dein_namespace>/agent_based/`
   - Testen: `cmk -D localhost`, `cmk --debug -v -II localhost`, `cmk -nv localhost`

### Variante B: Saubere omd-Installation (ohne Docker-Container)

In Debian:
```bash
# Checkmk Raw/Cloud .deb runterladen (aktuelle Version von checkmk.com/download)
wget https://download.checkmk.com/checkmk/2.4.0pX/check-mk-raw-2.4.0pX_0.bookworm_amd64.deb   # anpassen!
sudo apt install ./check-mk-raw-*.deb

# Site erstellen
sudo omd create devsite240
sudo omd start devsite240
```

Mehrere Sites:
```bash
sudo omd create devsite241
```

GUI-Zugriff → siehe unten.

## 5. GUI-Zugriff vom Windows-Browser

**Bei omd-Installation (Variante B):**
- http://localhost:5000/devsite240/check_mk/  
  (Login: cmkadmin + Passwort via `omd su devsite240` → `htpasswd ~/etc/htpasswd cmkadmin`)

**Bei Dev-Container (Variante A):**
- Schau in VS Code → Reiter **Ports** (unten) → forwarded Port (meist 5000 → localhost:5000)
- Oder docker-compose.yml prüfen (ports: Abschnitt)
- Typisch: http://localhost:5000/cmk/check_mk/ oder http://localhost:5000/devsite/check_mk/

**Mehrere Sites parallel?** Alle auf Port 5000 – unterscheide via Pfad: `/devsite240/check_mk/`, `/devsite241/check_mk/`

## 6. Plug-in-Entwicklung – Quick Start

1. In Container/omd-Site:
   ```bash
   mkdir -p ~/local/lib/python3/cmk_addons/plugins/mycompany/agent_based
   cd $_
   touch my_check.py
   ```

2. In VS Code: IntelliSense für `cmk.base.plugins.agent_based` sollte direkt gehen (dank Container-Env).

3. Debugging: `.vscode/launch.json` anpassen (meist schon vorhanden):
   - Breakpoints in `check_function()` setzen
   - Run → Start Debugging mit `cmk`-Call

4. Linting: Ruff oder mypy nutzen (in settings.json oder pyproject.toml konfigurieren)

## 7. Tipps & Troubleshooting

- Port 5000 belegt? → `omd config devsite240` → Apache-Port ändern (z. B. 5001)
- Kein Zugriff? → `omd status` prüfen, `ss -tuln | grep 5000`
- WSL-Probleme? → `wsl --shutdown` (PowerShell)
- Python-Version: Checkmk nutzt meist 3.11/3.12 → passt in Debian 12/Testing
- Update Checkmk: Neues .deb installieren oder Container neu bauen

Viel Erfolg beim Check- & Agent-Plug-in-Schreiben!  
Fragen? → Checkmk Forum: „Best IDE Configuration Practices for Checkmk Plug-in Development“

Letztes Update: März 2026
