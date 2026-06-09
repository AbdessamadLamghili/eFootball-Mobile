from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import User, UserProfile, PointTransaction, DailyReward, EmailVerificationToken


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['username', 'email', 'efootball_id', 'is_email_verified', 'is_suspended', 'date_joined']
    list_filter = ['is_email_verified', 'is_suspended', 'is_staff', 'is_active']
    search_fields = ['username', 'email', 'efootball_id']
    ordering = ['-date_joined']
    readonly_fields = ['date_joined', 'last_login', 'id']

    fieldsets = (
        (None, {'fields': ('id', 'email', 'username', 'efootball_id')}),
        ('Statut', {'fields': ('is_active', 'is_staff', 'is_superuser', 'is_email_verified', 'is_suspended')}),
        ('Dates', {'fields': ('date_joined', 'last_login')}),
        ('Permissions', {'fields': ('groups', 'user_permissions')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username', 'efootball_id', 'password1', 'password2'),
        }),
    )

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        # Never expose password field
        if 'password' in form.base_fields:
            form.base_fields['password'].help_text = (
                "Les mots de passe sont hashés et ne peuvent pas être affichés."
            )
        return form


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'points_balance', 'level', 'current_streak', 'last_daily_reward']
    list_filter = ['level']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['points_balance', 'total_points_earned', 'level', 'current_streak', 'longest_streak']

    def avatar_preview(self, obj):
        if obj.avatar:
            return format_html('<img src="{}" width="50" height="50" style="border-radius:50%"/>', obj.avatar.url)
        return '-'
    avatar_preview.short_description = 'Avatar'


@admin.register(PointTransaction)
class PointTransactionAdmin(admin.ModelAdmin):
    list_display = ['user', 'transaction_type', 'points', 'reason', 'balance_after', 'created_at']
    list_filter = ['transaction_type', 'created_at']
    search_fields = ['user__username', 'reason']
    readonly_fields = ['user', 'points', 'transaction_type', 'reason', 'balance_after', 'created_at']


@admin.register(DailyReward)
class DailyRewardAdmin(admin.ModelAdmin):
    list_display = ['user', 'date', 'points_earned', 'streak_day', 'bonus_points']
    list_filter = ['date']
    search_fields = ['user__username']
