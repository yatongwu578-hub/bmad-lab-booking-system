from django.urls import path

from .views import reservation_result, reserve_equipment


urlpatterns = [
    path("equipment/<int:pk>/reserve/", reserve_equipment, name="reservation-submit"),
    path("reservations/<int:pk>/result/", reservation_result, name="reservation-result"),
]
