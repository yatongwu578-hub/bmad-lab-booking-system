import re
from datetime import date

from django import forms


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
