from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone

from .models import Mission, MissionCompletion
from notifications.models import Notification
from logs.models import ActivityLog
from accounts.views import _get_client_ip


@login_required
def mission_list(request):
    user = request.user
    missions = Mission.objects.filter(is_active=True)
    mission_type = request.GET.get('type')
    if mission_type:
        missions = missions.filter(mission_type=mission_type)

    missions_data = []
    for mission in missions:
        completed = mission.is_completed_by(user)
        missions_data.append({'mission': mission, 'completed': completed})

    return render(request, 'missions/list.html', {
        'missions_data': missions_data,
        'mission_type': mission_type,
        'type_choices': Mission.TYPE_CHOICES,
    })


@login_required
def complete_mission(request, pk):
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

    MissionCompletion.objects.create(
        user=user,
        mission=mission,
        points_earned=mission.reward_points,
    )
    user.profile.add_points(mission.reward_points, f'Mission : {mission.title}')

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
        ip_address=_get_client_ip(request),
    )

    messages.success(request, f'Mission "{mission.title}" accomplie ! +{mission.reward_points} points.')
    return redirect('missions:list')
