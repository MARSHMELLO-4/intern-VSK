from django.contrib import admin
from .models import Lead, category, CustomUser
from django.contrib.auth.admin import UserAdmin

# Customize the Lead admin interface
@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone', 'status', 'priority', 'assigned_to', 'created_at')
    list_filter = ('status', 'priority', 'lead_source', 'assigned_to', 'category')
    search_fields = ('name', 'email', 'phone', 'company', 'role')
    ordering = ('-created_at',)

# Customize the Category admin interface
@admin.register(category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)
    ordering = ('name',)

# Register CustomUser with custom UserAdmin
@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ('username', 'email', 'first_name', 'last_name', 'phone', 'region', 'is_approved', 'is_staff')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'is_approved', 'region')
    search_fields = ('username', 'email', 'first_name', 'last_name', 'phone')
    ordering = ('username',)

    fieldsets = UserAdmin.fieldsets + (
        ('Additional Info', {
            'fields': ('phone', 'address', 'region', 'is_approved'),
        }),
    )
