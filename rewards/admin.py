from django.contrib import admin
from django.utils.html import format_html
from django.db import transaction
from .models import Reward, RedemptionRequest, RedemptionStatusHistory
from notifications.models import Notification
from accounts.emails import send_reward_accepted_email, send_reward_rejected_email
from logs.models import ActivityLog


class RedemptionStatusHistoryInline(admin.TabularInline):
    model = RedemptionStatusHistory
    extra = 0
    readonly_fields = ['old_status', 'new_status', 'changed_by', 'note', 'created_at']
    can_delete = False


@admin.register(Reward)
class RewardAdmin(admin.ModelAdmin):
    list_display = ['name', 'points_cost', 'category', 'quantity_available', 'is_active', 'image_preview']
    list_filter = ['is_active', 'category']
    search_fields = ['name', 'description']
    list_editable = ['is_active', 'points_cost']
    ordering = ['points_cost']

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="50" height="50" style="object-fit:cover;border-radius:4px;"/>', obj.image.url)
        return '—'
    image_preview.short_description = 'Aperçu'


@admin.register(RedemptionRequest)
class RedemptionRequestAdmin(admin.ModelAdmin):
    list_display = ['user', 'reward', 'points_spent', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['user__username', 'reward__name']
    readonly_fields = ['user', 'reward', 'points_spent', 'created_at']
    inlines = [RedemptionStatusHistoryInline]
    actions = ['accept_requests', 'reject_requests', 'mark_delivered']

    @transaction.atomic
    def _change_status(self, request, queryset, new_status, note=''):
        for obj in queryset.filter(status=RedemptionRequest.STATUS_PENDING):
            old_status = obj.status
            obj.status = new_status
            obj.save()
            RedemptionStatusHistory.objects.create(
                redemption=obj,
                old_status=old_status,
                new_status=new_status,
                changed_by=request.user,
                note=note,
            )
            if new_status == RedemptionRequest.STATUS_ACCEPTED:
                Notification.objects.create(
                    user=obj.user,
                    title='Récompense acceptée !',
                    message=f'Votre demande pour "{obj.reward.name}" a été acceptée.',
                    notification_type=Notification.TYPE_SUCCESS,
                )
                send_reward_accepted_email(obj.user, obj)
                ActivityLog.objects.create(
                    user=obj.user,
                    action=ActivityLog.ACTION_REWARD_ACCEPTED,
                    description=f'Admin {request.user.username} a accepté : {obj.reward.name}',
                )
            elif new_status == RedemptionRequest.STATUS_REJECTED:
                obj.user.profile.add_points(obj.points_spent, f'Remboursement : {obj.reward.name} refusée')
                Notification.objects.create(
                    user=obj.user,
                    title='Récompense refusée',
                    message=f'Votre demande pour "{obj.reward.name}" a été refusée. Points remboursés.',
                    notification_type=Notification.TYPE_ERROR,
                )
                send_reward_rejected_email(obj.user, obj)

    def accept_requests(self, request, queryset):
        self._change_status(request, queryset, RedemptionRequest.STATUS_ACCEPTED)
        self.message_user(request, 'Demandes acceptées.')
    accept_requests.short_description = 'Accepter les demandes sélectionnées'

    def reject_requests(self, request, queryset):
        self._change_status(request, queryset, RedemptionRequest.STATUS_REJECTED)
        self.message_user(request, 'Demandes refusées. Points remboursés.')
    reject_requests.short_description = 'Refuser les demandes sélectionnées'

    def mark_delivered(self, request, queryset):
        queryset.filter(status=RedemptionRequest.STATUS_ACCEPTED).update(status=RedemptionRequest.STATUS_DELIVERED)
        self.message_user(request, 'Demandes marquées comme livrées.')
    mark_delivered.short_description = 'Marquer comme livrées'


@admin.register(RedemptionStatusHistory)
class RedemptionStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ['redemption', 'old_status', 'new_status', 'changed_by', 'created_at']
    readonly_fields = ['redemption', 'old_status', 'new_status', 'changed_by', 'created_at']
