from django.contrib import admin
from django.utils import timezone
from .models import Mission, MissionCompletion, MissionRequest


@admin.register(Mission)
class MissionAdmin(admin.ModelAdmin):
    list_display = ['title', 'mission_code', 'reward_points', 'validation_type', 'is_active', 'created_at']
    list_editable = ['is_active', 'reward_points']
    list_filter = ['mission_code', 'validation_type', 'is_active']
    search_fields = ['title', 'description']
    ordering = ['mission_code', '-reward_points']


@admin.register(MissionRequest)
class MissionRequestAdmin(admin.ModelAdmin):
    list_display = ['user', 'mission', 'status', 'created_at', 'reviewed_at', 'reviewed_by']
    list_filter = ['status', 'mission']
    search_fields = ['user__username', 'user__email', 'mission__title']
    readonly_fields = ['created_at', 'reviewed_at', 'reviewed_by']
    ordering = ['-created_at']
    actions = ['approve_requests', 'reject_requests']

    def approve_requests(self, request, queryset):
        from missions.views import _complete_mission
        approved = 0
        for mr in queryset.filter(status=MissionRequest.STATUS_PENDING):
            if not mr.mission.is_completed_by(mr.user):
                _complete_mission(mr.user, mr.mission)
            mr.status = MissionRequest.STATUS_APPROVED
            mr.reviewed_by = request.user
            mr.reviewed_at = timezone.now()
            mr.save()
            approved += 1
        self.message_user(request, f'{approved} demande(s) approuvée(s).')
    approve_requests.short_description = 'Approuver les demandes sélectionnées'

    def reject_requests(self, request, queryset):
        updated = queryset.filter(status=MissionRequest.STATUS_PENDING).update(
            status=MissionRequest.STATUS_REJECTED,
            rejection_reason='Refus en masse par administrateur',
        )
        self.message_user(request, f'{updated} demande(s) refusée(s).')
    reject_requests.short_description = 'Refuser les demandes sélectionnées'


@admin.register(MissionCompletion)
class MissionCompletionAdmin(admin.ModelAdmin):
    list_display = ['user', 'mission', 'points_earned', 'completed_at']
    list_filter = ['mission']
    search_fields = ['user__username', 'mission__title']
    readonly_fields = ['user', 'mission', 'points_earned', 'completed_at']
    ordering = ['-completed_at']
