import time
from io import BytesIO

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from backend.config import get_settings


router = APIRouter()

settings = get_settings()


# =========================================================
# Request Models
# =========================================================

class GenerateRequest(BaseModel):
    document_type: str
    parties: str
    effective_date: str = ""
    terms: list[str]
    additional_instructions: str = ""


class ExportRequest(BaseModel):
    document_type: str = "Legal Document"
    text: str
    format: str


# =========================================================
# Demo Document Generator
# =========================================================

def generate_demo_document(request: GenerateRequest) -> str:

    terms_text = "\n".join(
        f"{index}. {term}"
        for index, term in enumerate(
            request.terms,
            start=1
        )
    )

    effective_date = (
        request.effective_date.strip()
        or "[INSERT EFFECTIVE DATE]"
    )

    instructions = (
        request.additional_instructions.strip()
        or "No additional instructions were provided."
    )

    return f"""# {request.document_type.upper()}

## Parties

{request.parties}

## Effective Date

{effective_date}

## Terms and Conditions

{terms_text}

## Additional Instructions

{instructions}

## Signatures

**Party 1 Signature:** ______________________________

**Name:** _________________________________________

**Date:** __________________________________________


**Party 2 Signature:** ______________________________

**Name:** _________________________________________

**Date:** __________________________________________


> **AI Draft Notice:** This document is an AI-generated first draft.
> It should be reviewed by a qualified legal professional before use.
"""


# =========================================================
# Gemini Document Generator
# =========================================================

def generate_gemini_document(
    request: GenerateRequest
):

    if not settings.gemini_api_key:

        raise RuntimeError(
            "Google Gemini API key is not configured."
        )

    from google import genai

    client = genai.Client(
        api_key=settings.gemini_api_key
    )

    terms_text = "\n".join(
        f"{index}. {term}"
        for index, term in enumerate(
            request.terms,
            start=1
        )
    )

    instructions = (
        request.additional_instructions.strip()
        or "No additional instructions were provided."
    )

    prompt = f"""
You are a legal document drafting assistant for an application called LegalEase.

Create a professional FIRST-DRAFT legal document based strictly on the information
provided by the user.

IMPORTANT:
- Do not invent names, dates, addresses, amounts, obligations, or other facts.
- If information is missing, use a clear placeholder such as [INSERT INFORMATION].
- Do not claim that the document is legally valid, legally binding, or suitable for
  a particular jurisdiction unless the user explicitly provides the relevant law
  and jurisdiction.
- This is an AI-generated draft and should be reviewed by a qualified legal
  professional before use.
- Use clear professional legal-document language.
- Organize the result with Markdown headings.
- Include signature sections where appropriate.
- Return ONLY the document itself. Do not explain your reasoning.

DOCUMENT TYPE:
{request.document_type}

PARTIES:
{request.parties}

EFFECTIVE DATE:
{request.effective_date}

TERMS AND CONDITIONS:
{terms_text}

ADDITIONAL INSTRUCTIONS:
{instructions}

Create the complete first-draft document now.
""".strip()

    max_retries = 3
    response = None

    for attempt in range(max_retries):

        try:

            response = client.models.generate_content(
                model=settings.gemini_model,
                contents=prompt,
            )

            break

        except Exception as exc:

            error_text = str(exc)

            if (
                "503" not in error_text
                and "UNAVAILABLE" not in error_text
            ):
                raise

            if attempt == max_retries - 1:

                raise RuntimeError(
                    "Gemini is temporarily unavailable after "
                    "multiple retries. Please try again in "
                    "a few minutes."
                ) from exc

            wait_seconds = 5 * (2 ** attempt)

            time.sleep(wait_seconds)

    if response is None:

        raise RuntimeError(
            "Gemini did not return a response."
        )

    generated_text = getattr(
        response,
        "text",
        None
    )

    if (
        not generated_text
        or not generated_text.strip()
    ):

        raise RuntimeError(
            "Gemini returned an empty response."
        )

    return generated_text.strip()


# =========================================================
# Health / System
# =========================================================

@router.get("/")
def router_root():

    return {
        "name": settings.app_name,
        "status": "running",
        "message": "LegalEase API router is running.",
    }


# =========================================================
# Generate Document
# =========================================================

@router.post("/generate")
def generate_document(
    request: GenerateRequest
):

    if not request.document_type.strip():

        raise HTTPException(
            status_code=400,
            detail="Document type is required."
        )

    if not request.parties.strip():

        raise HTTPException(
            status_code=400,
            detail="Parties information is required."
        )

    if not request.terms:

        raise HTTPException(
            status_code=400,
            detail=(
                "At least one term or condition "
                "is required."
            )
        )

    # -----------------------------------------------------
    # Demo Mode
    # -----------------------------------------------------

    if settings.demo_mode:

        text = generate_demo_document(
            request
        )

        return {
            "success": True,
            "document_type": request.document_type,
            "text": text,
            "demo_mode": True,
        }

    # -----------------------------------------------------
    # Gemini Mode
    # -----------------------------------------------------

    if not settings.gemini_api_key:

        raise HTTPException(
            status_code=500,
            detail=(
                "Gemini API key is not configured. "
                "Check GOOGLE_API_KEY in your .env file."
            ),
        )

    try:

        text = generate_gemini_document(
            request
        )

        return {
            "success": True,
            "document_type": request.document_type,
            "text": text,
            "demo_mode": False,
        }

    except Exception as exc:

        raise HTTPException(
            status_code=502,
            detail=(
                "Gemini document generation failed: "
                f"{exc}"
            ),
        )


# =========================================================
# Export Document
# =========================================================

@router.post("/export")
def export_document(
    request: ExportRequest
):

    export_format = (
        request.format
        .lower()
        .strip()
    )

    if not request.text.strip():

        raise HTTPException(
            status_code=400,
            detail="Document text is required."
        )

    # -----------------------------------------------------
    # TXT
    # -----------------------------------------------------

    if export_format == "txt":

        content = request.text.encode(
            "utf-8"
        )

        return Response(
            content=content,
            media_type=(
                "text/plain; charset=utf-8"
            ),
            headers={
                "Content-Disposition": (
                    'attachment; '
                    'filename="legalease_document.txt"'
                )
            },
        )

    # -----------------------------------------------------
    # DOCX
    # -----------------------------------------------------

    if export_format == "docx":

        try:

            from docx import Document

            document = Document()

            for line in request.text.splitlines():

                if line.startswith("### "):

                    document.add_heading(
                        line[4:],
                        level=3
                    )

                elif line.startswith("## "):

                    document.add_heading(
                        line[3:],
                        level=2
                    )

                elif line.startswith("# "):

                    document.add_heading(
                        line[2:],
                        level=1
                    )

                elif line.startswith("- "):

                    document.add_paragraph(
                        line[2:],
                        style="List Bullet"
                    )

                elif line.strip():

                    document.add_paragraph(
                        line
                    )

                else:

                    document.add_paragraph("")

            output = BytesIO()

            document.save(
                output
            )

            output.seek(0)

            return Response(
                content=output.getvalue(),
                media_type=(
                    "application/vnd.openxmlformats-"
                    "officedocument.wordprocessingml.document"
                ),
                headers={
                    "Content-Disposition": (
                        'attachment; '
                        'filename="legalease_document.docx"'
                    )
                },
            )

        except Exception as exc:

            raise HTTPException(
                status_code=500,
                detail=(
                    "DOCX export failed: "
                    f"{exc}"
                ),
            )

    # -----------------------------------------------------
    # PDF
    # -----------------------------------------------------

    if export_format == "pdf":

        try:

            from fpdf import FPDF

            pdf = FPDF()

            pdf.set_auto_page_break(
                auto=True,
                margin=15
            )

            pdf.add_page()

            pdf.set_font(
                "Helvetica",
                size=11
            )

            for line in request.text.splitlines():

                safe_line = (
                    line
                    .encode(
                        "latin-1",
                        errors="replace"
                    )
                    .decode("latin-1")
                )

                if not safe_line.strip():

                    pdf.ln(5)

                else:

                    pdf.multi_cell(
                        0,
                        7,
                        safe_line
                    )

            pdf_bytes = bytes(
                pdf.output()
            )

            return Response(
                content=pdf_bytes,
                media_type="application/pdf",
                headers={
                    "Content-Disposition": (
                        'attachment; '
                        'filename="legalease_document.pdf"'
                    )
                },
            )

        except Exception as exc:

            raise HTTPException(
                status_code=500,
                detail=(
                    "PDF export failed: "
                    f"{exc}"
                ),
            )

    # -----------------------------------------------------
    # Invalid Format
    # -----------------------------------------------------

    raise HTTPException(
        status_code=400,
        detail=(
            "Unsupported export format. "
            "Use txt, docx, or pdf."
        ),
    )