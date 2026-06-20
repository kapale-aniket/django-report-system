from django.contrib import admin

from .models import FAQ, UserQuestion, VisitorQuestion


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ('question', 'sort_order', 'is_active', 'updated_at')
    list_filter = ('is_active',)
    ordering = ('sort_order', 'pk')


@admin.register(UserQuestion)
class UserQuestionAdmin(admin.ModelAdmin):
    list_display = ('subject', 'user', 'status', 'created_at', 'answered_by')
    list_filter = ('status',)
    search_fields = ('subject', 'body', 'user__username')
    readonly_fields = ('user', 'created_at', 'answered_at', 'answered_by')


@admin.register(VisitorQuestion)
class VisitorQuestionAdmin(admin.ModelAdmin):
    list_display = ('subject', 'email', 'name', 'status', 'created_at', 'answered_by')
    list_filter = ('status',)
    search_fields = ('subject', 'body', 'email', 'name')
    readonly_fields = ('name', 'email', 'created_at', 'answered_at', 'answered_by')
