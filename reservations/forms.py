from django import forms


class ReservationForm(forms.Form):
    start_at = forms.CharField(label="开始时间（北京时间）", widget=forms.DateTimeInput(attrs={"type": "datetime-local", "step": "any"}))
    end_at = forms.CharField(label="结束时间（北京时间）", widget=forms.DateTimeInput(attrs={"type": "datetime-local", "step": "any"}))
