from django.contrib import admin

from .models import User


# admin.site.register(CustomUser)
@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('email', 'phone_number', 'country', 'is_active', 'is_staff')
    list_filter = ('is_active', 'is_staff', 'country')
    search_fields = ('email', 'phone_number', 'country')
    ordering = ('email',)
