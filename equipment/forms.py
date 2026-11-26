from django import forms
from django.utils.datastructures import MultiValueDict

from .models import Equipment
from .services import EQUIPMENT_EDIT_FIELDS


class EquipmentCreateForm(forms.Form):
    number = Equipment._meta.get_field("number").formfield()
    name = Equipment._meta.get_field("name").formfield()
    category = Equipment._meta.get_field("category").formfield()
    location = Equipment._meta.get_field("location").formfield()
    description = Equipment._meta.get_field("description").formfield()


class EquipmentEditForm(forms.Form):
    name = Equipment._meta.get_field("name").formfield(label="名称")
    category = Equipment._meta.get_field("category").formfield(label="类别")
    location = Equipment._meta.get_field("location").formfield(label="位置")
    description = Equipment._meta.get_field("description").formfield(label="说明", strip=False)

    def clean(self):
        cleaned = super().clean()
        submitted = self.data.keys() | self.files.keys()
        errors = []
        if "number" in submitted:
            errors.append("设备编号不可修改。")
        if "status" in submitted:
            errors.append("设备状态不可在此修改。")
        if submitted - {*EQUIPMENT_EDIT_FIELDS, "csrfmiddlewaretoken", "number", "status"} or self.files:
            errors.append("提交包含不允许的字段。")
        if isinstance(self.data, MultiValueDict) and any(len(values) != 1 for _, values in self.data.lists()):
            errors.append("提交包含重复字段。")
        if "description" not in submitted:
            errors.append("请提交说明字段，内容可留空。")
        if errors:
            raise forms.ValidationError(errors)
        return cleaned
