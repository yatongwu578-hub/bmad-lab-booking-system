from django.urls import path

from .views import create_equipment_view, edit_equipment_view, equipment_catalog, equipment_detail


urlpatterns = [
    path("equipment/", equipment_catalog, name="equipment-catalog"),
    path("equipment/new/", create_equipment_view, name="equipment-create"),
    path("equipment/<int:pk>/", equipment_detail, name="equipment-detail"),
    path("equipment/<int:pk>/edit/", edit_equipment_view, name="equipment-edit"),
]
