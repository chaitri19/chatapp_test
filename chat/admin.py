from django.contrib import admin
from .models import UserConnection

@admin.register(UserConnection)
class UserConnectionAdmin(admin.ModelAdmin):
    list_display = ('sender', 'receiver', 'status', 'created_at', 'updated_at')
    list_filter = ('status',)
    search_fields = ('sender__username', 'receiver__username')
