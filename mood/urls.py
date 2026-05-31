from django.urls import path
from . import views

urlpatterns = [
    path('',                                    views.mood_input,          name='mood_input'),
    path('register/',                           views.register_view,       name='register'),
    path('login/',                              views.login_view,          name='login'),
    path('logout/',                             views.logout_view,         name='logout'),
    path('verify/<str:token>/',                 views.verify_email,        name='verify_email'),
    path('results/<int:session_id>/',           views.results,             name='results'),
    path('history/',                            views.history,             name='history'),
    path('profile/',                            views.profile_view,        name='profile'),
    path('feedback/<int:recommendation_id>/',   views.feedback_view,       name='feedback'),
    path('search/',                             views.search_view,         name='search'),
    path('search/suggest/',                     views.track_suggest_ajax,  name='track_suggest'),
    path('search/similar/',                     views.similar_tracks_ajax, name='similar_tracks'),
    path('preferences/',                        views.preferences_view,    name='preferences'),
    path('account/delete/',                     views.delete_account_view, name='delete_account'),
]
