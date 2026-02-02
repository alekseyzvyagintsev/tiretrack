from django.contrib import admin

from .models import User


# admin.site.register(CustomUser)
@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    exclude = ("password",)
