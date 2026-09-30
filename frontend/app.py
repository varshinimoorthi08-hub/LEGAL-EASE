import base64
import os
from datetime import date

import requests
import streamlit as st
from dotenv import load_dotenv


# =========================================================
# Configuration
# =========================================================

load_dotenv()

BACKEND_URL = os.getenv(
    "BACKEND_URL",
    "http://127.0.0.1:8001"
).rstrip("/")

APP_NAME = os.getenv(
    "APP_NAME",
    "LegalEase"
)



# =========================================================
# Page Configuration
# =========================================================

st.set_page_config(
    page_title="LegalEase - AI Legal Document Generator",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# =========================================================
# Custom CSS
# =========================================================

st.markdown(
    """
    <style>
        .main {
            padding-top: 1rem;
        }

        .app-title {
            font-size: 2.6rem;
            font-weight: 700;
            margin-bottom: 0.2rem;
        }

        .app-subtitle {
            font-size: 1.05rem;
            color: #666;
            margin-bottom: 1.5rem;
        }

        .section-title {
            font-size: 1.25rem;
            font-weight: 600;
            margin-top: 1rem;
            margin-bottom: 0.75rem;
        }

        .status-card {
            padding: 0.8rem 1rem;
            border-radius: 10px;
            background-color: #f5f7fa;
            border: 1px solid #e2e6ea;
            margin-bottom: 1rem;
        }

        .preview-box {
            background-color: #ffffff;
            border: 1px solid #d9dee5;
            border-radius: 10px;
            padding: 1.5rem;
            min-height: 400px;
            color: #222222;
        }

        .stButton > button {
            width: 100%;
            border-radius: 8px;
            font-weight: 600;
        }

        div[data-testid="stDownloadButton"] button {
            width: 100%;
            border-radius: 8px;
        }

        .footer {
            text-align: center;
            color: #777;
            font-size: 0.85rem;
            margin-top: 3rem;
            padding-top: 1rem;
            border-top: 1px solid #ddd;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# Session State
# =========================================================

if "generated_text" not in st.session_state:
    st.session_state.generated_text = ""

if "generated_type" not in st.session_state:
    st.session_state.generated_type = ""

if "generated_terms" not in st.session_state:
    st.session_state.generated_terms = []

if "backend_status" not in st.session_state:
    st.session_state.backend_status = None


# =========================================================
# Helper Functions
# =========================================================

def check_backend():
    """
    Check whether the FastAPI backend is available.
    """
    try:
        response = requests.get(
            f"{BACKEND_URL}/health",
            timeout=5,
        )

        if response.status_code == 200:
            return response.json()

        return None

    except requests.RequestException:
        return None


def generate_document(payload):
    """
    Send document-generation request to the FastAPI backend.
    """
    try:
        response = requests.post(
            f"{BACKEND_URL}/generate",
            json=payload,
            timeout=120,
        )

        if response.status_code == 200:
            return response.json()

        try:
            error_data = response.json()
            error_message = error_data.get(
                "detail",
                "Unknown backend error."
            )
        except Exception:
            error_message = response.text

        st.error(
            f"Document generation failed "
            f"(HTTP {response.status_code}): {error_message}"
        )

        return None

    except requests.Timeout:
        st.error(
            "The request timed out. "
            "Please check that the backend and Gemini API are running."
        )
        return None

    except requests.ConnectionError:
        st.error(
            "Could not connect to the LegalEase backend. "
            "Make sure FastAPI is running on "
            f"{BACKEND_URL}."
        )
        return None

    except requests.RequestException as exc:
        st.error(f"Backend request failed: {exc}")
        return None


def export_document(
    document_type,
    text,
    export_format,
    terms,
    logo_file=None,
):
    """
    Ask the backend to create TXT, DOCX, or PDF output.
    """

    logo_base64 = None

    if logo_file is not None:
        try:
            logo_bytes = logo_file.getvalue()

            if logo_bytes:
                logo_base64 = (
                    "data:"
                    f"{logo_file.type};base64,"
                    f"{base64.b64encode(logo_bytes).decode('utf-8')}"
                )

        except Exception as exc:
            st.warning(
                f"Logo could not be processed: {exc}"
            )

    payload = {
        "document_type": document_type,
        "text": text,
        "format": export_format,
        "terms": terms,
        "logo_base64": logo_base64,
    }

    try:
        response = requests.post(
            f"{BACKEND_URL}/export",
            json=payload,
            timeout=60,
        )

        if response.status_code == 200:
            return response.content

        try:
            error_data = response.json()
            error_message = error_data.get(
                "detail",
                "Unknown export error."
            )
        except Exception:
            error_message = response.text

        st.error(
            f"Export failed "
            f"(HTTP {response.status_code}): {error_message}"
        )

        return None

    except requests.Timeout:
        st.error("The export request timed out.")
        return None

    except requests.ConnectionError:
        st.error(
            "Could not connect to the backend. "
            "Please make sure FastAPI is running."
        )
        return None

    except requests.RequestException as exc:
        st.error(f"Export request failed: {exc}")
        return None


def display_generated_document(text):
    """
    Display the generated document inside a readable HTML preview.
    """

    if not text:
        return

    escaped_text = (
        text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )

    lines = escaped_text.splitlines()

    html_lines = []

    for line in lines:
        stripped = line.strip()

        if not stripped:
            html_lines.append("<br>")
            continue

        if stripped.startswith("# "):
            html_lines.append(
                f"<h1>{stripped[2:]}</h1>"
            )

        elif stripped.startswith("## "):
            html_lines.append(
                f"<h2>{stripped[3:]}</h2>"
            )

        elif stripped.startswith("### "):
            html_lines.append(
                f"<h3>{stripped[4:]}</h3>"
            )

        elif stripped.startswith("- "):
            html_lines.append(
                f"<li>{stripped[2:]}</li>"
            )

        elif stripped.startswith("* "):
            html_lines.append(
                f"<li>{stripped[2:]}</li>"
            )

        else:
            html_lines.append(
                f"<p>{stripped}</p>"
            )

    html_content = "".join(html_lines)

    st.markdown(
        f"""
        <div class="preview-box">
            {html_content}
        </div>
        """,
        unsafe_allow_html=True,
    )


# =========================================================
# Header
# =========================================================

st.markdown(
    '<div class="app-title">⚖️ LegalEase</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="app-subtitle">'
    "AI-powered legal document drafting and export"
    "</div>",
    unsafe_allow_html=True,
)


# =========================================================
# Sidebar
# =========================================================

with st.sidebar:

    st.header("⚙️ System")

    if st.button("Check Backend"):
        with st.spinner("Checking backend..."):
            health = check_backend()

        st.session_state.backend_status = health

    health = st.session_state.backend_status

    if health:

        st.success("Backend connected")

        st.caption(
            f"Status: {health.get('status', 'unknown')}"
        )

        st.caption(
            f"Model: {health.get('gemini_model', 'unknown')}"
        )

        if health.get("demo_mode"):
            st.info(
                "Demo mode is enabled. "
                "Documents are generated using the built-in demo generator."
            )
        else:
            if health.get("gemini_configured"):
                st.success(
                    "Gemini API is configured."
                )
            else:
                st.warning(
                    "Gemini API key is not configured."
                )

    else:
        st.warning(
            "Backend status not checked."
        )

    st.divider()

    st.header("About")

    st.write(
        "LegalEase helps generate structured legal "
        "documents using Google's Gemini AI."
    )

    st.caption(
        "Always review AI-generated legal documents "
        "before using them for real-world purposes."
    )


# =========================================================
# Main Layout
# =========================================================

left_column, right_column = st.columns(
    [1, 1],
    gap="large",
)


# =========================================================
# LEFT COLUMN - INPUT FORM
# =========================================================

with left_column:

    st.markdown(
        '<div class="section-title">'
        "📄 Document Details"
        "</div>",
        unsafe_allow_html=True,
    )

    document_type = st.selectbox(
        "Document Type",
        options=[
            "Non-Disclosure Agreement",
            "Service Agreement",
            "Employment Agreement",
            "Freelance Agreement",
            "Consulting Agreement",
            "Rental Agreement",
            "Partnership Agreement",
            "Memorandum of Understanding",
            "Privacy Policy",
            "Terms and Conditions",
            "Custom Legal Document",
        ],
        index=0,
    )

    parties = st.text_area(
        "Parties",
        placeholder=(
            "Example:\n"
            "Party A: ABC Technologies Pvt. Ltd.\n"
            "Party B: John Doe"
        ),
        height=130,
        help=(
            "Enter the names and roles of all parties "
            "involved in the document."
        ),
    )

    st.markdown(
        '<div class="section-title">'
        "📌 Terms & Conditions"
        "</div>",
        unsafe_allow_html=True,
    )

    terms_text = st.text_area(
        "Enter one term per line",
        placeholder=(
            "Payment will be made within 30 days.\n"
            "The agreement will remain valid for one year.\n"
            "Confidential information must not be disclosed."
        ),
        height=180,
        help="Each line will be treated as a separate term.",
    )

    effective_date = st.date_input(
        "Effective Date",
        value=date.today(),
    )

    additional_instructions = st.text_area(
        "Additional Instructions",
        placeholder=(
            "Example: Include a confidentiality clause, "
            "termination clause, dispute resolution clause, "
            "and signature section."
        ),
        height=130,
    )

    logo_file = st.file_uploader(
        "Optional Company Logo",
        type=[
            "png",
            "jpg",
            "jpeg",
        ],
        help=(
            "The logo can be included in exported documents "
            "where supported."
        ),
    )

    st.divider()

    generate_button = st.button(
        "✨ Generate Legal Document",
        type="primary",
        use_container_width=True,
    )


# =========================================================
# GENERATE DOCUMENT
# =========================================================

if generate_button:

    if not parties.strip():
        st.error(
            "Please enter the parties involved "
            "before generating the document."
        )

    elif not terms_text.strip():
        st.error(
            "Please enter at least one term or condition."
        )

    else:

        terms = [
            term.strip()
            for term in terms_text.splitlines()
            if term.strip()
        ]

        payload = {
            "document_type": document_type,
            "parties": parties.strip(),
            "terms": terms,
            "effective_date": effective_date.isoformat(),
            "additional_instructions": (
                additional_instructions.strip()
            ),
        }

        with st.spinner(
            "🤖 Generating your legal document..."
        ):

            result = generate_document(payload)

        if result:

            st.session_state.generated_text = result.get(
                "text",
                "",
            )

            st.session_state.generated_type = result.get(
                "document_type",
                document_type,
            )

            st.session_state.generated_terms = terms

            st.success(
                "Legal document generated successfully!"
            )

            if result.get("demo_mode"):
                st.info(
                    "Demo mode was used. "
                    "Connect a Gemini API key and disable "
                    "DEMO_MODE for AI-generated documents."
                )


# =========================================================
# RIGHT COLUMN - PREVIEW / EDITOR
# =========================================================

with right_column:

    st.markdown(
        '<div class="section-title">'
        "👁️ Document Preview"
        "</div>",
        unsafe_allow_html=True,
    )

    if st.session_state.generated_text:

        display_generated_document(
            st.session_state.generated_text
        )

        st.markdown(
            '<div class="section-title">'
            "✏️ Editable Document"
            "</div>",
            unsafe_allow_html=True,
        )

        edited_text = st.text_area(
            "Edit the generated document before exporting",
            value=st.session_state.generated_text,
            height=550,
            label_visibility="collapsed",
        )

        st.session_state.generated_text = edited_text

        st.divider()

        st.markdown(
            '<div class="section-title">'
            "📥 Export Document"
            "</div>",
            unsafe_allow_html=True,
        )

        export_col1, export_col2, export_col3 = st.columns(3)

        # -------------------------------------------------
        # TXT
        # -------------------------------------------------

        with export_col1:

            if st.button(
                "Export TXT",
                use_container_width=True,
            ):

                with st.spinner("Creating TXT..."):

                    file_data = export_document(
                        document_type=(
                            st.session_state.generated_type
                        ),
                        text=st.session_state.generated_text,
                        export_format="txt",
                        terms=(
                            st.session_state.generated_terms
                        ),
                        logo_file=logo_file,
                    )

                if file_data:

                    st.download_button(
                        label="⬇️ Download TXT",
                        data=file_data,
                        file_name="legalease_document.txt",
                        mime="text/plain",
                        use_container_width=True,
                    )

        # -------------------------------------------------
        # DOCX
        # -------------------------------------------------

        with export_col2:

            if st.button(
                "Export DOCX",
                use_container_width=True,
            ):

                with st.spinner("Creating DOCX..."):

                    file_data = export_document(
                        document_type=(
                            st.session_state.generated_type
                        ),
                        text=st.session_state.generated_text,
                        export_format="docx",
                        terms=(
                            st.session_state.generated_terms
                        ),
                        logo_file=logo_file,
                    )

                if file_data:

                    st.download_button(
                        label="⬇️ Download DOCX",
                        data=file_data,
                        file_name="legalease_document.docx",
                        mime=(
                            "application/vnd.openxmlformats-"
                            "officedocument.wordprocessingml.document"
                        ),
                        use_container_width=True,
                    )

        # -------------------------------------------------
        # PDF
        # -------------------------------------------------

        with export_col3:

            if st.button(
                "Export PDF",
                use_container_width=True,
            ):

                with st.spinner("Creating PDF..."):

                    file_data = export_document(
                        document_type=(
                            st.session_state.generated_type
                        ),
                        text=st.session_state.generated_text,
                        export_format="pdf",
                        terms=(
                            st.session_state.generated_terms
                        ),
                        logo_file=logo_file,
                    )

                if file_data:

                    st.download_button(
                        label="⬇️ Download PDF",
                        data=file_data,
                        file_name="legalease_document.pdf",
                        mime="application/pdf",
                        use_container_width=True,
                    )

    else:

        st.info(
            "Your generated legal document will appear here."
        )

        st.markdown(
            """
            **How to use LegalEase**

            1. Select the type of legal document.
            2. Enter the parties involved.
            3. Add the required terms and conditions.
            4. Select the effective date.
            5. Add any additional instructions.
            6. Optionally upload a company logo.
            7. Click **Generate Legal Document**.
            8. Review and edit the generated document.
            9. Export it as TXT, DOCX, or PDF.
            """
        )


# =========================================================
# Footer
# =========================================================

st.markdown(
    """
    <div class="footer">
        LegalEase • AI Legal Document Generator
        <br>
        AI-generated documents should be reviewed by a
        qualified legal professional before use.
    </div>
    """,
    unsafe_allow_html=True,
)

