# MDZ-Demonstrator – EmAIls2profile

Ein interaktives Tool zur Verwaltung von Kundenmails und -profilen, inklusive KI-Chatbot zur Beantwortung von Kundenfragen. Der Demonstrator zeigt, wie aus unsortierten E-Mails mit Hilfe von Large Language Models (LLM) automatisch Kundenprofile generiert werden können.

## Voraussetzungen

- **Python 3.8+** (mit pip installiert)
- **Ollama** (für lokale LLM-Ausführung)
- **Git** (zum Klonen des Repositories)

## Installation

### 1. Ollama installieren (Grundvoraussetzung)

**Windows:**
- Lade Ollama von [https://ollama.ai](https://ollama.ai) herunter
- Führe das Installationsprogramm aus
- Öffne eine neue Eingabeaufforderung und teste: `ollama --version`

**macOS:**
```bash
brew install ollama
```

**Linux:**
```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

### 2. LLM-Modell herunterladen
```bash
ollama pull gemma3:12b
```
⚠️ **Wichtig:** Dieser Download ist ca. 8GB groß und kann je nach Internetverbindung längere Zeit dauern.

### 3. Repository klonen
```bash
git clone https://github.com/iph-hannover/MDZ-Demonstrator.git
cd MDZ-Demonstrator
```

### 4. Python-Abhängigkeiten installieren
```bash
pip install -r requirements.txt
```

### 5. Anwendung starten
```bash
streamlit run gui.py
```
Die Anwendung öffnet sich automatisch im Browser unter `http://localhost:8501`.

## Projektstruktur

- `gui.py` – Hauptprogramm, steuert Upload, Verarbeitung, Profil-Generierung und Chatbot
- `data/emails/eml/` – Hochgeladene E-Mails im .eml-Format
- `data/emails/json/` – JSON-Dateien pro Firma mit vollständigem E-Mail-Verlauf
- `data/profiles/json/` – Generierte Kundenprofile aus E-Mail-Verläufen
- `Logos/` – Logo-Dateien für die Anwendung
- `requirements.txt` – Python-Abhängigkeiten

## Funktionen

### 1. **E-Mail-Verwaltung**
- **Upload:** Hochladen von `.eml`-Dateien über die Oberfläche
- **Verarbeitung:** Automatische Extraktion von Metadaten (Absender, Empfänger, Betreff, Datum)
- **Bereinigung:** E-Mail-Body wird von Antwort-Ketten befreit
- **Gruppierung:** E-Mails werden automatisch nach Firmen-Domains sortiert
- **Löschung:** Einzelne E-Mails können ausgewählt und gelöscht werden

### 2. **KI-gestützte Profilerstellung**
- **Automatische Analyse:** Das LLM `gemma3:12b` analysiert E-Mail-Verläufe
- **Profil-Generierung:** Erstellt strukturierte Kundenprofile mit:
  - Firmenname und Kontaktdaten
  - Liste der angefragten/bestellten Produkte
  - KI-Zusammenfassung des E-Mail-Verlaufs (max. 8 Sätze)
- **Cache-Management:** Automatisches Leeren des Caches bei Aktualisierungen

### 3. **Intelligenter Chatbot**
- **Kontextbasierte Antworten:** Beantwortet Fragen auf Basis der gespeicherten Profile
- **Fuzzy-Matching:** Erkennt Firmennamen auch bei Tippfehlern
- **Chatverlauf:** Gespräche werden während der Session gespeichert
- **Beispielfragen:** Vorgefertigte Fragen für einfachen Einstieg

### 4. **Benutzeroberfläche**
- **Responsive Design:** Funktioniert auf Desktop und Tablet
- **Sidebar-Navigation:** Übersichtliche Menüführung
- **Firmen-Kacheln:** Schneller Zugriff auf einzelne Kundenprofile
- **E-Mail-Verlauf:** Chronologische Darstellung mit Links/Rechts-Ausrichtung

## Systemanforderungen

- **RAM:** Mindestens 8GB (empfohlen: 16GB für `gemma3:12b`)
- **Speicherplatz:** ~10GB (8GB für LLM + 2GB für Anwendung)
- **Internet:** Nur für initiale Installation erforderlich
- **Prozessor:** x64-Architektur (Intel/AMD)
- **Graphikkarte:** Nvidia RTX 4090 empfohlen

---

## Beispiel-Workflow

1. **E-Mails hochladen**
   - Navigiere zu "📧 Emails verwalten"
   - Lade eine oder mehrere `.eml`-Dateien hoch
   - E-Mails werden automatisch verarbeitet und als JSON gespeichert

2. **E-Mails löschen (optional)**
   - Wähle zu löschende E-Mails aus der Liste
   - Klicke "🗑️ Ausgewählte löschen"
   - E-Mails und zugehörige JSONs werden entfernt

3. **Kundenprofile aktualisieren**
   - Wechsle zu "🏢 KI-Kundenübersicht"
   - Klicke "🔄 Kundenprofile aktualisieren"
   - KI erstellt Profile aus aktuellen E-Mail-JSONs

4. **Profile ansehen**
   - Überblick aller Kundenprofile in der Hauptansicht
   - Klick auf Firmen-Kachel für detaillierte Einzelansicht
   - E-Mail-Verlauf chronologisch sortiert

5. **Chatbot nutzen**
   - Wechsle zu "💻 KI-Chatbot"
   - Stelle Fragen zu Kunden, Produkten oder E-Mail-Verläufen
   - Nutze Beispielfragen für schnellen Einstieg

## Fehlerbehebung

**Ollama läuft nicht:**
```bash
# Ollama-Service starten
ollama serve
```

**Modell nicht gefunden:**
```bash
# Modell erneut herunterladen
ollama pull gemma3:12b
```

**Port bereits belegt:**
```bash
# Streamlit auf anderem Port starten
streamlit run gui.py --server.port 8502
```

**Speicherprobleme:**
- Verwende kleineres Modell: `ollama pull gemma3:8b`
- Passe MODEL-Variable in `gui.py` entsprechend an

## Technische Details

- **Framework:** Streamlit für Web-UI
- **LLM-Integration:** Ollama für lokale Model-Ausführung
- **E-Mail-Parsing:** Python `email`-Bibliothek
- **Datenformat:** JSON für strukturierte Speicherung
- **Cache:** Streamlit `@st.cache_data` für Performance

## Sicherheit & Datenschutz

- **Lokale Verarbeitung:** Alle Daten bleiben auf dem lokalen System
- **Keine Cloud-Verbindung:** LLM läuft vollständig offline
- **Datenschutz:** E-Mails werden nur lokal im `data/`-Ordner gespeichert
- **Löschung:** Vollständige Entfernung durch Löschen des Projektordners

## Lizenz

MIT License - Siehe LICENSE-Datei für Details.

---
