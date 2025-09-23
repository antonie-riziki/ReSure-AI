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

load_dotenv()

sys.path.insert(1, './Resure_app')

# from rag_model import get_qa_chain, query_system
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


# Create your views here.
def home(request):
    return render(request, "index.html")


def registration(request):
    return render(request, "registration.html")


def login(request):
    return render(request, "login2.html")


def dashboard(request):
    return render(request, "dashboard.html")


def claims(request):
    return render(request, "claims.html")


def fraud(request):
    return render(request, "fraud.html")


def map(request):
    return render(request, "map.html")