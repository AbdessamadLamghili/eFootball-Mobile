from django.contrib import admin

from .models import League, LeagueLog, LeagueParticipant, LeagueStanding, Match, MatchResult


class LeagueParticipantInline(admin.TabularInline):
    model = LeagueParticipant
    extra = 0
    readonly_fields = ['added_by', 'added_at']


@admin.register(League)
class LeagueAdmin(admin.ModelAdmin):
    list_display = ['name', 'status', 'season', 'created_by', 'started_at', 'ended_at', 'champion']
    list_filter = ['status']
    search_fields = ['name', 'season']
    inlines = [LeagueParticipantInline]
    readonly_fields = ['created_at', 'updated_at', 'started_at', 'ended_at', 'champion']


@admin.register(LeagueParticipant)
class LeagueParticipantAdmin(admin.ModelAdmin):
    list_display = ['user', 'team_name', 'league', 'added_at']
    list_filter = ['league']
    search_fields = ['user__username', 'team_name']


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'league', 'round_number', 'status', 'home_score', 'away_score']
    list_filter = ['league', 'status', 'round_number']
    readonly_fields = ['created_at']


@admin.register(MatchResult)
class MatchResultAdmin(admin.ModelAdmin):
    list_display = ['match', 'home_score', 'away_score', 'submitted_by', 'submitted_at', 'validated_by']
    readonly_fields = ['submitted_at', 'validated_at']


@admin.register(LeagueStanding)
class LeagueStandingAdmin(admin.ModelAdmin):
    list_display = ['participant', 'league', 'points', 'played', 'wins', 'draws', 'losses', 'goals_for', 'goals_against']
    list_filter = ['league']


@admin.register(LeagueLog)
class LeagueLogAdmin(admin.ModelAdmin):
    list_display = ['league', 'action', 'performed_by', 'created_at']
    list_filter = ['league', 'action']
    readonly_fields = ['created_at']
