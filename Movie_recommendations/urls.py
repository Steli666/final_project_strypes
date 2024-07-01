from django.contrib import admin
from django.urls import path, include

from Movie_recommendations.views import UserRegister, UserLogin, UserLogout

urlpatterns = [
    # path('api/', include('Movie_recommendations.urls', name='Apis')),
    path('register', UserRegister.as_view(), name='register'),
    path('login', UserLogin.as_view(), name='login'),
    path('logout', UserLogout.as_view(), name='logout'),
]