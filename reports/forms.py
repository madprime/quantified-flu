from collections import OrderedDict

from django import forms
from django.core.exceptions import ValidationError

from quantified_flu.models import Account

from .models import (
    ReportSetup,
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


class SelectReportSetupForm(forms.ModelForm):
    class Meta:
        model = Account
        fields = ["report_setup"]
        widgets = {"report_setup": forms.RadioSelect}

    def __init__(self, *args, **kwargs):
        self.account = kwargs.pop("account")
        super().__init__(*args, **kwargs)
        self.fields["report_setup"].queryset = ReportSetup.get_available(
            account=self.account
        )


class ReportSetupForm(forms.ModelForm):
    class Meta:
        model = ReportSetup
        fields = ["title", "description", "category_ordering"]

    def __init__(self, *args, **kwargs):
        """
        Add custom fields for selecting category ordering.
        """
        super().__init__(*args, **kwargs)
        categories = self.instance.get_categories()
        for i in range(categories.count()):
            field_name = "select_ordering_{}".format(i)
            self.fields[field_name] = forms.ModelChoiceField(categories, required=False)

    def clean(self):
        """
        Use custom fields to create category ordering field.
        """
        super().clean()
        cat_order_keys = sorted(
            [x for x in self.cleaned_data.keys() if x.startswith("select_ordering_")],
            key=lambda k: int(k.split("_")[-1]),
        )
        # If this part of the form was skipped, retain the current category_ordering.
        if not any([self.cleaned_data[key] for key in cat_order_keys]):
            self.cleaned_data["category_ordering"] = self.instance.category_ordering
            return
        cat_order_list = []
        for key in cat_order_keys:
            if self.cleaned_data[key].id not in cat_order_list:
                cat_order_list.append(self.cleaned_data[key].id)
            else:
                msg = (
                    'The category "{}"'.format(self.cleaned_data[key].name)
                    + " is entered more than once in the category ordering!"
                )
                raise ValidationError(msg)
        self.cleaned_data["category_ordering"] = ",".join(
            [str(x) for x in cat_order_list]
        )


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
