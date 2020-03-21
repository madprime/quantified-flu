from django.conf import settings
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.views.generic import TemplateView
from django.shortcuts import render

from openhumans.models import OpenHumansMember

from checkin.models import CheckinSchedule
from checkin.forms import CheckinScheduleForm
from retrospective.models import RetrospectiveEvent
from .helpers import identify_missing_sources


def logout_user(request):
    """
    Logout user.
    """
    if request.method == "POST":
        logout(request)
    redirect_url = settings.LOGOUT_REDIRECT_URL
    if not redirect_url:
        redirect_url = "/"
    return redirect(redirect_url)


class HomeView(TemplateView):
    template_name = "quantified_flu/home.html"

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)

        if self.request.user.is_authenticated:
            openhumansmember = self.request.user.openhumansmember

            # checkin_form
            try:
                schedule = CheckinSchedule.objects.get(member=openhumansmember)
                checkin_form = CheckinScheduleForm(instance=schedule)
            except CheckinSchedule.DoesNotExist:
                checkin_form = CheckinScheduleForm()

            # fitbit_auth_url
            fitbit_auth_url = (
                "https://www.fitbit.com/oauth2/authorize?response_type=code&client_id="
                + settings.FITBIT_CLIENT_ID
                + "&scope=activity%20nutrition%20heartrate%20location%20nutrition%20profile%20settings%20sleep%20social%20weight"
            )

            # missing_sources
            missing_sources = identify_missing_sources(openhumansmember)

            context.update(
                {
                    "checkin_form": checkin_form,
                    "fitbit_auth_url": fitbit_auth_url,
                    "missing_sources": missing_sources,
                    "openhumansmember": openhumansmember,
                }
            )

        # Not logged in.
        else:
            context.update({"openhumans_login_url": OpenHumansMember.get_auth_url()})

        return context


def about(request):
    return render(request, "retrospective/about.html")
