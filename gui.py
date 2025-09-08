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


# =====================================
# ⚡ Globale Initialisierung: Profile
# =====================================

UPLOAD_FOLDER = "data"
EML_MAIL_FOLDER = UPLOAD_FOLDER + "/emails/eml"
JSON_MAIL_FOLDER = UPLOAD_FOLDER + "/emails/json"
JSON_PROFILE_FOLDER = UPLOAD_FOLDER + "/profiles/json"


# Zu verwendendes LLM-Modell als globale Variable definieren
MODEL = "gemma3:12b"

# Eigene Domains (für Erkennung von Antwort-Mails)
MY_DOMAINS = ["innovatek-solutions.de"]

os.makedirs(JSON_PROFILE_FOLDER, exist_ok=True)

# Aktive Unternehmen (Emails vorhanden)
company_files = glob.glob(os.path.join(JSON_MAIL_FOLDER, "*.json"))
active_companies = {os.path.splitext(os.path.basename(f))[0] for f in company_files}

# Profiles laden
profiles = {}
for profile_path in glob.glob(os.path.join(JSON_PROFILE_FOLDER, "profil_*.json")):
    profile_name = os.path.splitext(os.path.basename(profile_path))[0].replace(
        "profil_", ""
    )
    if profile_name in active_companies:
        with open(profile_path, "r", encoding="utf-8") as f:
            try:
                profiles[profile_name] = json.load(f)
            except Exception as e:
                st.warning(f"⚠️ Fehler beim Laden von {profile_path}: {e}")


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
                        body += part.get_payload(decode=True).decode(
                            charset, errors="ignore"
                        )
            else:
                charset = msg.get_content_charset() or "utf-8"
                body = msg.get_payload(decode=True).decode(charset, errors="ignore")

            body_clean = clean_body(body)

            emails_data.append(
                {
                    "filename": filename,
                    "date": date.isoformat() if date else None,
                    "from_email": sender_email,
                    "to_emails": to_cc,
                    "subject": subject,
                    "body": body_clean,
                }
            )

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

    # 🔧 Sicherstellen, dass der Ausgabeordner existiert
    os.makedirs(output_dir, exist_ok=True)

    # JSON speichern (nur für diese Firma)
    for company, mails in profiles.items():
        safe_name = company.replace(".", "_").replace("@", "_")
        out_path = os.path.join(output_dir, f"{safe_name}.json")
        # sicherstellen, dass der Ordner existiert
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(mails, f, indent=2, ensure_ascii=False)
        st.toast(f"✅ {len(mails)} Mail(s) verarbeitet für '{company}'")


# =====================================
# 📂 Verwaltung hochgeladener Emails
# =====================================
import glob


def manage_uploaded_emails(company_folder, output_dir):
    st.divider()
    st.subheader("🗑️ Emails löschen")

    # Alle EML-Dateien im globalen EML-Ordner sammeln
    eml_files = glob.glob(os.path.join(EML_MAIL_FOLDER, "*.eml"))

    if not eml_files:
        st.info("Keine Emails vorhanden.")
        return

    # Auswahl der zu löschenden Dateien
    files_to_delete = st.multiselect(
        "Zu löschende Dateien auswählen:",
        options=[os.path.basename(f) for f in eml_files],
    )

    if st.button("🗑️ Ausgewählte löschen"):
        for fname in files_to_delete:
            # EML löschen aus EML-Ordner (absoluter Pfad für Zuverlässigkeit)
            fpath = os.path.abspath(os.path.join(EML_MAIL_FOLDER, fname))
            if os.path.isfile(fpath):
                os.remove(fpath)
                st.success(f"'{fname}' wurde gelöscht ✅")
            else:
                st.warning(f"Datei nicht gefunden: {fpath}")

            # Alle Email-JSONs löschen (JSONs sind pro Kunde, nicht pro EML-Datei)
            removed = 0
            for jpath in glob.glob(os.path.join(output_dir, "*.json")):
                try:
                    os.remove(jpath)
                    removed += 1
                except Exception:
                    pass
            if removed:
                st.info(f"{removed} Email-JSON-Datei(en) gelöscht")

        # JSON-Dateien für diese Firma neu erzeugen
        process_uploaded_emails(company_folder, output_dir)

        # Seite neu laden (falls nötig)
        st.rerun()

    if st.button("🧹 Alle Emails löschen"):
        for fpath in eml_files:
            os.remove(fpath)
        st.success("Alle .eml-Dateien wurden gelöscht ✅")

        json_files = glob.glob(os.path.join(output_dir, "*.json"))
        for jpath in json_files:
            os.remove(jpath)
        st.info("Alle zugehörigen JSON-Dateien wurden gelöscht ✅")

        process_uploaded_emails(company_folder, output_dir)


# 🔹 Profile laden
@st.cache_data
def load_profiles():
    """Lädt alle Kundenprofile aus JSON."""
    profiles = {}
    for filepath in glob.glob(os.path.join(JSON_PROFILE_FOLDER, "*.json")):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                profile = data[0] if isinstance(data, list) and len(data) > 0 else data
                company_name = profile.get("company_name", os.path.basename(filepath))
                profiles[company_name] = profile
        except Exception as e:
            st.warning(f"⚠️ Fehler beim Laden von {filepath}: {e}")
    return profiles


# 🔹 Emails laden
@st.cache_data
def load_emails():
    """Lädt alle den gesamten Email Verlauf aus JSON."""
    emails = {}
    for filepath in glob.glob(os.path.join(JSON_MAIL_FOLDER, "*.json")):
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
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    return response["message"]["content"]


# -------------------------------
# App Layout
# -------------------------------

st.set_page_config(page_title="Kundenportal", page_icon="📊", layout="wide")

import streamlit as st
import base64, pathlib


# etwas Platz lassen, damit der Footer nicht Content überlappt
st.markdown(
    """
<style>
.block-container { padding-bottom: 100px; }  /* Platz für Footer */
.app-footer{
  position: fixed; left: 0; bottom: 0; width: 100%;
  padding: 10px 16px; border-top: 1px solid #eee;
  background: #ffffff; 
  box-shadow: 0 -1px 10px rgba(0,0,0,0.1);
    z-index: 9999;
}
.app-footer .logos{
  display: flex; gap: 48px; justify-content: center; align-items: center;
}
@media (max-width: 640px){ .app-footer .logos img{ height: 22px; } }
</style>
""",
    unsafe_allow_html=True,
)


def img64(path: str) -> str:
    mime = "image/svg+xml" if path.lower().endswith(".svg") else "image/png"
    data = pathlib.Path(path).read_bytes()
    b64 = base64.b64encode(data).decode()
    return f"data:{mime};base64,{b64}"


# Pfade anpassen (PNG/SVG verwenden!)
logo_left = img64("Logos/MD_zentrum_hannover_schutzzone_RGB.svg")
logo_right = img64("Logos/bmwi_logo_de.svg")

st.markdown(
    f"""
<div class="app-footer">
  <div class="logos">
    <img src="{logo_left}"  height="32">
    <img src="{logo_right}" height="32">
  </div>
</div>
""",
    unsafe_allow_html=True,
)


# # Logos hinzufügen (oben)
# col1, col2 = st.columns([1, 1])
# with col1:
#     st.image(
#         "Logos/MD_zentrum_hannover_schutzzone_RGB.svg",
#         width=200,
#     )
# with col2:
#     st.image("Logos/bmwi_logo_de.svg", width=150)

profiles = load_profiles()
emails = load_emails()

# -------------------------------
# Sidebar Navigation mit Kacheln
# -------------------------------


# Buttons in der Sidebar links ausrichten (einmalig injizieren)
st.sidebar.markdown(
    """
<style>
/* Gilt nur für Buttons in der Sidebar */
section[data-testid="stSidebar"] .stButton > button {
  width: 100%;
  display: flex;           /* sorgt dafür, dass justify-content wirkt */
  justify-content: flex-start; /* links ausrichten */
  text-align: left;
  gap: .5rem;              /* kleiner Abstand zwischen Emoji/Text */
  padding: .5rem .75rem;   /* optional: etwas angenehmerer Klickbereich */
}
section[data-testid="stSidebar"] .stButton > button p {
  margin: 0;               /* entfernt ggf. Extra-Abstand */
  width: 100%;
  text-align: left;        /* falls der Text in <p> gerendert wird */
}
</style>
""",
    unsafe_allow_html=True,
)


st.sidebar.title("📑 Navigation")

# Fixe Seiten
if st.sidebar.button("   🏠 Startseite", width="stretch"):
    st.query_params["page"] = "Startseite"
if st.sidebar.button(
    "1: 📧 Emails verwalten",
    width="stretch",
):
    st.query_params["page"] = "Emails verwalten"
if st.sidebar.button(
    "2: 🏢 KI-Kundenübersicht",
    width="stretch",
):
    st.query_params["page"] = "KI-Kundenübersicht"
if st.sidebar.button("3: 💻 KI-Chatbot", width="stretch"):
    st.query_params["page"] = "KI-Chatbot"

st.sidebar.markdown("---")
st.sidebar.markdown("# 👥 Kundenprofile")

# Kacheln für Unternehmen
for company, profile in profiles.items():
    contact = profile.get("contacts", [{}])[0]
    contact_name = contact.get("name", "Kein Kontakt")
    product_count = len(profile.get("products", []))
    contact_email = contact.get("email", "Keine Email")

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
        unsafe_allow_html=True,
    )


# Standard-Firma global setzen
if "selected_company" not in st.session_state:
    st.session_state.selected_company = "emails/eml"

selected_company = st.session_state.selected_company


# aktive Seite bestimmen
page = st.query_params.get("page", "Startseite")


# -------------------------------
# Seite 0: Startseite
# -------------------------------
if page == "Startseite":
    st.title("🏠 Startseite")
    st.markdown(
        "Willkommen zum Demonstrator Em<strong>AI</strong>ls2profile des **Mittelstand-Digital Zentrums Hannover**!\n\n"
        "Dieser **Prototyp** zeigt, wie aus einer Vielzahl unsortierter Emails mit verschiedenen Kunden lokal mit Hilfe von **Künstlicher Intelligenz (KI)** in Form von **Large-Language-Models (LLM)** automatisch **Kundenprofile** mit den wichstigsten Informationen generiert werden können. Anschließend können mit einem **KI-Chatbot** Fragen zu diesen Profilen beantwortet werden.\n\n"
        " **So startest du:** \n\n"
        "Schritt 1: Klicke links in der Navigationsleiste auf **📧 Emails verwalten** und lade dort einige Emails (im .eml-Dateiformat) hoch.\n\n"
        "Schritt 2: Klicke anschließend auf **🏢 KI-Kundenübersicht**, um die KI-generierten Kundenprofile anzusehen.\n\n"
        "Schritt 3: Klicke auf **💻 KI-Chatbot** und stelle Fragen zu Kunden, Produkten, Emails etc.\n\n"
        "> Hinweis: Dies ist ein Software-Demonstrator. Daten werden lokal im Projektordner gespeichert und können auf der Seite **📧 Emails verwalten** komplett gelöscht werden.",
        unsafe_allow_html=True,
    )


# -------------------------------
# Seite: 1 Emails verwalten
# -------------------------------
if page == "Emails verwalten":
    st.title("📧 Emails verwalten")

    os.makedirs(os.path.join(UPLOAD_FOLDER, selected_company), exist_ok=True)

    st.divider()
    st.subheader("📤 Emails hochladen")

    # Mehrfach-Upload erlauben
    uploaded_files = st.file_uploader(
        "📎 Emails (.eml) hochladen", type=["eml"], accept_multiple_files=True
    )

    # if uploaded_files:
    #     for uploaded_file in uploaded_files:
    #         save_path = os.path.join(
    #             UPLOAD_FOLDER, selected_company, uploaded_file.name
    #         )

    #         with open(save_path, "wb") as f:
    #             f.write(uploaded_file.getbuffer())
    #         # st.toast(f"✅ '{uploaded_file.name}' gespeichert in '{selected_company}'")

    if uploaded_files:
        new_uploads = []
        for uploaded_file in uploaded_files:
            save_path = os.path.join(
                UPLOAD_FOLDER, selected_company, uploaded_file.name
            )
            with open(save_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            new_uploads.append(uploaded_file.name)

        # Toast nur einmal für alle neuen Uploads
        if new_uploads:
            st.toast(
                f"✅ {len(new_uploads)} Datei(en) gespeichert in '{selected_company}'"
            )

    # 🚀 Direkt verarbeiten (nur diesen Firmenordner!)
    company_folder = os.path.join(UPLOAD_FOLDER, selected_company)
    process_uploaded_emails(company_folder, JSON_MAIL_FOLDER)
    manage_uploaded_emails(company_folder, JSON_MAIL_FOLDER)


# -------------------------------
# Seite 2: KI-Kundenübersicht
# -------------------------------
elif page == "KI-Kundenübersicht":
    st.title("🏢 KI-Kundenübersicht")

    os.makedirs(JSON_PROFILE_FOLDER, exist_ok=True)

    if st.button("🔄 Kundenprofile aktualisieren"):
        # 1) Cache leeren, damit keine veralteten Daten verwendet werden
        try:
            st.cache_data.clear()
        except Exception:
            pass

        # 2) Alte Profile löschen
        removed_profiles = 0
        for p in glob.glob(os.path.join(JSON_PROFILE_FOLDER, "*.json")):
            try:
                os.remove(p)
                removed_profiles += 1
            except Exception:
                pass
        if removed_profiles:
            st.info(f"🗑️ {removed_profiles} bestehende Profil(e) gelöscht")

        # 3) Neue Profile aus vorhandenen Email-JSONs generieren
        st.info("Starte Verarbeitung der Emails…")

        for filepath in glob.glob(os.path.join(JSON_MAIL_FOLDER, "*.json")):
            filename = os.path.basename(filepath)
            output_file = os.path.join(JSON_PROFILE_FOLDER, f"profil_{filename}")

            st.write(f"📥 Verarbeite `{filename}` ...")

            # Emails laden
            with open(filepath, "r", encoding="utf-8") as f:
                try:
                    emails = json.load(f)
                except Exception as e:
                    st.error(f"⚠️ Fehler beim Laden von {filename}: {e}")
                    continue

            # Prompt vorbereiten
            prompt = f"""
            Du bekommst eine Liste von Emails im JSON-Format.
            Erstelle für jede Kundenfirma nur ein Profil.

            Jedes Profil enthält:
            - Name des Unternehmens
            - alle eindeutigen Kontakte (Name + Email)
            - eine Liste der angefragten oder bestellten Produkte
            - Summary des Email-Verlaufs (max. 8 Sätze). Die Zusammenfassung muss summary heißen.

            Regeln:
            - Die Kontakte der Firma Innovatek Solutions sollen nicht aufgenommen werden.
            - Das heißt, eine Kunden-Emailadresse kann nicht auf @innovatek-solutions.de enden.
            - Gib das Ergebnis ausschließlich als gültiges JSON-Array zurück, ohne Markdown.

            Hier sind die Emails:
            {json.dumps(emails, ensure_ascii=False, indent=2)}
            """

            # LLM ausführen
            result = subprocess.run(
                ["ollama", "run", MODEL],
                input=prompt.encode("utf-8"),
                capture_output=True,
            )
            output_text = result.stdout.decode("utf-8").strip()

            # Eventuelle ```json``` Tags entfernen
            cleaned_output = re.sub(r"```json|```", "", output_text).strip()

            # JSON parsen
            try:
                kundenprofil = json.loads(cleaned_output)
            except json.JSONDecodeError:
                st.warning(
                    f"⚠️ JSON-Parsing fehlgeschlagen bei {filename}, Rohtext gespeichert."
                )
                kundenprofil = {"raw_output": output_text}

            # Speichern
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(kundenprofil, f, indent=2, ensure_ascii=False)

            st.success(f"✅ Profil gespeichert: `{output_file}`")

        st.success("🎉 Alle Kundenprofile wurden aktualisiert!")
        st.cache_data.clear()
        st.rerun()

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
                    st.markdown("**📝 KI-Zusammenfassung:**")
                    st.info(profile["summary"])

                st.divider()


# -------------------------------
# Seite 2b: Einzelne Kundenprofile
# -------------------------------

elif page in profiles:
    profile = profiles[page]
    st.title(f"🏭 {profile.get('company_name', page)}")

    # --- Profil Übersicht ---
    if "summary" in profile:
        st.markdown("### 📝 KI-Zusammenfassung")
        st.info(profile["summary"])

    if "products" in profile and profile["products"]:
        st.markdown("### 📦 Produkte")
        st.write(", ".join(profile["products"]))

    if "contacts" in profile and profile["contacts"]:
        st.markdown("### 👤 Kontakte")
        for c in profile["contacts"]:
            st.write(f"- {c.get('name')} ({c.get('email')})")

    st.divider()

    # --- Email Verlauf ---
    st.markdown("### 📧 Email Verlauf")

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
        best_match = difflib.get_close_matches(
            expected_norm, normalized_keys.keys(), n=1, cutoff=0.6
        )
        if best_match:
            return normalized_keys[best_match[0]]

        return None

    # Erwarteter Key (vom Page-Namen)
    expected_key = page
    real_key = find_best_key(expected_key, list(emails.keys()))

    if real_key is None:
        st.warning(
            f"❌ Kein Match für '{expected_key}'.\n\n📂 Vorhandene Keys:\n{list(emails.keys())}"
        )
        mails = []
    else:
        mails = emails.get(real_key, [])

    if not mails:
        st.info("📭 Keine Emails für diesen Kunden vorhanden.")
    else:
        mails_sorted = sorted(mails, key=lambda x: x.get("date", ""), reverse=True)
        my_domains = tuple(d.lower() for d in MY_DOMAINS)

        for mail in mails_sorted:
            date_str = mail.get("date", "")
            try:
                date_fmt = datetime.fromisoformat(date_str).strftime("%d.%m.%Y %H:%M")
            except:
                date_fmt = date_str

            frm = (mail.get("from_email") or "").lower()
            frm_domain = frm.split("@")[-1] if "@" in frm else frm
            outgoing = (
                frm_domain.endswith(my_domains) if frm_domain else False
            )  # rechts ausrichten

            # Zwei Spalten – Kunde links / du rechts
            left_ratio, right_ratio = (0.38, 0.62) if outgoing else (0.62, 0.38)
            col_left, col_right = st.columns([left_ratio, right_ratio])
            target_col = col_right if outgoing else col_left

            with target_col:
                with st.expander(f"{date_fmt} | {mail.get('subject', 'Kein Betreff')}"):
                    st.write(f"**Von:** {mail.get('from_email', 'Unbekannt')}")
                    st.write(f"**Betreff:** {mail.get('subject', 'Kein Betreff')}")
                    st.write("---")
                    st.write(mail.get("body", "📭 Kein Inhalt"))


# -------------------------------
# Seite 3: Chatbot
# -------------------------------
if page == "KI-Chatbot":
    st.title("💻 KI-Chatbot")
    st.write("Stelle Fragen zu den Kundenprofilen.")

    # Chat-Verlauf & State initialisieren
    if "history" not in st.session_state:
        st.session_state["history"] = []
    if "show_examples" not in st.session_state:
        st.session_state["show_examples"] = False

    # 🧪 Beispielfragen
    sample_questions = [
        "An welchen Produkten hat Herr Vogt Interesse gezeigt?",
        "Gehören Frau Klein und Herr Reuter zum selben Unternehmen?",
        "Wie viele Produkte hat Mueller Maschinenbau bisher bei uns bestellt?",
        "Welcher Kunde wartet noch auf eine Rückmeldung von uns?",
        "Hat Frau Klein Interesse am Predictive Maintenance Plus Paket?",
        "Welche Firma hat einen Care Basic Wartungsvertrag?",
    ]

    # Toggle zum Anzeigen/Ausblendenl
    if st.button("✨ Beispielfragen", use_container_width=False):
        st.session_state["show_examples"] = not st.session_state["show_examples"]
        st.rerun()

    # Buttons nur rendern, wenn sichtbar
    if st.session_state["show_examples"]:
        cols = st.columns(2)
        for i, q in enumerate(sample_questions):
            if cols[i % 2].button(q, key=f"ex_{i}", use_container_width=True):
                st.session_state["queued_prompt"] = q
                st.rerun()

    # Falls eine Beispielfrage geklickt wurde: wie User-Eingabe verarbeiten
    if "queued_prompt" in st.session_state:
        q = st.session_state.pop("queued_prompt")
        st.session_state["history"].append(("user", q))
        antwort = chatbot(q, profiles)
        st.session_state["history"].append(("assistant", antwort))

    # Chatverlauf anzeigen
    for role, content in st.session_state["history"]:
        with st.chat_message(role):
            st.markdown(content)

    # Normale Chat-Eingabe
    if prompt := st.chat_input("💬 Frage eingeben..."):
        st.session_state["history"].append(("user", prompt))
        with st.chat_message("user"):
            st.markdown(prompt)

        antwort = chatbot(prompt, profiles)
        st.session_state["history"].append(("assistant", antwort))
        with st.chat_message("assistant"):
            st.markdown(antwort)
