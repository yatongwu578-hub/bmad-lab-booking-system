from django import forms

from .models import Equipment


class EquipmentCreateForm(forms.Form):
    number = Equipment._meta.get_field("number").formfield()
    name = Equipment._meta.get_field("name").formfield()
    category = Equipment._meta.get_field("category").formfield()
    location = Equipment._meta.get_field("location").formfield()
    description = Equipment._meta.get_field("description").formfield()
