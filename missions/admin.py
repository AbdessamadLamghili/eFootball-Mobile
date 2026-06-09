from django.contrib import admin
from .models import Mission, MissionCompletion


@admin.register(Mission)
class MissionAdmin(admin.ModelAdmin):
    list_display = ['title', 'mission_type', 'reward_points', 'is_active', 'created_at']
    list_filter = ['mission_type', 'is_active']
    search_fields = ['title', 'description']
    list_editable = ['is_active', 'reward_points']


@admin.register(MissionCompletion)
class MissionCompletionAdmin(admin.ModelAdmin):
    list_display = ['user', 'mission', 'points_earned', 'completed_at']
    list_filter = ['mission__mission_type', 'completed_at']
    search_fields = ['user__username', 'mission__title']
    readonly_fields = ['user', 'mission', 'points_earned', 'completed_at']
