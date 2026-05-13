from django.urls import path
from . import views

urlpatterns = [
    path('',                            views.mood_input,    name='mood_input'),
    path('register/',                   views.register_view, name='register'),
    path('login/',                      views.login_view,    name='login'),
    path('logout/',                     views.logout_view,   name='logout'),
    path('verify/<str:token>/',         views.verify_email,  name='verify_email'),
    path('results/<int:session_id>/',   views.results,       name='results'),
    path('history/',                    views.history,       name='history'),
]
