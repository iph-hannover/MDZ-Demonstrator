import streamlit as st
import json
import glob
import os
from datetime import datetime
import ollama
import email
from email.header import decode_header
from email.utils import parsedate_to_datetime, parseaddr, getaddresses
from collections import defaultdict
import subprocess
import re
import difflib

# --- Ordnerpfade ---
PROFILE_FOLDER = "Json/Profiles"
MAIL_FOLDER = "Json/Company"
UPLOAD_FOLDER = "Kundenmails"
#Eigene Domains (für Erkennung von Antwort-Mails)
MY_DOMAINS = ["innovatek-solutions.de"]

# -------------------------------
# Funktionen
# -------------------------------

def clean_body(text):
    """Reduziert die Email so, dass nur noch die Antwort drauf ist."""
    marker = "-----Ursprüngliche Nachricht-----"
    if marker in text:
        text = text.split(marker)[0]
    return text.strip()

def extract_company(from_email, to_emails):
    """Bestimmt die Firma anhand der Absender-/Empfänger-Domain."""
    if not from_email:
        return "Unbekannt"
    from_domain = from_email.split("@")[-1].lower()

    if any(from_domain.endswith(my_dom) for my_dom in MY_DOMAINS):
        if to_emails:
            return to_emails[0].split("@")[-1].lower()
        return "Unbekannt"
    return from_domain

def decode_subject(raw_subject):
    """Dekodiert den Betreff und entfernt fehlerhafte Sonderzeichen."""
    if not raw_subject:
        return ""
    decoded_parts = decode_header(raw_subject)
    subject = ""
    for part, enc in decoded_parts:
        if isinstance(part, bytes):
            try:
                subject += part.decode(enc or "utf-8", errors="ignore")
            except:
                subject += part.decode("utf-8", errors="ignore")
        else:
            subject += part
    return subject

def process_uploaded_emails(company_folder, output_dir):
    """Verarbeitet alle .eml-Dateien eines Firmenordners und speichert JSON."""
    emails_data = []

    for filename in os.listdir(company_folder):
        if filename.lower().endswith(".eml"):
            filepath = os.path.join(company_folder, filename)
            with open(filepath, "rb") as f:
                msg = email.message_from_binary_file(f)

            # Metadaten extrahieren
            date = parsedate_to_datetime(str(msg["Date"])) if msg["Date"] else None
            _, sender_email = parseaddr(str(msg["From"]) if msg["From"] else "")

            to_cc = []
            if msg["To"]:
                to_cc.extend([addr for _, addr in getaddresses([msg["To"]])])
            if msg["Cc"]:
                to_cc.extend([addr for _, addr in getaddresses([msg["Cc"]])])

            
            subject = decode_subject(msg["Subject"])

            # Body
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        charset = part.get_content_charset() or "utf-8"
                        body += part.get_payload(decode=True).decode(charset, errors="ignore")
            else:
                charset = msg.get_content_charset() or "utf-8"
                body = msg.get_payload(decode=True).decode(charset, errors="ignore")

            body_clean = clean_body(body)

            emails_data.append({
                "filename": filename,
                "date": date.isoformat() if date else None,
                "from_email": sender_email,
                "to_emails": to_cc,
                "subject": subject, 
                "body": body_clean,
            })

    # Sortieren + Duplikate
    emails_data.sort(key=lambda x: x["date"] or "", reverse=False)
    unique_emails, seen_bodies = [], set()
    for mail in emails_data:
        body_hash = hash(mail["body"])
        if body_hash not in seen_bodies:
            seen_bodies.add(body_hash)
            unique_emails.append(mail)

    # Nach Firma gruppieren
    profiles = defaultdict(list)
    for mail in unique_emails:
        company = extract_company(mail["from_email"], mail["to_emails"])
        mail_copy = {k: v for k, v in mail.items() if k != "to_emails"}
        profiles[company].append(mail_copy)

    # JSON speichern (nur für diese Firma)
    for company, mails in profiles.items():
        safe_name = company.replace(".", "_").replace("@", "_")
        out_path = os.path.join(output_dir, f"{safe_name}.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(mails, f, indent=2, ensure_ascii=False)
        st.success(f"✅ {len(mails)} Mails verarbeitet → {out_path}")

# 🔹 Profile laden
@st.cache_data
def load_profiles():
    """Lädt alle Kundenprofile aus JSON."""
    profiles = {}
    for filepath in glob.glob(os.path.join(PROFILE_FOLDER, "*.json")):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                profile = data[0] if isinstance(data, list) and len(data) > 0 else data
                company_name = profile.get("company_name", os.path.basename(filepath))
                profiles[company_name] = profile
        except Exception as e:
            st.warning(f"⚠️ Fehler beim Laden von {filepath}: {e}")
    return profiles


# 🔹 E-Mails laden
@st.cache_data
def load_emails():
    """Lädt alle den gesamten E-Mail Verlauf aus JSON."""
    emails = {}
    for filepath in glob.glob(os.path.join(MAIL_FOLDER, "*.json")):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                company = os.path.splitext(os.path.basename(filepath))[0]
                emails[company] = data
        except Exception as e:
            st.warning(f"⚠️ Fehler beim Laden von {filepath}: {e}")
    return emails


# 🔹 Chatbot-Funktion (alle Profile)
def chatbot(query, all_profiles):
    """Chatbot, der Kundenfragen anhand der Profile beantwortet."""
    system_prompt = """Du bist ein Kundenservice-Assistent.
Antworte auf Basis aller vorhandenen Kundenprofile.
Wenn die Frage zu einem bestimmten Unternehmen gehört, beantworte sie mit Bezug auf dieses Profil.
Wenn keine Information vorhanden ist, sage: 'Das weiß ich leider nicht'. """

    user_prompt = f"""
Frage: {query}

Hier sind alle Kundenprofile:
{json.dumps(all_profiles, indent=2, ensure_ascii=False)}
"""

    response = ollama.chat(
        model="gemma3:12b",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    )
    return response["message"]["content"]


# -------------------------------
# App Layout
# -------------------------------

st.set_page_config(page_title="Kundenportal", page_icon="📊", layout="wide")

profiles = load_profiles()
emails = load_emails()

# -------------------------------
# Sidebar Navigation mit Kacheln
# -------------------------------
st.sidebar.title("📑 Navigation")

# Fixe Seiten
if st.sidebar.button("🤖 Chatbot"):
    st.query_params["page"] = "Chatbot"
if st.sidebar.button("📤 E-Mails hochladen"):
    st.query_params["page"] = "Mail Upload"
if st.sidebar.button("👥 Profile aktualisieren"):
    st.query_params["page"] = "Kundenprofile aktualisieren"
if st.sidebar.button("🏢 Firmenübersichten"):
    st.query_params["page"] = "Firmenübersichten"

st.sidebar.markdown("---")
st.sidebar.markdown("### 👥 Unternehmen")

# Kacheln für Unternehmen
for company, profile in profiles.items():
    contact = profile.get("contacts", [{}])[0]
    contact_name = contact.get("name", "Kein Kontakt")
    product_count = len(profile.get("products", []))
    contact_email = contact.get("email", "Keine E-Mail")
    
    st.sidebar.markdown(
        f"""
        <a href="/?page={company}" target="_self" style="text-decoration:none;">
            <div style="
                border:1px solid #ddd;
                border-radius:10px;
                padding:10px;
                margin-bottom:10px;
                background-color:#f9f9f9;
                transition: all 0.2s ease-in-out;
            " onmouseover="this.style.backgroundColor='#eee';" onmouseout="this.style.backgroundColor='#f9f9f9';">
                <h4 style="margin:0;color:#333;">🏭 {company}</h4>
                <p style="margin:0;color:#666;font-size:13px;">
                    👤 {contact_name}
                </p>
                <p style="margin:0;color:#666;font-size:12px;">
                    ✉️ {contact_email}
                </p>
                <p style="margin:0;color:#999;font-size:12px;">
                    📦 {product_count} Produkte
                </p>
            </div>
        </a>
        """,
        unsafe_allow_html=True
    )


# aktive Seite bestimmen
page = st.query_params.get("page", "Chatbot")


# -------------------------------
# Seite 1: Chatbot
# -------------------------------
if page == "Chatbot":
    st.title("🤖 Kunden-Chatbot")
    st.write("Stelle Fragen zu den Kundenprofilen.")

    # Chat-Verlauf initialisieren
    if "history" not in st.session_state:
        st.session_state["history"] = []

    # Chatverlauf anzeigen
    for role, content in st.session_state["history"]:
        with st.chat_message(role):
            st.markdown(content)

    # Chat-Eingabe
    if prompt := st.chat_input("💬 Frage eingeben..."):
        st.session_state["history"].append(("user", prompt))
        with st.chat_message("user"):
            st.markdown(prompt)

        # Bot antwortet unter Verwendung aller Profile
        antwort = chatbot(prompt, profiles)
        st.session_state["history"].append(("assistant", antwort))
        with st.chat_message("assistant"):
            st.markdown(antwort)


# -------------------------------
# Seite:2 Mail Upload
# -------------------------------
if page == "Mail Upload":
    st.title("📤 Kundenmails hochladen")

    # Firmenordner vorbereiten
    existing_companies = [d for d in os.listdir(UPLOAD_FOLDER) if os.path.isdir(os.path.join(UPLOAD_FOLDER, d))]

    selected_company = st.selectbox("Firma auswählen oder neu eingeben:", ["Neue Firma hinzufügen..."] + existing_companies)

    if selected_company == "Neue Firma hinzufügen...":
        new_company = st.text_input("🔹 Neuer Firmenname")
        if new_company:
            selected_company = new_company
            os.makedirs(os.path.join(UPLOAD_FOLDER, selected_company), exist_ok=True)
    elif selected_company:
        os.makedirs(os.path.join(UPLOAD_FOLDER, selected_company), exist_ok=True)

    # Mehrfach-Upload erlauben
    uploaded_files = st.file_uploader("📎 E-Mails (.eml) hochladen", type=["eml"], accept_multiple_files=True)

    if uploaded_files and selected_company:
        for uploaded_file in uploaded_files:
            save_path = os.path.join(UPLOAD_FOLDER, selected_company, uploaded_file.name)
            with open(save_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            st.success(f"✅ '{uploaded_file.name}' gespeichert in '{selected_company}'")

        # 🚀 Direkt verarbeiten (nur diesen Firmenordner!)
        company_folder = os.path.join(UPLOAD_FOLDER, selected_company)
        process_uploaded_emails(company_folder, MAIL_FOLDER)
                    


# ------------------------------------
# Seite 3: Kundenprofile aktualisieren
# ------------------------------------
elif page == "Kundenprofile aktualisieren":
    st.title("👥 Kundenprofile aktualisieren")

    input_folder = "Json/Company"    # E-Mail JSONs
    output_folder = "Json/Profiles"  # Kundenprofile
    model = "gemma3:12b"

    os.makedirs(output_folder, exist_ok=True)

    if st.button("🔄 Kundenprofile aktualisieren"):
        st.info("Starte Verarbeitung aller Firmen-E-Mails...")

        for filepath in glob.glob(os.path.join(input_folder, "*.json")):
            filename = os.path.basename(filepath)
            output_file = os.path.join(output_folder, f"profil_{filename}")

            st.write(f"📥 Verarbeite `{filename}` ...")

            # E-Mails laden
            with open(filepath, "r", encoding="utf-8") as f:
                try:
                    emails = json.load(f)
                except Exception as e:
                    st.error(f"⚠️ Fehler beim Laden von {filename}: {e}")
                    continue

            # Prompt vorbereiten
            prompt = f"""
            Du bekommst eine Liste von E-Mails im JSON-Format.
            Erstelle für jede Kundenfirma nur ein Profil.

            Jedes Profil enthält:
            - Name des Unternehmens
            - alle eindeutigen Kontakte (Name + E-Mail)
            - eine Liste der angefragten oder bestellten Produkte
            - kurze summary des E-Mail-Verlaufs (max. 5 Sätze)

            Regeln:
            - Die Kontakte der Firma Innovatek Solutions sollen nicht aufgenommen werden.
            - Gib das Ergebnis ausschließlich als gültiges JSON-Array zurück, ohne Markdown.

            Hier sind die E-Mails:
            {json.dumps(emails, ensure_ascii=False, indent=2)}
            """

            # LLM ausführen
            result = subprocess.run(
                ["ollama", "run", model],
                input=prompt.encode("utf-8"),
                capture_output=True
            )
            output_text = result.stdout.decode("utf-8").strip()

            # Eventuelle ```json``` Tags entfernen
            cleaned_output = re.sub(r"```json|```", "", output_text).strip()

            # JSON parsen
            try:
                kundenprofil = json.loads(cleaned_output)
            except json.JSONDecodeError:
                st.warning(f"⚠️ JSON-Parsing fehlgeschlagen bei {filename}, Rohtext gespeichert.")
                kundenprofil = {"raw_output": output_text}

            # Speichern
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(kundenprofil, f, indent=2, ensure_ascii=False)

            st.success(f"✅ Profil gespeichert: `{output_file}`")

        st.success("🎉 Alle Kundenprofile wurden aktualisiert!")
        st.cache_data.clear()
        st.rerun()


# -------------------------------
# Seite 3: Firmenübersicht
# -------------------------------
elif page == "Firmenübersichten":
    st.title("🏢 Firmenübersichten")

    if not profiles:
        st.warning("Keine Profile gefunden.")
    else:
        for company, profile in profiles.items():
            with st.container():
                st.markdown(f"### 🏭 {profile.get('company_name', 'Unbekannt')}")

                if "contacts" in profile and profile["contacts"]:
                    st.markdown("**👤 Kontakte:**")
                    for c in profile["contacts"]:
                        st.write(f"- {c.get('name')} ({c.get('email')})")

                if "products" in profile and profile["products"]:
                    st.markdown("**📦 Produkte:**")
                    st.write(", ".join(profile["products"]))

                if "summary" in profile:
                    st.markdown("**📝 Zusammenfassung:**")
                    st.info(profile["summary"])

                st.divider()


# -------------------------------
# Seite 4+: Einzelne Kundenprofile
# -------------------------------
elif page in profiles:
    profile = profiles[page]
    st.title(f"🏭 {profile.get('company_name', page)}")

    # --- Profil Übersicht ---
    if "summary" in profile:
        st.markdown("### 📝 Zusammenfassung")
        st.info(profile["summary"])

    if "products" in profile and profile["products"]:
        st.markdown("### 📦 Produkte")
        st.write(", ".join(profile["products"]))

    if "contacts" in profile and profile["contacts"]:
        st.markdown("### 👤 Kontakte")
        for c in profile["contacts"]:
            st.write(f"- {c.get('name')} ({c.get('email')})")

    st.divider()

    # --- E-Mail Verlauf ---
    st.markdown("### 📧 E-Mail Verlauf")

    def normalize_key(name: str) -> str:
        name = (
            name.lower()
            .replace("_", "-")
            .replace(" ", "-")
            .replace("ä", "ae")
            .replace("ö", "oe")
            .replace("ü", "ue")
            .replace("ß", "ss")
        )
        # Firmen-Rechtsformen entfernen
        for suffix in ["-gmbh", "-mbh", "-ag", "-kg", "-ug", "-inc", "-ltd"]:
            if name.endswith(suffix):
                name = name.replace(suffix, "")
        return name.strip("-")


    def find_best_key(expected: str, keys: list[str]) -> str | None:
        expected_norm = normalize_key(expected)
        normalized_keys = {normalize_key(k): k for k in keys}

        # 1️⃣ Direkter exakter Treffer
        if expected_norm in normalized_keys:
            return normalized_keys[expected_norm]

        # 2️⃣ Fuzzy-Matching (findet auch Tippfehler oder Teilmatches)
        best_match = difflib.get_close_matches(expected_norm, normalized_keys.keys(), n=1, cutoff=0.6)
        if best_match:
            return normalized_keys[best_match[0]]

        return None


    # Erwarteter Key (vom Page-Namen)
    expected_key = page
    real_key = find_best_key(expected_key, list(emails.keys()))

    if real_key is None:
        st.warning(f"❌ Kein Match für '{expected_key}'.\n\n📂 Vorhandene Keys:\n{list(emails.keys())}")
        mails = []
    else:
        mails = emails.get(real_key, [])

    if not mails:
        st.info("📭 Keine E-Mails für diesen Kunden vorhanden.")
    else:
        mails_sorted = sorted(mails, key=lambda x: x.get("date", ""))
        for mail in mails_sorted:
            date_str = mail.get("date", "")
            try:
                date_fmt = datetime.fromisoformat(date_str).strftime("%d.%m.%Y %H:%M")
            except:
                date_fmt = date_str

            with st.expander(f"{date_fmt} | {mail.get('subject', 'Kein Betreff')}"):
                st.write(f"**Von:** {mail.get('from_email', 'Unbekannt')}")
                st.write(f"**Betreff:** {mail.get('subject', 'Kein Betreff')}")
                st.write("---")
                st.write(mail.get("body", "📭 Kein Inhalt"))
