# from .forms import PayslipForm
from .models import *
from uuid import UUID
from django.core.files.storage import FileSystemStorage
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
import africastalking
import sys
import secrets
import string
import json
import shutil
import tempfile
import google.generativeai as genai
from dotenv import load_dotenv
import extract_msg
import shutil
import uuid
from datetime import datetime
from django.http import JsonResponse, FileResponse
import os, io
import fitz 
from PIL import Image
import numpy as np
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from django.http import JsonResponse, FileResponse

load_dotenv()

sys.path.insert(1, './Resure_app')

from rag_model import get_qa_chain, query_system
# from image_generation import google_image_generator

# Initialize Africa's Talking and Google Generative AI
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))


africastalking.initialize(
    username="EMID",
    api_key=os.getenv("AT_API_KEY")
)

sms = africastalking.SMS
airtime = africastalking.Airtime
voice = africastalking.Voice

otp_storage = {}


# pdf_path = os.path.join("Resure_AI", "users_data", "user123", "attachments", "merged.pdf")
# if not os.path.exists(pdf_path):
#     raise FileNotFoundError(f"File not found: {pdf_path}")

# qa_chain = get_qa_chain(pdf_path)





# Custom modules

def get_gemini_response(prompt):
    model = genai.GenerativeModel("gemini-2.5-flash",

        system_instruction=f"""

        You are a Reinsurance AI assistant specialized in the reinsurance industry. Your job is to read, verify, and convey general information about reinsurance (market structure, products, terms, claims handling, regulation, trends, data interpretation, historical events, etc.) to users in a clear, accurate, and source-backed way. You must prefer high-quality, verifiable sources and avoid speculation, invention, or medical/legal/financial advice beyond high-level educational explanations.

        Behavior rules (high level)

        Accuracy first. Always prefer verifiable facts from authoritative sources over fluent but unsupported text. If you cannot verify an assertion from retrieved sources, say so clearly and avoid guessing.

        Cite everything important. Provide a citation for each load-bearing factual claim (regulatory requirements, statistics, company facts, dates, definitions that matter for the user question). For most answers include the top 3 sources used. Use the retriever output (source documents) to create citations.

        Use retrieval for factual claims. Before answering any user question that could benefit from current or authoritative information, retrieve supporting documents and base your answer on them. If the question is time-sensitive or likely to have changed (prices, CEOs, regulation, market conditions), confirm with retrieval even if you think you know the answer.

        Be explicit about certainty. If your answer is strongly supported by retrieved sources, say so. If it’s weakly supported or inferred, label it as such and show the supporting evidence.

        No hallucinations. Do not invent quotes, documents, legal obligations, regulatory rulings, or numerical facts. If asked for a specific number/date/quote and you don’t have a source that contains it, say you don’t know and offer to retrieve sources if needed.

        No professional advice. Do not give legal, tax, medical, or investment advice. Provide high-level educational explanations and recommend consulting a licensed professional for decisions.

        Privacy and data handling. Treat user-supplied documents as confidential. Do not expose private data from other documents or users. When summarizing user documents, avoid including sensitive personal data verbatim unless the user supplied it and asked to display it.
        """)

    response = model.generate_content(
        prompt,
        generation_config=genai.GenerationConfig(
            max_output_tokens=1000,
            temperature=1.5,
        )

    )

    return response.text






def gemini_decision_agent(prompt):
    model = genai.GenerativeModel("gemini-2.5-flash",

        system_instruction=f"""

        Role & Purpose

        You are ReInsure Strategist AI, a decision-making, advisory, and policy strategy assistant for the reinsurance industry.
        Your role is to act as a virtual underwriter, strategist, and advisor supporting reinsurers, insurers (cedants), and brokers in analyzing facultative reinsurance placements.

        You must:

        Interpret and reason strictly from verified reinsurance documentation and data (e.g., Facultative Working Sheet, Appendix 1/2, actuarial references, catastrophe models).

        Provide clear, structured, and actionable recommendations.

        Maintain accuracy, compliance, and professional underwriting standards.

        Avoid speculation; if information is missing, state clearly what else is needed.

        🧩 Responsibilities

        Decision Making & Underwriting Support

        Evaluate cedant submissions (insured, peril, TSI, retention, PML, CAT exposure, etc.).

        Recommend acceptance/rejection of risks and propose percentage share to underwrite.

        Suggest terms, conditions, exclusions, or warranties to improve portfolio quality.

        Advisory & Strategy

        Advise on pricing, market positioning, and negotiation dynamics with brokers.

        Assess portfolio impact (diversification vs. concentration).

        Provide guidance on climate change, ESG, and regulatory compliance.

        Policy Structuring

        Recommend reinsurance structure (facultative vs. treaty, layers, deductibles).

        Evaluate whether to accept risks net of brokerage/taxes.

        Suggest suitable deductibles, retentions, and limits.

        Computation & Analysis

        Apply reinsurance formulas:

Premium Rate (% or ‰): 
(Premium÷TSI)×100 or ×1000

Premium (given rate & TSI): 
TSI×(Rate/100)

Loss Ratio: 
(Paid + Outstanding − Recoveries)÷Earned Premium × 100

Accepted Premium: Gross Premium × Accepted Share %

Accepted Liability: TSI × Accepted Share %

Always show formulas, calculations, and interpretations.

        Risk Assessment

        Evaluate catastrophe risk using reliable models (e.g., GEM, flood maps).

        Assess climate & ESG exposures (low/medium/high).

        Review technical risk survey reports (fire safety, construction quality, security).

        Highlight positive and negative factors (e.g., good housekeeping vs. weak fire systems).

        🗂 Required Information Fields

        For every case, capture and analyze the following (from the Facultative Reinsurance Working Sheet

        Insured, Cedant, Broker
        Perils Covered
        Geographical Limit & Situation of Risk/Voyage
        Occupation & Main Activities of Insured
        TSI and Breakdown
        Excess/Deductible
        Retention of Cedant (%)
        PML %
        CAT Exposure
        Period of Insurance
        Claims Experience (last 3 years)
        Share Offered %
        Risk Survey Report
        Premium Rate & Premium (original currency + KES equivalent)
        Climate Change & ESG Factors
        Technical Assessment
        Market Considerations
        Portfolio Impact
        Proposed Terms & Conditions
        Final Recommended % Share
        Remarks & Manager’s Comments

        📊 Output Style

        Your responses must be:

        Structured and professional, like a reinsurance underwriting memo.

        Include tables for numeric data (TSI, Premium, Loss Ratios, Retentions).

        Provide reasoned recommendations, not just raw data.

        Highlight uncertainties and advise what additional data is required.

        Example Output Block:

        📌 Technical Assessment:
        - Insured: ABC Manufacturing Ltd
        - Perils Covered: Fire, Explosion
        - PML: 60% of TSI → KES 300,000,000
        - Claims Experience (3 yrs): Loss Ratio = 35%

        ✅ Positive Factors: Good fire systems, diversified portfolio
        ⚠️ Negative Factors: High CAT exposure (earthquake zone)

        💡 Recommendation:
        - Accept 20% facultative share.
        - Proposed Premium: KES 25,000,000
        - Conditions: Earthquake deductible of 5%, warranty on sprinkler maintenance.

        🛑 Boundaries

        Never generate fictitious or speculative data.

        Do not provide legal or financial investment advice outside reinsurance.

        Always clarify if a response is based on provided documents vs. general knowledge.""")

    response = model.generate_content(
        prompt,
        generation_config=genai.GenerationConfig(
            max_output_tokens=1000,
            temperature=1.5,
        )

    )

    return response.text





def generate_otp(length=6):
    characters = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(characters) for _ in range(length))


def send_otp(phone_number, otp_sms):

    recipients = [f"+254{str(phone_number)}"]

    # Set your message
    message = f"{otp_sms}"

    # Set your shortCode or senderId
    sender = 20880

    try:
        response = sms.send(message, recipients, sender)

        print(response)

    except Exception as e:
        print(f'Houston, we have a problem: {e}')


def welcome_message(first_name, phone_number):

    recipients = [f"+254{str(phone_number)}"]

    # Set your message
    message = f"{first_name}, Welcome to Reinsure AI – your trusted platform for smarter claims and fraud detection."

    # Set your shortCode or senderId
    sender = 20880
 
    try:
        response = sms.send(message, recipients, sender)

        print(response)

    except Exception as e:
        print(f'Houston, we have a problem: {e}')






@csrf_exempt
def send_otp_view(request):
    if request.method == 'POST':
        phone = request.POST.get('phone')
        first_name = request.POST.get('firstName')
        last_name = request.POST.get('lastName')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirmPassword')

        if password != confirm_password:
            return JsonResponse({'error': 'Passwords do not match'}, status=400)

        otp_code = generate_otp()
        otp_storage[phone] = {
            'otp': otp_code,
            'first_name': first_name,
            'last_name': last_name,
            'email': email,
            'password': password,
        }

        welcome_message(first_name, phone)

        send_otp(phone, otp_code)

        # if get_otp_code:
        #     welcome_message(first_name, phone)

        return JsonResponse({'status': 'OTP sent', 'phone': phone})

    return JsonResponse({'error': 'Invalid request'}, status=400)





@csrf_exempt
def verify_otp_view(request):
    if request.method == 'POST':
        phone = request.POST.get('phone')
        entered_otp = request.POST.get('otp')
        first_name = request.POST.get('first_name')
        saved = otp_storage.get(phone)

        if saved and saved['otp'] == entered_otp:
            welcome_message(first_name, phone)
            messages.success(
                request, "Registration successful! Welcome to Reinsure AI.")
            return redirect('dashboard')  # or your actual home page
        else:
            messages.error(request, "Invalid OTP. Please try again.")
            return render(request, 'verify_otp.html', {'phone': phone, 'first_name': first_name})
    return redirect('registration')











def get_merged_pdf_path(user_id="user123"):
    """Helper: Returns path to merged.pdf for a given user_id"""
    return os.path.join(settings.BASE_DIR, "users_data", user_id, "attachments", "merged.pdf")


# Global storage for later use (in memory, not a file)
EXTRACTED_TEXT_STORE = {}


@csrf_exempt
def extract_text_from_pdf(request, user_id="user123"):
    """
    Extracts all text from merged.pdf in the user's attachments folder
    and stores it in a global variable for later use.
    """
    try:
        pdf_path = get_merged_pdf_path(user_id)
        if not os.path.exists(pdf_path):
            return JsonResponse({"status": "error", "message": f"Merged PDF not found at {pdf_path}"}, status=404)

        # Open and extract text
        doc = fitz.open(pdf_path)
        all_text = []
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text("text")
            if text.strip():
                all_text.append(f"\n--- Page {page_num+1} ---\n{text}")
        doc.close()

        # Save into global variable for later usage
        EXTRACTED_TEXT_STORE[user_id] = "\n".join(all_text)

        return JsonResponse({
            "status": "success",
            "message": "Text extracted and stored in memory.",
            "preview": EXTRACTED_TEXT_STORE[user_id][:3000]  # only preview first 500 chars
        })

    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


# qa_chain = None

# def get_or_build_chain():
#     global qa_chain
#     if qa_chain is None:
#         pdf_path = os.path.join("Resure_AI", "users_data", "user123", "attachments", "merged.pdf")
#         if not os.path.exists(pdf_path):
#             raise FileNotFoundError("merged.pdf not found yet")
#         qa_chain = get_qa_chain(pdf_path)
#     return qa_chain
qa_chain = EXTRACTED_TEXT_STORE.get("user123", "")



def get_pdf_path():
    return os.path.join(settings.BASE_DIR, "users_data", "user123", "attachments", "merged.pdf")

@csrf_exempt
def rag_chatbot_response(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        rag_user_message = data.get('message', '')

        if not rag_user_message:
            return JsonResponse({'response': "Sorry, I didn't catch that."}, status=400)

        pdf_path = get_pdf_path()
        if not os.path.exists(pdf_path):
            return JsonResponse({'response': f"File not found at: {pdf_path}"}, status=400)

        try:
            qa_chain = get_qa_chain(pdf_path)
            if qa_chain is None:
                return JsonResponse({'response': "System initialization failed. Check logs."}, status=500)

            bot_reply = query_system(rag_user_message, qa_chain)
            return JsonResponse({'response': bot_reply})
        except Exception as e:
            return JsonResponse({'response': f"System error: {str(e)}"}, status=500)



@csrf_exempt
def chatbot_response(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        user_message = data.get('message', '')

        if user_message:
            bot_reply = get_gemini_response(user_message)
            return JsonResponse({'response': bot_reply})
        else:
            return JsonResponse({'response': "Sorry, I didn't catch that."}, status=400)



# Extracting Files and analyzing them


# file_path = 
# user_id = "user123"
# source_dir = f"users_data/{user_id}/attachments"
# pdf_path = os.path.join(source_dir, "merged.pdf")



def extract_msg_file(file_path: str, user_id: str, output_base: str = "users_data"):
    """
    Extracts metadata and attachments from a .msg file. 

    Args:
        file_path (str): Path to the .msg file.
        user_id (str): Unique identifier for the user (used to create folder).
        output_base (str): Base folder where user data will be stored.

    Returns:
        dict: Extracted metadata (sender, recipients, subject, body, etc.)
    """
    # Ensure user-specific folder exists
    user_folder = os.path.join(output_base, user_id, "attachments")
    os.makedirs(user_folder, exist_ok=True)

    # Parse the .msg file
    msg = extract_msg.Message(file_path)

    # Build metadata dictionary
    metadata = {
        "from": msg.sender,
        "to": msg.to,
        "cc": msg.cc,
        "bcc": msg.bcc,
        "date": msg.date,
        "subject": msg.subject,
        "body_text": msg.body,
        "body_html": msg.htmlBody,
        "headers": msg.headerDict,
        "attachments": []
    }

    # Save attachments automatically
    for att in msg.attachments:
        filename = os.path.basename(att.longFilename or att.shortFilename or "attachment")
        save_path = os.path.join(user_folder, filename)
        att.save(customPath=user_folder)  # saves into the folder
        metadata["attachments"].append(save_path)

    # Close msg to release file lock
    msg.close()

    return metadata




import os
from docx2pdf import convert

def convert_docx_to_pdf(user_id: str, base_dir: str = "users_data"):
    """
    Loops over user's attachments folder, converts .docx files to .pdf,
    and saves them in the same folder.

    Args:
        user_id (str): User identifier (e.g., 'user123')
        base_dir (str): Base directory where user folders are stored
    """
    attach_dir = os.path.join(base_dir, user_id, "attachments")

    if not os.path.exists(attach_dir):
        raise FileNotFoundError(f"Attachment folder not found: {attach_dir}")

    for filename in os.listdir(attach_dir):
        if filename.lower().endswith(".docx"):
            docx_path = os.path.join(attach_dir, filename)
            pdf_path = os.path.splitext(docx_path)[0] + ".pdf"

            try:
                convert(docx_path, pdf_path)
                print(f"✅ Converted: {filename} → {os.path.basename(pdf_path)}")
            except Exception as e:
                print(f"⚠️ Failed to convert {filename}: {e}")



import os
from PyPDF2 import PdfMerger

def merge_pdfs(user_id: str, base_dir: str = "users_data", output_name: str = "merged.pdf"):
    """
    Merges all PDF files in a user's attachment folder into one PDF.

    Args:
        user_id (str): User identifier (e.g., 'user123')
        base_dir (str): Base directory where user folders are stored
        output_name (str): Name of the merged PDF file

    Returns:
        str: Path to the merged PDF file
    """
    attach_dir = os.path.join(base_dir, user_id, "attachments")

    if not os.path.exists(attach_dir):
        raise FileNotFoundError(f"Attachment folder not found: {attach_dir}")

    # Find all PDFs in the folder
    pdf_files = [f for f in os.listdir(attach_dir) if f.lower().endswith(".pdf")]

    if not pdf_files:
        raise FileNotFoundError(f"No PDF files found in {attach_dir}")

    pdf_files.sort()  # Optional: merge in alphabetical order

    merger = PdfMerger()

    try:
        for pdf in pdf_files:
            merger.append(os.path.join(attach_dir, pdf))

        output_path = os.path.join(attach_dir, output_name)
        merger.write(output_path)
        merger.close()

        print(f"✅ Merged {len(pdf_files)} PDFs into: {output_path}")
        return output_path

    except Exception as e:
        print(f"⚠️ Failed to merge PDFs: {e}")
        return None





def extract_images_only(user_id: str, base_dir: str = "users_data", merged_file: str = "merged.pdf"):
    attach_dir = os.path.join(base_dir, user_id, "attachments")
    pdf_path = os.path.join(attach_dir, merged_file)

    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"Merged PDF not found: {pdf_path}")

    results = {"images": []}
    doc = fitz.open(pdf_path)

    for page_num in range(len(doc)):
        for img_index, img in enumerate(doc.get_page_images(page_num), start=1):
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            ext = base_image["ext"]

            pil_img = Image.open(io.BytesIO(image_bytes))
            w, h = pil_img.size
            if w < 100 or h < 100:
                continue

            img_name = f"extracted_page{page_num+1}_{img_index}.{ext}"
            img_path = os.path.join(attach_dir, img_name)
            pil_img.save(img_path)

            # Convert path to URL
            img_url = f"users_data/{user_id}/attachments/{img_name}"
            results["images"].append(img_url)

    doc.close()
    return results







# ==============================================================================
# ==============================================================================




# @csrf_exempt
# def upload_msg(request):
#     try:
#         if request.method == "POST" and request.FILES.get("file"):
#             uploaded_file = request.FILES["file"]

#             # Generate user_id (or use logged-in user)
#             user_id = request.POST.get("user_id", str(uuid.uuid4()))

#             # Save uploaded file
#             user_dir = os.path.join("users_data", user_id)
#             os.makedirs(user_dir, exist_ok=True)

#             file_path = os.path.join(user_dir, uploaded_file.name)
#             with open(file_path, "wb+") as dest:
#                 for chunk in uploaded_file.chunks():
#                     dest.write(chunk)

#             # Process file
#             metadata = extract_msg_file(file_path, user_id)
  
#             return JsonResponse({
#                 "status": "success",
#                 "user_id": user_id,
#                 "metadata": metadata,
#             }, safe=False, json_dumps_params={"default": lambda x: x.decode() if isinstance(x, bytes) else str(x)})


#         return JsonResponse({"status": "error", "message": "No file uploaded"}, status=400)

#     except Exception as e:
#         # Catch any crash and return as JSON
#         return JsonResponse({"status": "error", "message": str(e)}, status=500)


@csrf_exempt
def upload_msg(request):
    if request.method == "POST":
        user_id = request.POST.get("user_id", "user123")
        uploaded_file = request.FILES.get("file")

        if not uploaded_file:
            return JsonResponse({"status": "error", "message": "No file uploaded"})

        # Save uploaded .msg to user's folder
        base_dir = "users_data"
        user_dir = os.path.join(base_dir, user_id)
        os.makedirs(user_dir, exist_ok=True)

        file_path = os.path.join(user_dir, uploaded_file.name)
        with open(file_path, "wb+") as f:
            for chunk in uploaded_file.chunks():
                f.write(chunk)

        # Extract .msg attachments
        try:
            metadata = extract_msg_file(file_path, user_id)
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)})

        # Convert any .docx to .pdf inside attachments
        try:
            convert_docx_to_pdf(user_id, base_dir=base_dir)
        except Exception as e:
            print(f"⚠️ Docx→PDF conversion failed: {e}")

        return JsonResponse({
            "status": "success",
            "user_id": user_id,
            "metadata": metadata,
        }, safe=False, json_dumps_params={"default": lambda x: x.decode() if isinstance(x, bytes) else str(x)})


    return JsonResponse({"status": "error", "message": "Invalid request"})



import os
from docx2pdf import convert

def convert_docx_to_pdf(user_id: str, base_dir: str = "users_data"):
    """
    Loops over user's attachments folder, converts .docx files to .pdf,
    and saves them in the same folder.

    Args:
        user_id (str): User identifier (e.g., 'user123')
        base_dir (str): Base directory where user folders are stored
    """
    attach_dir = os.path.join(base_dir, user_id, "attachments")

    if not os.path.exists(attach_dir):
        raise FileNotFoundError(f"Attachment folder not found: {attach_dir}")

    for filename in os.listdir(attach_dir):
        if filename.lower().endswith(".docx"):
            docx_path = os.path.join(attach_dir, filename)
            pdf_path = os.path.splitext(docx_path)[0] + ".pdf"

            try:
                convert(docx_path, pdf_path)
                print(f"✅ Converted: {filename} → {os.path.basename(pdf_path)}")
            except Exception as e:
                print(f"⚠️ Failed to convert {filename}: {e}")




import os
from PyPDF2 import PdfMerger

def merge_pdfs(user_id: str, base_dir: str = "users_data", output_name: str = "merged.pdf"):
    """
    Merges all PDF files in a user's attachment folder into one PDF.

    Args:
        user_id (str): User identifier (e.g., 'user123')
        base_dir (str): Base directory where user folders are stored
        output_name (str): Name of the merged PDF file

    Returns:
        str: Path to the merged PDF file
    """
    attach_dir = os.path.join(base_dir, user_id, "attachments")

    if not os.path.exists(attach_dir):
        raise FileNotFoundError(f"Attachment folder not found: {attach_dir}")

    # Find all PDFs in the folder
    pdf_files = [f for f in os.listdir(attach_dir) if f.lower().endswith(".pdf")]

    if not pdf_files:
        raise FileNotFoundError(f"No PDF files found in {attach_dir}")

    pdf_files.sort()  # Optional: merge in alphabetical order

    merger = PdfMerger()

    try:
        for pdf in pdf_files:
            merger.append(os.path.join(attach_dir, pdf))

        output_path = os.path.join(attach_dir, output_name)
        merger.write(output_path)
        merger.close()

        print(f"✅ Merged {len(pdf_files)} PDFs into: {output_path}")
        return output_path

    except Exception as e:
        print(f"⚠️ Failed to merge PDFs: {e}")
        return None




from django.http import JsonResponse, FileResponse

@csrf_exempt
def merge_user_pdfs(request):
    """
    API to merge all PDFs in a user's attachments folder into one PDF.
    """
    if request.method == "POST":
        user_id = request.POST.get("user_id", "user123")

        try:
            merged_path = merge_pdfs(user_id)

            if merged_path:
                return JsonResponse({
                    "status": "success",
                    "message": "PDFs merged successfully",
                    "file_url": f"/download_attachment/?user_id={user_id}&file={os.path.basename(merged_path)}"
                })
            else:
                return JsonResponse({"status": "error", "message": "Merging failed"})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=500)

    return JsonResponse({"status": "error", "message": "Invalid request"}, status=400)





# ===============================================================================
# ==============================================================================




def generate_pdf_report(agent_output: str, user_id="user123", base_dir="users_data"):
    """
    Generate a structured PDF report from model's output string.
    """
    user_dir = os.path.join(base_dir, user_id)
    os.makedirs(user_dir, exist_ok=True)

    pdf_path = os.path.join(user_dir, "report.pdf")

    doc = SimpleDocTemplate(pdf_path, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    # Title
    title_style = styles['Heading1']
    title_style.alignment = 1
    story.append(Paragraph("📑 Reinsurance AI Report", title_style))
    story.append(Spacer(1, 20))

    # Subtitle
    subtitle_style = styles['Heading2']
    story.append(Paragraph("Generated by ReInsure Strategist AI", subtitle_style))
    story.append(Spacer(1, 20))

    # Body
    body_style = ParagraphStyle(
        "Body",
        parent=styles['Normal'],
        fontSize=11,
        leading=16,
        spaceAfter=12
    )

    for para in agent_output.split("\n"):
        if para.strip():
            story.append(Paragraph(para.strip(), body_style))

    doc.build(story)
    return pdf_path


@csrf_exempt
def generate_report_view(request):
    """
    API endpoint to trigger PDF generation.
    """
    if request.method == "POST":
        user_id = request.POST.get("user_id", "user123")

        try:
            # 1. Extract text from PDF
            extracted_text = extract_text_from_pdf(user_id)

            # 2. Call the decision agent with extracted text
            agent_output = gemini_decision_agent(extracted_text)

            if not agent_output:
                return JsonResponse({"status": "error", "message": "No output from model"}, status=500)

            # 3. Generate PDF
            pdf_path = generate_pdf_report(agent_output, user_id=user_id)

            return JsonResponse({
                "status": "success",
                "pdf_url": f"/users_data/{user_id}/generated_report.pdf"
            })
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=500)

    return JsonResponse({"status": "error", "message": "Invalid request"}, status=400)









@csrf_exempt
def convert_attachments_to_pdf(request):
    if request.method == "POST":
        user_id = request.POST.get("user_id", "user123")

        try:
            convert_docx_to_pdf(user_id, base_dir="users_data")
            return JsonResponse({"status": "success", "message": "All DOCX files converted to PDF."}, safe=False, json_dumps_params={"default": lambda x: x.decode() if isinstance(x, bytes) else str(x)})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, safe=False, json_dumps_params={"default": lambda x: x.decode() if isinstance(x, bytes) else str(x)})

    return JsonResponse({"status": "error", "message": "Invalid request"})




import os
from django.http import JsonResponse

def list_attachments(request):
    user_id = request.GET.get("user_id", "user123")
    attach_dir = os.path.join("users_data", user_id, "attachments")

    if not os.path.exists(attach_dir):
        return JsonResponse({"status": "error", "message": "No attachment folder"})

    files_data = []
    for f in os.listdir(attach_dir):
        path = os.path.join(attach_dir, f)
        if os.path.isfile(path):
            size_kb = os.path.getsize(path) / 1024
            ext = f.split(".")[-1].lower()
            files_data.append({
                "name": f,
                "ext": ext,
                "size": f"{size_kb:.1f} KB",
                "url": f"/download_attachment/?user_id={user_id}&file={f}"
            })

    if not files_data:
        return JsonResponse({"status": "error", "message": "No files found"})

    return JsonResponse({"status": "success", "files": files_data})





from django.http import FileResponse

def download_attachment(request):
    user_id = request.GET.get("user_id", "user123")
    filename = request.GET.get("file")
    file_path = os.path.join("users_data", user_id, "attachments", filename)

    if not os.path.exists(file_path):
        return JsonResponse({"status": "error", "message": "File not found"}, status=404)

    return FileResponse(open(file_path, "rb"), as_attachment=True, filename=filename)





@csrf_exempt
def extract_images_view(request):
    if request.method == "POST":
        user_id = request.POST.get("user_id", "user123")
        print(f"Extracting images for user_id={user_id}")  # Debug log

        try:
            results = extract_images_only(user_id=user_id)
            print(f"Extracted images: {results['images']}")

            # Convert file system paths -> URLs
            image_urls = []
            for path in results["images"]:
                rel_path = os.path.relpath(path, settings.MEDIA_ROOT)
                url = settings.MEDIA_URL + rel_path.replace("\\", "/")
                image_urls.append(url)

            return JsonResponse({"status": "success", "images": image_urls})
        except Exception as e:
            print(f"Error extracting images: {e}")
            return JsonResponse({"status": "error", "message": str(e)})

    return JsonResponse({"status": "error", "message": "Invalid request"})







# Create your views here.
def home(request):
    return render(request, "index.html")


def registration(request):
    return render(request, "registration.html")


def login(request):
    return render(request, "login2.html")


def dashboard(request):
    return render(request, "dashboard.html")


def message_analysis(request):
    return render(request, "message-analysis.html")


def claims(request):
    return render(request, "claims.html")


def fraud(request):
    return render(request, "fraud.html")


def map(request):
    return render(request, "map.html")