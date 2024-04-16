from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

from django.contrib.auth import views as auth_views

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('queue-history', views.q_history, name="q_history"),

    path('station-list/', views.station_list, name="station_list"),
    path('station/station-history/<int:pk>/', views.station_history, name="station_history"),
    path('create-station-and-route/', views.create_station_and_route, name="create_station_and_route"),
    path('edit_station/<int:station_id>/', views.edit_station, name='edit_station'),
    path('delete_station/<int:station_id>/', views.delete_station, name='delete_station'),


    path('drivers/', views.drivers2, name="drivers"),

    path('register-driver/', views.add_driver, name='add_driver'),
    path('edit_driver/', views.edit_driver, name='edit_driver'),
    path('delete_driver/<int:driver_id>/', views.delete_driver, name='delete_driver'),
    path('', views.home, name='home'),

    path('login/', views.login_page, name='login'),
        
    path('admin/', views.admin_login, name='admin_login'),
    path('', views.register_page, name='register'),
    path('logout/', views.logout_user, name='logout'),


   # path('station/', views.station, name="station"),
    path('station/<int:station_id>/', views.station, name='station_page'),

    path('driver-display-page/', views.driver_display_page, name='driver_display_page'),
    path('display-page/', views.display_page, name="display_page"),
    path('process-next-queue/<int:station_id>/', views.process_next_queue, name='process_next_queue'),

    path('update-queue-status/<str:token_number>/', views.update_queue_status, name='update_queue_status'),





   # path('drivers/', views.drivers, name='drivers2'),
   # path('add-driver/', views.register_driver, name='add-driver'),
    path('driver_info/<int:driver_id>/', views.driver_info, name='driver_info'),

    path('add_to_queue/<int:driver_id>/', views.add_to_queue, name='add_to_queue'),

    path('q/', views.q_page, name='q_page'),


    path('users/', views.users_page, name='users_page'),
    path('create-user-account/', views.create_user_account, name='create_user_account'),

    path('reset-password/', auth_views.PasswordResetView.as_view(template_name="base/authentication/reset_password.html"), name="reset_password"),
    path('reset-password-sent/', auth_views.PasswordResetDoneView.as_view(template_name='base/authentication/reset_password_sent.html'), name="password_reset_done"),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='base/authentication/reset_password_form.html'), name="password_reset_confirm"),
    path('reset-password-complete/', auth_views.PasswordResetCompleteView.as_view(template_name='base/authentication/reset_password_done.html'), name="password_reset_complete"),


]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)