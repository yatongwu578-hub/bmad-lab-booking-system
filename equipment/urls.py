from django.urls import path

from .views import create_equipment_view


urlpatterns = [
    path("equipment/new/", create_equipment_view, name="equipment-create"),
]
