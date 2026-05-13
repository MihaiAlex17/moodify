from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from mood.views import CustomPasswordResetConfirmView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('mood.urls')),

    # ── Password reset flow (Django built-in) ──────────────────────────────
    path('password-reset/',
         auth_views.PasswordResetView.as_view(
             template_name='mood/password_reset.html',
             email_template_name='mood/email/password_reset_email.txt',
             subject_template_name='mood/email/password_reset_subject.txt',
         ),
         name='password_reset'),

    path('password-reset/done/',
         auth_views.PasswordResetDoneView.as_view(
             template_name='mood/password_reset_done.html',
         ),
         name='password_reset_done'),

    path('password-reset-confirm/<uidb64>/<token>/',
         CustomPasswordResetConfirmView.as_view(),
         name='password_reset_confirm'),
]
