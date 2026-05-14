from django.contrib import admin

from .models import Issue, IssueTranslation, Subscriber


class IssueTranslationInline(admin.StackedInline):
    model = IssueTranslation
    extra = 1
    prepopulated_fields = {"slug": ("title",)}


@admin.register(Issue)
class IssueAdmin(admin.ModelAdmin):
    inlines = [IssueTranslationInline]

    list_display = [
        "__str__",
        "is_current",
        "published_at",
        "created_at",
    ]
    list_editable = ["is_current"]
    list_filter = ["is_current"]
    date_hierarchy = "published_at"

    fieldsets = (
        (
            "Main information",
            {
                "fields": (
                    "is_current",
                    "published_at",
                )
            },
        ),
        (
            "Cover image",
            {
                "fields": (
                    "cover_image",
                )
            },
        ),
    )


@admin.register(Subscriber)
class SubscriberAdmin(admin.ModelAdmin):
    list_display = [
        "email",
        "language",
        "is_active",
        "created_at",
    ]
    list_filter = [
        "language",
        "is_active",
    ]
    search_fields = [
        "email",
    ]
    list_editable = [
        "is_active",
    ]
    date_hierarchy = "created_at"