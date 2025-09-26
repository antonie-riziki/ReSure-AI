from django.urls import path, include
from . import views
# from django.contrib.auth.views import LoginView,LogoutView
from django.conf import settings
from django.conf.urls.static import static


from django.http import JsonResponse

# def chrome_devtools_placeholder(request):
#     return JsonResponse({}, safe=False)


urlpatterns = [
    path('', views.home, name='home'),
    path('registration', views.registration, name='registration'),
    path('login/', views.login, name='login'),
    path('send-otp/', views.send_otp_view, name='send_otp'),
    # path('welcome-message/', views.welcome_message_view, name='welcome_message'),
    path('verify-otp/', views.verify_otp_view, name='verify_otp'),
    path('login/', views.login, name='login'),
    path('chatbot-response/', views.chatbot_response, name='chatbot_response'),
    path('rag-chatbot-response/', views.rag_chatbot_response, name='rag-chatbot_response'),

    path("dashboard/", views.dashboard, name="dashboard"),
    path("message-analysis/", views.message_analysis, name="message-analysis"),
    path("claims/", views.claims, name="claims"),
    path("fraud/", views.fraud, name="fraud"),
    path("map/", views.map, name="map"), 

    path("upload_msg/", views.upload_msg, name="upload_msg"),
    path("convert_attachments_to_pdf/", views.convert_attachments_to_pdf, name="convert_attachments_to_pdf"),
    path("list_attachments/", views.list_attachments, name="list_attachments"),
    path("download_attachment/", views.download_attachment, name="download_attachment"),
    path("merge_user_pdfs/", views.merge_user_pdfs, name="merge_user_pdfs"),
    path("extract_images/", views.extract_images_view, name="extract_images"),


]  

