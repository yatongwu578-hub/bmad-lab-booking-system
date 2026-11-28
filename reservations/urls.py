from django.urls import path

from .views import (
    admin_reservation_detail,
    admin_reservation_list,
    equipment_occupancy,
    reservation_cancel,
    reservation_list,
    reservation_result,
    reserve_equipment,
)


urlpatterns = [
    path("equipment/<int:pk>/reserve/", reserve_equipment, name="reservation-submit"),
    path("equipment/<int:pk>/occupancy/", equipment_occupancy, name="equipment-occupancy"),
    path("reservations/", reservation_list, name="reservation-list"),
    path("reservations/manage/", admin_reservation_list, name="admin-reservation-list"),
    path("reservations/manage/<int:pk>/", admin_reservation_detail, name="admin-reservation-detail"),
    path("reservations/<int:pk>/result/", reservation_result, name="reservation-result"),
    path("reservations/<int:pk>/cancel/", reservation_cancel, name="reservation-cancel"),
]
