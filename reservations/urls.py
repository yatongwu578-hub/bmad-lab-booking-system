from django.urls import path

from .views import equipment_occupancy, reservation_result, reserve_equipment


urlpatterns = [
    path("equipment/<int:pk>/reserve/", reserve_equipment, name="reservation-submit"),
    path("equipment/<int:pk>/occupancy/", equipment_occupancy, name="equipment-occupancy"),
    path("reservations/<int:pk>/result/", reservation_result, name="reservation-result"),
]
