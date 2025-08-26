# MDZ-Demonstrator
Kundenportal

Ein interaktives Tool zur Verwaltung von Kundenmails und -profilen, inklusive eines Chatbots zur Beantwortung von Kundenfragen.  

📂 Projektstruktur  
gui.py – Hauptprogramm, alle Funktionen laufen hier zusammen  
Kundenmails/ – Hochgeladene E-Mails im .eml-Format  
Json/Company/ – JSON-Dateien pro Firma mit vollständigem E-Mail-Verlauf  
Json/Profiles/ – Generierte Kundenprofile aus E-Mail-Verläufen  

⚙️ Abhängigkeiten installieren:  
pip install streamlit==1.48.1 ollama==0.5.3  
LLM-Modell gemma3:12b offline pullen:  
ollama pull gemma3:12b  

🚀 Starten  
streamlit run gui.py  
Die Anwendung öffnet sich im Browser.  

🛠 Funktionen  
1️⃣ Chatbot  
Beantwortet Kundenfragen auf Basis der gespeicherten Profile.  
Nutzt das LLM gemma3:12b für intelligente Antworten.  
Chatverlauf wird gespeichert, neue Fragen können jederzeit gestellt werden.  
2️⃣ E-Mail Upload  
Hochladen von .eml-Dateien über die Oberfläche.  
Automatische Verarbeitung und Speicherung als JSON im Firmenordner.  
E-Mails werden bereinigt (nur Antworten) und nach Firma gruppiert.  
3️⃣ Kundenprofile aktualisieren  
Erstellt aus allen E-Mail-JSONs ein konsolidiertes Kundenprofil.  
Enthält: Firmenname, Kontakte, Produkte, Zusammenfassung des E-Mail-Verlaufs.  
Innovatek Solutions Kontakte werden automatisch ausgeschlossen.  
4️⃣ Firmenübersichten  
Zeigt alle Kundenprofile mit Kontakten, Produkten und Zusammenfassung.  
5️⃣ Einzelne Kundenprofile  
Detailansicht pro Kunde inklusive E-Mail-Verlauf.  
Fuzzy-Matching für Firmennamen, um Tippfehler abzufangen.  

📌 Hinweise  
Ordnerstruktur einhalten, sonst können E-Mails/Profiles nicht geladen werden.  
JSON-Dateien werden nach Firma gespeichert: Punkte und @ im Dateinamen werden ersetzt.  
Das LLM muss offline verfügbar sein, sonst funktionieren Chatbot und Profil-Generierung nicht.  
Streamlit-Cache wird automatisch geleert, wenn Profile aktualisiert werden.  

📖 Nutzung  
Chatbot: Fragen direkt an Kundenprofile stellen.  
E-Mail Upload: Neue .eml-Dateien hochladen → automatisch verarbeitet.  
Kundenprofile aktualisieren: Alle JSONs verarbeiten → Profile aktualisieren.  
Firmenübersichten & Einzelprofile: Überblick über Kundeninformationen & E-Mail-Verläufe.  
