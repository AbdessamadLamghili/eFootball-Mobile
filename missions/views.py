from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone

from .models import Mission, MissionCompletion, MissionRequest
from notifications.models import Notification
from logs.models import ActivityLog
from accounts.views import _get_client_ip, _check_all_missions
from accounts.models import PointTransaction


@login_required
def mission_list(request):
    user = request.user
    missions = Mission.objects.filter(is_active=True).order_by('mission_code', '-reward_points')

    missions_data = []
    for mission in missions:
        completed = mission.is_completed_by(user)
        pending_request = mission.get_pending_request(user) if mission.is_manual else None
        missions_data.append({
            'mission': mission,
            'completed': completed,
            'pending_request': pending_request,
        })

    from django.conf import settings
    return render(request, 'missions/list.html', {
        'missions_data': missions_data,
        'invitation_pts': getattr(settings, 'POINTS_INVITE_FRIEND', 50),
    })


@login_required
def submit_mission(request, pk):
    """
    For manual missions: create a MissionRequest.
    For automatic missions that can be self-triggered: complete directly.
    """
    if request.method != 'POST':
        return redirect('missions:list')

    user = request.user
    if not user.can_earn_points:
        messages.warning(request, 'Vérifiez votre email pour compléter des missions.')
        return redirect('missions:list')

    mission = get_object_or_404(Mission, pk=pk, is_active=True)

    if mission.is_completed_by(user):
        messages.info(request, 'Vous avez déjà complété cette mission.')
        return redirect('missions:list')

    if mission.has_pending_request(user):
        messages.info(request, 'Votre demande est déjà en cours de validation.')
        return redirect('missions:list')

    if mission.is_manual:
        # Create a pending request for admin review
        MissionRequest.objects.create(user=user, mission=mission)
        Notification.objects.create(
            user=user,
            title='Demande de mission envoyée',
            message=f'Votre demande pour "{mission.title}" est en attente de validation.',
            notification_type=Notification.TYPE_INFO,
        )
        messages.success(request, f'Votre demande pour "{mission.title}" a été envoyée. En attente de validation.')
        return redirect('missions:list')

    # Auto missions that can be manually triggered (custom ones)
    if mission.mission_code in (Mission.CODE_CUSTOM,):
        _complete_mission(user, mission)
        messages.success(request, f'Mission "{mission.title}" accomplie ! +{mission.reward_points} points.')
        return redirect('missions:list')

    messages.info(request, 'Cette mission se complète automatiquement.')
    return redirect('missions:list')


def _complete_mission(user, mission):
    """Internal helper: award points and record completion."""
    MissionCompletion.objects.create(
        user=user,
        mission=mission,
        points_earned=mission.reward_points,
    )
    user.profile.add_points(
        mission.reward_points,
        f'Mission : {mission.title}',
        PointTransaction.CAT_MISSION,
    )
    Notification.objects.create(
        user=user,
        title='Mission accomplie !',
        message=f'"{mission.title}" complétée ! +{mission.reward_points} points.',
        notification_type=Notification.TYPE_POINTS,
    )
    ActivityLog.objects.create(
        user=user,
        action=ActivityLog.ACTION_MISSION_COMPLETE,
        description=f'Mission complétée : {mission.title}',
    )
    _check_all_missions(user)
