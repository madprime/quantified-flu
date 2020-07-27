from collections import OrderedDict

from django import forms
from django.core.exceptions import ValidationError

from .models import (
    SYMPTOM_INTENSITY_CHOICES,
    Symptom,
    SymptomReport,
    SymptomReportSymptomItem,
)


class SymptomReportForm(forms.ModelForm):
    other_symptoms = forms.CharField(widget=forms.TextInput(), required=False)
    suspected_virus = forms.CharField(widget=forms.TextInput(), required=False)

    class Meta:
        model = SymptomReport
        fields = ["other_symptoms", "fever_guess", "fever", "suspected_virus", "notes"]

    def __init__(self, *args, **kwargs):
        """
        Add fields to the form for each potential symptom.

        This reorders to place the symptom list first, as provided by ReportSetup.
        The value is initialized to 0 if none is provided.
        """
        self.account = kwargs.pop("account")
        returned = super().__init__(*args, **kwargs)
        new_fields = OrderedDict()
        for symptom_item in self.account.report_setup.get_symptom_items():
            symptom_label = symptom_item.symptom.label
            if symptom_label not in self.initial:
                self.initial[symptom_label] = 0
            new_fields[symptom_label] = forms.IntegerField(
                required=False,
                min_value=min([x[0] for x in SYMPTOM_INTENSITY_CHOICES]),
                max_value=max([x[0] for x in SYMPTOM_INTENSITY_CHOICES]),
            )
        new_fields.update(self.fields)
        self.fields = new_fields
        return returned

    def save(self):
        """
        Add saving for the symptom fields to SymptomReportSymptomItem.

        Creates a Symptom and SymptomReportSymptomItem objects if not already present.
        """
        new_report = super().save()
        for symptom_item in self.account.report_setup.get_symptom_items():
            symptom_label = symptom_item.symptom.label
            value = self.cleaned_data[symptom_label]
            symptom_item, _ = SymptomReportSymptomItem.objects.get_or_create(
                report=new_report, symptom=symptom_item.symptom
            )
            symptom_item.intensity = value
            symptom_item.save()
        return new_report


"""
TODO: Implement reporting of diagnostic testing.
class DiagnosisReportForm(forms.ModelForm):
    diagnoses = forms.MultipleChoiceField(
        required=False, widget=forms.CheckboxSelectMultiple(), choices=DIAGNOSIS_CHOICES
    )

    class Meta:
        model = DiagnosisReport
        fields = ["date_tested", "diagnosis", "notes"]
"""
