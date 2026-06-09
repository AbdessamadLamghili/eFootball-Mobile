from rest_framework import serializers
from accounts.models import User, UserProfile, PointTransaction, DailyReward
from rewards.models import Reward, RedemptionRequest
from missions.models import Mission, MissionCompletion
from notifications.models import Notification


class UserProfileSerializer(serializers.ModelSerializer):
    avatar_url = serializers.SerializerMethodField()
    level_display = serializers.CharField(source='get_level_display', read_only=True)
    level_info = serializers.SerializerMethodField()

    class Meta:
        model = UserProfile
        fields = [
            'points_balance', 'total_points_earned', 'level', 'level_display',
            'current_streak', 'longest_streak', 'last_daily_reward',
            'avatar_url', 'level_info',
        ]

    def get_avatar_url(self, obj):
        request = self.context.get('request')
        if obj.avatar and request:
            return request.build_absolute_uri(obj.avatar.url)
        return None

    def get_level_info(self, obj):
        return obj.get_level_display_info()


class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'efootball_id',
            'is_email_verified', 'date_joined', 'profile',
        ]
        read_only_fields = ['id', 'email', 'is_email_verified', 'date_joined']


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'efootball_id', 'password', 'confirm_password']

    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError('Les mots de passe ne correspondent pas.')
        return data

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('Un compte avec cet email existe déjà.')
        return value

    def validate_username(self, value):
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError('Ce nom d\'utilisateur est déjà pris.')
        return value

    def validate_efootball_id(self, value):
        if User.objects.filter(efootball_id__iexact=value).exists():
            raise serializers.ValidationError('Cet eFootball ID est déjà utilisé.')
        return value

    def create(self, validated_data):
        validated_data.pop('confirm_password')
        return User.objects.create_user(**validated_data)


class PointTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PointTransaction
        fields = ['id', 'points', 'transaction_type', 'reason', 'balance_after', 'created_at']


class DailyRewardSerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyReward
        fields = ['id', 'date', 'points_earned', 'streak_day', 'bonus_points', 'created_at']


class RewardSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    is_available = serializers.BooleanField(read_only=True)

    class Meta:
        model = Reward
        fields = [
            'id', 'name', 'description', 'image_url', 'points_cost',
            'quantity_available', 'category', 'category_display',
            'is_active', 'is_available',
        ]

    def get_image_url(self, obj):
        request = self.context.get('request')
        if obj.image and request:
            return request.build_absolute_uri(obj.image.url)
        return None


class RedemptionRequestSerializer(serializers.ModelSerializer):
    reward = RewardSerializer(read_only=True)
    reward_id = serializers.PrimaryKeyRelatedField(
        queryset=Reward.objects.filter(is_active=True),
        write_only=True,
        source='reward',
    )
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = RedemptionRequest
        fields = [
            'id', 'reward', 'reward_id', 'points_spent',
            'status', 'status_display', 'admin_note', 'created_at',
        ]
        read_only_fields = ['id', 'points_spent', 'status', 'admin_note', 'created_at']


class MissionSerializer(serializers.ModelSerializer):
    type_display = serializers.CharField(source='get_mission_type_display', read_only=True)
    is_completed = serializers.SerializerMethodField()

    class Meta:
        model = Mission
        fields = [
            'id', 'title', 'description', 'reward_points',
            'mission_type', 'type_display', 'is_active', 'icon', 'is_completed',
        ]

    def get_is_completed(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.is_completed_by(request.user)
        return False


class NotificationSerializer(serializers.ModelSerializer):
    icon = serializers.CharField(read_only=True)
    type_display = serializers.CharField(source='get_notification_type_display', read_only=True)

    class Meta:
        model = Notification
        fields = ['id', 'title', 'message', 'notification_type', 'type_display', 'icon', 'is_read', 'created_at']
        read_only_fields = ['id', 'title', 'message', 'notification_type', 'created_at']
