@echo off

:: ======================================================

:: MDZ-Demonstrator – EmAIls2Profile

:: Vollständiges Windows-Installationsscript (Batch)

:: ======================================================

 

:::: === Adminrechte prüfen / ggf. selbst neu starten ===

::net session >nul 2>&1

::if %errorLevel% neq 0 (

::    echo.

::    echo ⚠️  Dieses Script benötigt Administratorrechte.

::    echo Starte es neu mit Adminrechten...

::    powershell -Command "Start-Process '%~f0' -Verb runAs"

::    exit /b

::)

 

title MDZ-Demonstrator Installation

color 0A

echo.

echo ===============================================

echo   MDZ-Demonstrator – EmAIls2Profile

echo ===============================================

echo.

 

setlocal enabledelayedexpansion

 

:: === Variablen ===

set "REPO_URL=https://github.com/iph-hannover/MDZ-Demonstrator/archive/refs/heads/main.zip"

set "INSTALL_DIR=%USERPROFILE%\MDZ-Demonstrator"

set "ZIP_PATH=%TEMP%\MDZ-Demonstrator.zip"

set "LOG_FILE=%USERPROFILE%\mdz_install_log.txt"

set "OLLAMA_EXE=%TEMP%\OllamaSetup.exe"

 

:: ===============================================

:: 1. Python prüfen / installieren via winget

:: ===============================================

echo [1/7] Überprüfe Python ...

where python >nul 2>&1

if %errorlevel% neq 0 (

    echo → Installiere Python 3 via winget ...

    winget install --id Python.Python.3.12 -e --source winget --accept-package-agreements --accept-source-agreements

) else (

    echo ✓ Python bereits installiert.

)

where python >nul 2>&1

if %errorlevel% neq 0 (

    echo ❌ Python konnte nicht installiert werden. Bitte überprüfe winget.

    pause

    exit /b

)

 

:: ===============================================

:: 2. Ollama prüfen / installieren

:: ===============================================

echo [2/7] Überprüfe Ollama ...

where ollama >nul 2>&1

if %errorlevel% neq 0 (

    echo → Lade Ollama herunter ...

    curl -fsSL https://ollama.ai/download/OllamaSetup.exe -o "%OLLAMA_EXE%"

    echo → Installiere Ollama ...

    start /wait "" "%OLLAMA_EXE%"

    del "%OLLAMA_EXE%"

 

    echo → Schließe Ollama-GUI nach Installation ...

    taskkill /IM "ollama.exe" /F >nul 2>&1

) else (

    echo ✓ Ollama bereits installiert.

)

 

:: ===============================================

:: 3. Repository herunterladen (inkl. Unterordner)

:: ===============================================

echo [3/7] Lade Repository herunter (ohne Git) ...

if exist "%INSTALL_DIR%" (

    echo → Entferne alte Version ...

    rd /s /q "%INSTALL_DIR%"

)

 

curl -L -o "%ZIP_PATH%" "%REPO_URL%"

echo → Entpacke Dateien ...

powershell -Command "Expand-Archive -Path '%ZIP_PATH%' -DestinationPath '%INSTALL_DIR%' -Force"

 

:: Alle Dateien inkl. Unterordner korrekt verschieben

if exist "%INSTALL_DIR%\MDZ-Demonstrator-main" (

    powershell -Command "Get-ChildItem -Path '%INSTALL_DIR%\MDZ-Demonstrator-main' -Recurse | Move-Item -Destination '%INSTALL_DIR%' -Force"

    rd /s /q "%INSTALL_DIR%\MDZ-Demonstrator-main"

)

del "%ZIP_PATH%"

echo ✓ MDZ-Demonstrator erfolgreich heruntergeladen und entpackt.

 

:: ===============================================

:: 4. Python-Abhängigkeiten installieren

:: ===============================================

echo [4/7] Installiere Python-Abhängigkeiten ...

cd /d "%INSTALL_DIR%"

python -m pip install --upgrade pip

pip install -r requirements.txt

 

:: ===============================================

:: 5. LLM-Modell laden

:: ===============================================

echo [5/7] Lade LLM-Modell gemma3:12b ...

echo ⚠️  Achtung: ca. 8 GB Download – dies kann dauern.

ollama pull gemma3:12b

 

:: ===============================================
:: 6. Verknüpfung erstellen (Desktop, Fallback Startmenü)
:: ===============================================
echo [6/7] Erstelle Verknuepfung ...

:: Pfade sicher ermitteln (auch bei OneDrive-Umleitung)
for /f "usebackq delims=" %%D in (`powershell -NoProfile -Command "[Environment]::GetFolderPath('Desktop')"`) do set "DESKTOP_PATH=%%D"
for /f "usebackq delims=" %%S in (`powershell -NoProfile -Command "[Environment]::GetFolderPath('StartMenu')"`) do set "STARTMENU_PATH=%%S"

set "SHORTCUT_NAME=MDZ-Demonstrator.lnk"
set "SHORTCUT_DESKTOP=%DESKTOP_PATH%\%SHORTCUT_NAME%"
set "SHORTCUT_STARTMENU=%STARTMENU_PATH%\Programs\%SHORTCUT_NAME%"

:: Helper-Script zum unsichtbaren Start von PowerShell im TEMP lassen
(
  echo Set objShell = CreateObject("Wscript.Shell"^)
  echo objShell.Run "powershell -NoProfile -Command cd '%INSTALL_DIR%'; streamlit run gui.py", 0, False
) > "%TEMP%\start_mdz.vbs"

:: Schreibtest auf Desktop (CFA/OneDrive kann blockieren)
set "CAN_WRITE_DESKTOP=1"
(echo.) > "%DESKTOP_PATH%\.__mdz_test" 2>nul || set "CAN_WRITE_DESKTOP=0"
del "%DESKTOP_PATH%\.__mdz_test" 2>nul

if "%CAN_WRITE_DESKTOP%"=="1" (
  set "TARGET_SHORTCUT=%SHORTCUT_DESKTOP%"
) else (
  echo ⚠️  Desktop ist geschuetzt/nicht beschreibbar. Lege Verknuepfung im Startmenue an.
  set "TARGET_SHORTCUT=%SHORTCUT_STARTMENU%"
)

:: Verknuepfung per PowerShell-WSH erzeugen (kein separates .vbs noetig)
powershell -NoProfile -Command ^
  "$s=New-Object -ComObject WScript.Shell; " ^
  "$lnk=$s.CreateShortcut('%TARGET_SHORTCUT%'); " ^
  "$lnk.TargetPath='wscript.exe'; " ^
  "$lnk.Arguments='\"\"\"'+$env:TEMP+'\start_mdz.vbs\"\"\"'; " ^
  "$lnk.IconLocation='%INSTALL_DIR%\icon.ico'; " ^
  "$lnk.WorkingDirectory='%INSTALL_DIR%'; " ^
  "$lnk.Save()"

if exist "%TARGET_SHORTCUT%" (
  echo ✓ Verknuepfung erstellt: %TARGET_SHORTCUT%
) else (
  echo ❌ Konnte keine Verknuepfung anlegen. Bitte Ransomware-Schutz pruefen oder als Admin ausfuehren.
)


 

:: ===============================================

:: 7. Anwendung starten

:: ===============================================

echo [7/7] Starte Anwendung ...

start "" powershell -NoProfile -Command "cd '%INSTALL_DIR%'; streamlit run gui.py"

 

echo.

echo ✅ Installation abgeschlossen!

echo Logdatei: %LOG_FILE%

echo.

pause

exit /b