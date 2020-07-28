import csv
import io
import json
import pytz

from django.contrib import messages
from django.contrib.auth import get_user_model, login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Count
from django.http import HttpResponse
from django.shortcuts import render, redirect, reverse
from django.urls import reverse_lazy
from django.utils.timezone import now
from django.views.generic import CreateView, ListView, RedirectView, UpdateView

from openhumans.models import OpenHumansMember

from checkin.models import CheckinSchedule
from quantified_flu.helpers import update_openhumans_reportslist
from quantified_flu.models import Account
from retrospective.tasks import add_wearable_to_symptom

from .forms import SelectReportSetupForm, SymptomReportForm
from .models import (
    SYMPTOM_INTENSITY_CHOICES,
    SymptomReport,
    ReportSetup,
    ReportToken,
)  # TODO: add DiagnosisReport


User = get_user_model()


class CheckTokenMixin:
    def dispatch(self, request, *args, **kwargs):
        """
        Redirect if user isn't logged in, or if provided token isn't valid for login.

        This also allows access if user is already logged in & no login_token is given.
        """
        self.token = None
        token_string = request.GET.get("login_token", None)
        if token_string:
            # Logout to avoid potential confusion if token is attempt to switch user.
            logout(request)
            try:
                self.token = ReportToken.objects.get(token=token_string)
                if self.token.is_valid():
                    login(request, self.token.member.user)
            except ReportToken.DoesNotExist:
                pass

        # Either token login failed or user wasn't logged in.
        if request.user.is_anonymous:
            messages.add_message(
                request,
                messages.WARNING,
                "Login or token required to submit reports. (Token may be expired, invalid, or missing.)",
            )
            return redirect("/")

        return super().dispatch(request, *args, **kwargs)


class ReportSymptomsView(CheckTokenMixin, CreateView):
    form_class = SymptomReportForm
    template_name = "reports/symptoms.html"
    success_url = reverse_lazy("reports:list")

    def get_form_kwargs(self):
        """Override to add 'account' when initializing form"""
        kwargs = super().get_form_kwargs()
        kwargs["account"] = self.request.user.openhumansmember.account
        return kwargs

    def get_categorized_symptom_choices(self):
        return (
            self.request.user.openhumansmember.account.report_setup.get_display_format()
        )

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context.update(
            {
                "form_categorized_symptom_choices": self.get_categorized_symptom_choices(),
                "form_symptom_intensity_choices": SYMPTOM_INTENSITY_CHOICES,
            }
        )
        return context

    def form_valid(self, form):
        form.instance.member = self.request.user.openhumansmember
        report = form.save()
        if self.token:
            report.token = self.token
            report.save()
        add_wearable_to_symptom.delay(report.member.oh_id)
        messages.add_message(self.request, messages.SUCCESS, "Symptom report recorded")
        update_openhumans_reportslist(self.request.user.openhumansmember)
        return super().form_valid(form)


class ReportNoSymptomsView(CheckTokenMixin, RedirectView):
    pattern_name = "reports:list"

    def get(self, request, *args, **kwargs):
        """Loading with valid token immediately creates a no-symptom report."""
        report_setup = request.user.openhumansmember.account.report_setup
        report = SymptomReport(
            report_none=True, token=self.token, member=request.user.openhumansmember
        )
        report.save()
        for symptom_item in report_setup.get_symptom_items():
            SymptomReportSymptomItem.create(report=report, symptom=symptom_item.symptom)
        add_wearable_to_symptom.delay(report.member.oh_id)
        messages.add_message(request, messages.SUCCESS, "No symptom report saved!")
        return super().get(request, *args, **kwargs)


class ReportListView(ListView):
    template_name = "reports/list.html"
    as_csv = False
    as_json = False
    member = None
    is_owner = False

    def get_list_member(self):
        if self.member:
            list_member = self.member
        else:
            list_member = self.request.user.openhumansmember
        return list_member

    def get_queryset(self):
        list_member = self.get_list_member()
        if (
            not self.request.user.is_anonymous
            and list_member == self.request.user.openhumansmember
        ):
            self.is_owner = True
        return SymptomReport.objects.filter(member=list_member).order_by("-created")

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)

        timezone = pytz.timezone("UTC")
        if self.member:
            try:
                timezone = self.member.checkinschedule.timezone
            except CheckinSchedule.DoesNotExist:
                pass
        elif not self.request.user.is_anonymous:
            try:
                timezone = self.request.user.openhumansmember.checkinschedule.timezone
            except CheckinSchedule.DoesNotExist:
                pass

        member_id = self.member.oh_id if self.member else self.member

        context.update(
            {"timezone": timezone, "member_id": member_id, "is_owner": self.is_owner}
        )

        return context

    def get_as_json(self):
        context_data = self.get_context_data()
        list_member = self.get_list_member()
        data = {
            i.data_source: json.loads(i.values)
            for i in list_member.symptomreportphysiology_set.all()
        }
        report_data = [
            json.loads(r.as_json()) for r in context_data["object_list"].reverse()
        ]
        data["symptom_report"] = []
        for report in report_data:
            timestamp = report.pop("created")
            symptoms = report.pop("symptoms")
            formatted = {"timestamp": timestamp, "data": report}
            formatted["data"].update(
                {"symptom_{}".format(x): symptoms[x] for x in symptoms}
            )
            data["symptom_report"].append(formatted)
        return json.dumps(data, sort_keys=True)

    def get_as_csv(self):
        json_data = json.loads(self.get_as_json())
        header = ["timestamp", "data_type", "key", "value"]
        with io.StringIO(newline="") as f:
            csv_out = csv.writer(f)
            csv_out.writerow(header)
            for data_type in json_data.keys():
                for entry in json_data[data_type]:
                    for key in entry["data"]:
                        csv_out.writerow(
                            [entry["timestamp"], data_type, key, entry["data"][key]]
                        )
            f.seek(0)
            return f.read()

    def get(self, request, *args, **kwargs):
        if "member_id" in self.kwargs:
            self.member = OpenHumansMember.objects.get(oh_id=self.kwargs["member_id"])
            account, _ = Account.objects.get_or_create(member=self.member)
            if not account.publish_symptom_reports:
                raise PermissionDenied
        elif self.request.user.is_anonymous:
            return redirect("/")

        default_response = super().get(request, *args, **kwargs)
        if self.as_json:
            response = HttpResponse(self.get_as_json(), content_type="application/json")
        if self.as_csv:
            response = HttpResponse(self.get_as_csv(), content_type="text/csv")
        if self.as_json or self.as_csv:
            response["Access-Control-Allow-Origin"] = "*"
            response["Access-Control-Allow-Methods"] = "GET"
            response["Access-Control-Max-Age"] = "1000"
            response["Access-Control-Allow-Headers"] = "X-Requested-With, Content-Type"
            return response
        return default_response

    def post(self, request, *args, **kwargs):
        account, _ = Account.objects.get_or_create(
            member=self.request.user.openhumansmember
        )
        account.publish_symptom_reports = True
        account.save()
        return self.get(request, *args, **kwargs)


class PublicReportsLinkView(ListView):
    template_name = "reports/public.html"
    as_json = False

    def get_queryset(self):
        public_symptom_members = OpenHumansMember.objects.filter(
            account__publish_symptom_reports=True
        )
        return public_symptom_members

    def get(self, request, *args, **kwargs):
        if self.as_json:
            data = [
                {
                    "json_path": reverse(
                        "reports:list_member_json", kwargs={"member_id": m.oh_id}
                    ),
                    "csv_path": reverse(
                        "reports:list_member_csv", kwargs={"member_id": m.oh_id}
                    ),
                    "member_id": m.oh_id,
                }
                for m in self.get_queryset()
            ]
            return HttpResponse(json.dumps(data), content_type="application/json")
        return super().get(request, *args, **kwargs)


class ReportSetupView(LoginRequiredMixin, UpdateView):
    template_name = "reports/setup.html"
    login_url = "/"
    model = Account
    form_class = SelectReportSetupForm
    success_url = reverse_lazy("manage-account")

    def get_object(self):
        self.account = self.request.user.openhumansmember.account
        return self.account

    def get_form_kwargs(self):
        """Override to add 'account' when initializing form"""
        kwargs = super().get_form_kwargs()
        kwargs["account"] = self.account
        return kwargs

    def get_context_data(self, *args, **kwargs):
        """
        Override to create custom order for list of setups.
        """
        context = super().get_context_data(*args, **kwargs)
        setup_qs = context["form"].fields["report_setup"]._queryset
        setups = {}
        try:
            setups["current"] = setup_qs.get(id=self.account.report_setup.id)
        except ReportSetup.DoesNotExist:
            pass
        setups["own"] = setup_qs.filter(owner=self.account).exclude(
            id=self.account.report_setup.id
        )
        setups["public"] = (
            setup_qs.filter(public=True)
            .exclude(id=self.account.report_setup.id)
            .exclude(id__in=setups["own"])
        )
        context["report_setups"] = setups
        return context


"""
TODO: Implement reporting of diagnostic testing.
class ReportDiagnosisView(CheckTokenMixin, CreateView):
    model = DiagnosisReport
    template_name = "reports/diagnosis.html"
    fields = ["date_tested", "virus"]

    def form_valid(self, form):
        form.instance.member = self.request.user.openhumansmember
        form.save()
        return super().form_valid(form)
"""
