from collections import OrderedDict

import datetime
import json
import secrets

from django.core.exceptions import ValidationError
from django.core.validators import validate_comma_separated_integer_list
from django.db import models
from django.db.models import Count, F, Q
from django.forms.widgets import CheckboxSelectMultiple
from django.utils.timezone import now

from openhumans.models import OpenHumansMember


SYMPTOM_INTENSITY_CHOICES = [
    (0, "None"),
    (1, "A little"),
    (2, "Somewhat"),
    (3, "Quite a bit"),
    (4, "Very much"),
]

FEVER_CHOICES = [
    ("none", "No fever"),
    ("low", "Maybe feverish"),
    ("moderate", "Feverish"),
    ("high", "High fever"),
]

"""
# TODO: Implement reporting of diagnostic testing.
VIRUS_CHOICES = [
    ("maybe_coronavirus", "suspect Coronavirus"),
    ("coronavirus", "Coronavirus, confirmed by test"),
    ("maybe_influenza", "suspect Influenza"),
    ("influenza", "Influenza, confirmed by test"),
    ("cold", "Common cold"),
]
"""


def create_token():
    return secrets.token_urlsafe(16)


TOKEN_EXPIRATION_MINUTES = 1440  # default expiration is one day


class ReportToken(models.Model):
    member = models.ForeignKey(OpenHumansMember, on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True)
    token = models.TextField(default=create_token)
    minutes_valid = models.IntegerField(default=TOKEN_EXPIRATION_MINUTES)

    def is_valid(self):
        expires = self.created + datetime.timedelta(minutes=self.minutes_valid)
        if expires > now():
            return True
        return False

    def valid_member(self):
        if self.is_valid():
            return self.member
        return None


class SymptomCategory(models.Model):
    name = models.CharField(max_length=20, unique=True)

    def __str__(self):
        return self.name

    def __unicode__(self):
        return self.name


class Symptom(models.Model):
    """
    Symptoms have "universal" meanings that are expected to remain stable.

    Each Symptom may optionally belong to a SymptomCategory.

    A Symptom marked as "standard" is made available to all users.
    """

    label = models.CharField(max_length=20, unique=True)
    verbose = models.CharField(max_length=40, blank=True)
    category = models.ForeignKey(SymptomCategory, on_delete=models.PROTECT, null=True)
    available = models.BooleanField(default=False)
    owner = models.ForeignKey(
        "quantified_flu.account", on_delete=models.SET_NULL, null=True
    )

    def __str__(self):
        return self.label

    def __unicode__(self):
        return self.label

    def save(self, *args, **kwargs):
        if not self.verbose:
            self.verbose = self.label
        super().save(*args, **kwargs)


class ReportDisplayMixin(object):
    """
    Structure report symptoms and categories for display purposes.
    """

    @staticmethod
    def order_by_symptoms(symptomitem_queryset):
        return (
            symptomitem_queryset.annotate(verbose=F("symptom__verbose"))
            .extra(select={"ci_verbose": "lower(verbose)"})
            .order_by("ci_verbose")
        )

    @staticmethod
    def sort_category_items(categoryitem_queryset, category_ordering):
        ordering = [int(i) for i in category_ordering.split(",") if i]
        categories = OrderedDict(
            [(c.id, c) for c in categoryitem_queryset.order_by("name")]
        )
        sorted_categories = []
        for item in ordering:
            try:
                sorted_categories.append(categories.pop(item))
            except KeyError:
                continue
        for key in categories.keys():
            sorted_categories.append(categories[key])
        return sorted_categories

    @property
    def display_format(self):
        return self.get_display_format()

    def get_display_format(self):
        formatted = []
        symptom_items = self.get_symptom_items()
        sorted_categories = self.sort_category_items(
            categoryitem_queryset=self.get_categories(),
            category_ordering=self.category_ordering,
        )

        for category in sorted_categories:
            formatted.append(
                {
                    "category": category,
                    "symptoms": self.order_by_symptoms(
                        symptom_items.filter(symptom__category=category)
                    ),
                }
            )

        formatted.append(
            {
                "category": None,
                "symptoms": self.order_by_symptoms(
                    symptom_items.filter(symptom__category=None)
                ),
            }
        )

        return formatted


class ReportSetup(ReportDisplayMixin, models.Model):
    """
    The template set of symptoms and categories used for symptom reporting.

    These are arranged as:
      1. a category ordering (SymptomCategory ids)
      2. a set of symptoms (ReportSetupSymptomItems)

    Symptoms may be re-used in other ReportSetups (Symptom objects).

    A symptom in the setup (ReportSetupSymptomItem) may have a category, or
    may be unassigned (e.g. displayed later as "Uncategorized symptoms").

    ReportSetups are created as soon as a user initiates customization,
    to enable associated symptomitems, but are not visible for use until
    "saved".
    """

    title = models.CharField(max_length=30, unique=True)
    category_ordering = models.TextField(
        validators=[validate_comma_separated_integer_list], blank=True
    )
    owner = models.ForeignKey(
        "quantified_flu.account", on_delete=models.SET_NULL, null=True
    )
    description = models.TextField(blank=True)
    public = models.BooleanField(default=False)

    def __str__(self):
        return "{} ({})".format(self.title, self.id)

    @classmethod
    def get_available(cls, account=None):
        """
        Return queryset containing ReportSetups available to this user.

        ReportSetups are available if they are "public", "owned" by the user,
        or already in user by the user (e.g. previously public).
        """
        if account:
            qs = cls.objects.filter(
                Q(account=account) | Q(owner=account) | Q(public=True)
            )
        else:
            qs = cls.objects.filter(public=True)
        return qs.annotate(use_count=Count("account")).order_by("-use_count")

    def get_categories(self):
        return SymptomCategory.objects.filter(
            symptom__in=Symptom.objects.filter(
                reportsetupsymptomitem__in=self.get_symptom_items()
            )
        ).distinct()

    def get_symptom_items(self):
        return self.reportsetupsymptomitem_set.all()


class ReportSetupSymptomItem(models.Model):
    report_setup = models.ForeignKey(ReportSetup, on_delete=models.CASCADE)
    symptom = models.ForeignKey(Symptom, on_delete=models.PROTECT)

    def __str__(self):
        return "{} ({})".format(self.symptom.label, self.id)


"""
# TODO: Implement reporting of diagnostic testing.
class DiagnosticTest(models.Model):

    label = models.CharField(max_length=20, choices=VIRUS_CHOICES, unique=True)
    tested = models.BooleanField(null=True, blank=True)
    available = models.BooleanField(default=False)

    def __str__(self):
        return self.label

    def __unicode__(self):
        return self.label
"""


class SymptomReport(ReportDisplayMixin, models.Model):
    member = models.ForeignKey(OpenHumansMember, on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True)
    category_ordering = models.TextField(
        validators=[validate_comma_separated_integer_list], blank=True
    )
    fever_guess = models.CharField(
        max_length=20, choices=FEVER_CHOICES, null=True, blank=True
    )
    fever = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    other_symptoms = models.TextField(blank=True, default="")
    suspected_virus = models.TextField(
        blank=True,
        default="",
        help_text="Any guess on what infection you have? (flu, cold, norovirus, coronavirus, etc.)",
    )
    notes = models.TextField(blank=True, default="")

    # Represents reports which were simple "report nothing" clicks.
    report_none = models.BooleanField(default=False)
    token = models.ForeignKey(ReportToken, null=True, on_delete=models.SET_NULL)

    def clean(self):
        """Ensure that nothing is "reported" when report_none is True."""
        if self.report_none:
            if self.fever_guess or self.fever or self.other_symptoms or self.notes:
                raise ValidationError

    @property
    def reported_symptoms(self):
        return self.symptomreportsymptomitem_set.all().exclude(intensity=0)

    def get_symptom_values(self):
        return {
            s.symptom.label: s.intensity
            for s in self.symptomreportsymptomitem_set.all()
        }

    def get_categories(self):
        return SymptomCategory.objects.filter(
            symptom__in=Symptom.objects.filter(
                symptomreportsymptomitem__in=self.get_symptom_items()
            )
        ).distinct()

    def get_symptom_items(self):
        return self.symptomreportsymptomitem_set.all()

    @property
    def severity(self):
        """Rough attempt to assess "severity" for a report, for display purposes"""
        symptom_amount = sum(
            [x.intensity for x in self.symptomreportsymptomitem_set.all()]
        )
        if self.report_none or (
            symptom_amount == 0 and (not self.fever_guess or self.fever_guess == "none")
        ):
            return 0
        if symptom_amount <= 4 and (not self.fever_guess or self.fever_guess == "none"):
            return 1
        if not self.fever_guess or self.fever_guess in ["none", "low"]:
            return 2
        if self.fever_guess == "moderate":
            return 3
        return 4

    def as_json(self):
        if isinstance(self.fever, type(None)):
            fever = ""
        else:
            fever = float(self.fever)
        data = {
            "created": self.created.isoformat(),
            "symptoms": self.get_symptom_values(),
            "other_symptoms": self.other_symptoms,
            "fever_guess": self.fever_guess,
            "fever": fever,
            "suspected_virus": self.suspected_virus,
            "notes": self.notes,
        }
        return json.dumps(data)


class SymptomReportSymptomItem(models.Model):
    """
    A specific Symptom recorded in a given report.
    """

    symptom = models.ForeignKey(Symptom, on_delete=models.PROTECT)
    report = models.ForeignKey(SymptomReport, on_delete=models.CASCADE)
    intensity = models.IntegerField(choices=SYMPTOM_INTENSITY_CHOICES, default=0)

    def __str__(self):
        return "{} ({})".format(self.symptom.label, self.id)


class SymptomReportPhysiology(models.Model):
    member = models.ForeignKey(OpenHumansMember, on_delete=models.CASCADE)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField(null=True)  # up to present if undefined
    data_source = models.TextField()
    values = models.TextField()


"""
# TODO: Implement reporting of diagnostic testing.
class DiagnosisReport(models.Model):
    member = models.ForeignKey(OpenHumansMember, on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True)
    date_tested = models.DateField()
    diagnosis = ManyToManyField(Diagnosis)
    notes = models.TextField(blank=True, default="")
"""
