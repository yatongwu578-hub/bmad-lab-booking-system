import re
from datetime import date

from django import forms
from django.utils.datastructures import MultiValueDict

from equipment.models import Equipment


class ReservationForm(forms.Form):
    start_at = forms.CharField(label="开始时间（北京时间）", widget=forms.DateTimeInput(attrs={"type": "datetime-local", "step": "any"}))
    end_at = forms.CharField(label="结束时间（北京时间）", widget=forms.DateTimeInput(attrs={"type": "datetime-local", "step": "any"}))


class OccupancyDateForm(forms.Form):
    date = forms.CharField(
        label="查询日期（北京时间）",
        strip=False,
        required=True,
        widget=forms.DateInput(attrs={"type": "date"}),
        error_messages={"required": "请选择查询日期（北京时间）。"},
    )

    def clean_date(self):
        value = self.cleaned_data["date"]
        if re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
            try:
                day = date.fromisoformat(value)
            except ValueError:
                pass
            else:
                # Both Beijing midnights must be representable in UTC and Python.
                if date.min < day < date.max:
                    return day
        raise forms.ValidationError("请输入有效日期，格式为 YYYY-MM-DD。")


class AdminReservationFilterForm(forms.Form):
    equipment = Equipment._meta.get_field("number").formfield(
        label="设备编号", required=False, widget=forms.TextInput,
    )

    def clean(self):
        cleaned = super().clean()
        if self.data.keys() - {"equipment"}:
            raise forms.ValidationError("查询包含不允许的参数。")
        if "equipment" in self.data:
            if isinstance(self.data, MultiValueDict) and len(self.data.getlist("equipment")) != 1:
                raise forms.ValidationError("设备编号只能提供一次。")
            if "equipment" in cleaned and not cleaned["equipment"]:
                self.add_error("equipment", "请输入设备编号，或清除筛选查看全部预约。")
        else:
            cleaned["equipment"] = None
        return cleaned
