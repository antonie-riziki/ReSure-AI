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

    path("dashboard/", views.dashboard, name="dashboard"),
    path("claims/", views.claims, name="claims"),
    path("fraud/", views.fraud, name="fraud"),
    path("map/", views.map, name="map"), 
]  