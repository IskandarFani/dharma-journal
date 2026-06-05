import csv

from django.contrib import admin, messages
from django.db import models
from django.forms import Textarea
from django.http import HttpResponse
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from .models import Issue, IssueTranslation, Subscriber


LANGUAGE_LABELS = {
    "ru": "RU",
    "en": "EN",
    "lt": "LT",
}


def make_language_badges(translations):
    existing_languages = {translation.language for translation in translations}
    badges = []

    for code, label in LANGUAGE_LABELS.items():
        css_class = "language-badge is-ready" if code in existing_languages else "language-badge"
        badges.append(format_html('<span class="{}">{}</span>', css_class, label))

    return format_html('<span class="language-badges">{}</span>', mark_safe("".join(badges)))


def image_preview(image, alt_text):
    if not image:
        return mark_safe('<span class="admin-muted">No image</span>')

    return format_html(
        '<img class="admin-thumb" src="{}" alt="{}">',
        image.url,
        alt_text,
    )


class IssueTranslationInline(admin.StackedInline):
    model = IssueTranslation
    extra = 0
    prepopulated_fields = {"slug": ("title",)}
    fields = ["language", "title", "slug", "description"]
    formfield_overrides = {
        models.TextField: {"widget": Textarea(attrs={"rows": 5})},
    }


@admin.register(Issue)
class IssueAdmin(admin.ModelAdmin):
    inlines = [IssueTranslationInline]

    list_display = [
        "title",
        "translations_status",
        "cover",
        "is_current",
        "published_at",
        "created_at",
        "article_count",
    ]
    list_editable = ["is_current"]
    list_filter = ["is_current"]
    search_fields = [
        "translations__title",
        "translations__slug",
        "translations__description",
    ]
    readonly_fields = ["cover_preview", "created_at", "updated_at", "preview_links"]
    date_hierarchy = "published_at"
    save_on_top = True
    actions = ["make_current_issue", "unset_current_issue"]

    fieldsets = (
        (
            "Issue setup",
            {
                "fields": (
                    "is_current",
                    "published_at",
                )
            },
        ),
        (
            "Cover",
            {
                "fields": (
                    "cover_image",
                    "cover_preview",
                )
            },
        ),
        (
            "Publishing links",
            {
                "classes": ("collapse",),
                "fields": (
                    "preview_links",
                    "created_at",
                    "updated_at",
                ),
            },
        ),
    )

    class Media:
        css = {"all": ("core/admin.css",)}

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("translations", "articles")

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

        if obj.is_current:
            Issue.objects.exclude(pk=obj.pk).update(is_current=False)

    @admin.display(description="Issue", ordering="translations__title")
    def title(self, obj):
        return str(obj)

    @admin.display(description="Languages")
    def translations_status(self, obj):
        return make_language_badges(obj.translations.all())

    @admin.display(description="Cover")
    def cover(self, obj):
        return image_preview(obj.cover_image, str(obj))

    @admin.display(description="Cover preview")
    def cover_preview(self, obj):
        return image_preview(obj.cover_image, str(obj))

    @admin.display(description="Articles")
    def article_count(self, obj):
        return obj.articles.count()

    @admin.display(description="Site links")
    def preview_links(self, obj):
        if not obj.pk:
            return "Links will appear after the issue is saved."

        links = []

        for translation in obj.translations.all():
            url = reverse("issue_detail", args=[translation.language, translation.slug])
            links.append(
                format_html(
                    '<a class="admin-link-chip" href="{}" target="_blank">{}: open</a>',
                    url,
                    LANGUAGE_LABELS.get(translation.language, translation.language.upper()),
                )
            )

        if not links:
            return "Add at least one translation."

        return format_html('<span class="admin-link-chips">{}</span>', mark_safe("".join(links)))

    @admin.action(description="Make selected issue current")
    def make_current_issue(self, request, queryset):
        if queryset.count() != 1:
            self.message_user(
                request,
                "Select exactly one issue to make it current.",
                messages.ERROR,
            )
            return

        issue = queryset.first()
        Issue.objects.update(is_current=False)
        issue.is_current = True
        issue.save(update_fields=["is_current", "updated_at"])
        self.message_user(request, f"Current issue: {issue}", messages.SUCCESS)

    @admin.action(description="Unset current issue flag")
    def unset_current_issue(self, request, queryset):
        updated = queryset.update(is_current=False)
        self.message_user(request, f"Updated issues: {updated}", messages.SUCCESS)


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
    readonly_fields = ["created_at"]
    actions = ["activate_subscribers", "deactivate_subscribers", "export_csv"]
    list_per_page = 50

    class Media:
        css = {"all": ("core/admin.css",)}

    @admin.action(description="Activate selected subscriptions")
    def activate_subscribers(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"Activated subscriptions: {updated}", messages.SUCCESS)

    @admin.action(description="Deactivate selected subscriptions")
    def deactivate_subscribers(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"Deactivated subscriptions: {updated}", messages.SUCCESS)

    @admin.action(description="Export selected subscribers to CSV")
    def export_csv(self, request, queryset):
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="subscribers.csv"'
        response.write("\ufeff")

        writer = csv.writer(response)
        writer.writerow(["email", "language", "is_active", "created_at"])

        for subscriber in queryset.order_by("email"):
            writer.writerow(
                [
                    subscriber.email,
                    subscriber.language,
                    subscriber.is_active,
                    subscriber.created_at.isoformat(),
                ]
            )

        return response
