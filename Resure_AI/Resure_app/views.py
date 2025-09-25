# from .forms import PayslipForm
from .models import *
from uuid import UUID
from django.core.files.storage import FileSystemStorage
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
import africastalking
import os
import sys
import secrets
import string
import json
import shutil
import tempfile
import google.generativeai as genai
from dotenv import load_dotenv
import os
import extract_msg
import shutil
import uuid
from datetime import datetime

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


# Custom modules


def get_gemini_response(prompt):
    model = genai.GenerativeModel("gemini-2.0-flash",

        system_instruction=f"""

        You are ElevateHR — a helpful, professional, and smart HR assistant. 
        You support employees, managers, and HR staff with information on recruitment, onboarding, employee wellness, leave policies, performance management, and workplace culture.

        Guidelines:
        - Use a warm, clear, and professional tone.
        - Keep answers short and relevant (2–4 sentences max).
        - If unsure or a question is out of scope, recommend contacting HR directly.
        - Avoid making assumptions about company-specific policies unless provided.
        - Be friendly but not too casual. Respectful and informative.

        Example Output:
        - "Hi there! You can apply for leave through the Employee Portal under 'My Requests'. Need help navigating it?"
        - "Sure! During onboarding, you’ll get access to all core HR systems and meet your assigned buddy."
        
        Donts:
        - Don't provide personal opinions or unverified information.
        - Don't discuss sensitive topics like salary negotiations or personal grievances.
        - Don't use jargon or overly technical language.
        - Don't make assumptions about the user's knowledge or experience level.
        - Don't provide legal or financial advice.
        - Don't engage in casual conversation unrelated to HR, Employee, Managerial, Employer or Work Environment topics.
        
        """)

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









# ===============================================================================
# ==============================================================================




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