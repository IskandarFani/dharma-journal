from django.contrib import admin, messages
from django.db import models
from django.forms import Textarea
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.timezone import now

from .models import (
    Article,
    ArticleTranslation,
    Author,
    Category,
    CategoryTranslation,
)


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


class CategoryTranslationInline(admin.StackedInline):
    model = CategoryTranslation
    extra = 0
    prepopulated_fields = {"slug": ("title",)}
    fields = ["language", "title", "slug", "description"]
    formfield_overrides = {
        models.TextField: {"widget": Textarea(attrs={"rows": 4})},
    }


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    inlines = [CategoryTranslationInline]

    list_display = ["title", "translations_status", "cover", "order", "is_active"]
    list_editable = ["order", "is_active"]
    list_filter = ["is_active"]
    search_fields = [
        "translations__title",
        "translations__slug",
        "translations__description",
    ]
    readonly_fields = ["cover_preview"]
    actions = ["activate_categories", "deactivate_categories"]
    fields = ["order", "is_active", "cover_image", "cover_preview"]

    class Media:
        css = {"all": ("core/admin.css",)}

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("translations")

    @admin.display(description="Category", ordering="translations__title")
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

    @admin.action(description="Activate selected categories")
    def activate_categories(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"Activated categories: {updated}", messages.SUCCESS)

    @admin.action(description="Deactivate selected categories")
    def deactivate_categories(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"Deactivated categories: {updated}", messages.SUCCESS)


@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "article_count"]
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ["name", "slug", "bio"]
    formfield_overrides = {
        models.TextField: {"widget": Textarea(attrs={"rows": 6})},
    }

    class Media:
        css = {"all": ("core/admin.css",)}

    @admin.display(description="Articles")
    def article_count(self, obj):
        return obj.articles.count()


class ArticleTranslationInline(admin.StackedInline):
    model = ArticleTranslation
    extra = 0
    prepopulated_fields = {"slug": ("title",)}
    fieldsets = (
        (
            "Editorial copy",
            {
                "fields": (
                    "language",
                    "title",
                    "slug",
                    "subtitle",
                    "excerpt",
                    "body",
                )
            },
        ),
        (
            "SEO",
            {
                "classes": ("collapse",),
                "fields": (
                    "seo_title",
                    "seo_description",
                ),
            },
        ),
    )
    formfield_overrides = {
        models.TextField: {"widget": Textarea(attrs={"rows": 5})},
    }

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        formfield = super().formfield_for_dbfield(db_field, request, **kwargs)

        if db_field.name == "body":
            formfield.widget.attrs["rows"] = 18
            formfield.widget.attrs["class"] = "vLargeTextField article-body-field"

        if db_field.name == "excerpt":
            formfield.widget.attrs["rows"] = 4

        if db_field.name == "seo_description":
            formfield.widget.attrs["rows"] = 3

        return formfield


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    inlines = [ArticleTranslationInline]

    list_display = [
        "title",
        "translations_status",
        "placement",
        "editorial_flags",
        "publication_state",
        "published_at",
    ]
    list_filter = ["status", "is_featured", "is_editor_pick", "category", "issue"]
    search_fields = [
        "translations__title",
        "translations__subtitle",
        "translations__excerpt",
        "translations__body",
        "author__name",
        "category__translations__title",
        "issue__translations__title",
    ]
    date_hierarchy = "published_at"
    autocomplete_fields = ["category", "author", "issue"]
    readonly_fields = ["cover_preview", "created_at", "updated_at", "preview_links"]
    list_select_related = ["category", "author", "issue"]
    list_per_page = 30
    save_on_top = True
    actions = ["publish_articles", "move_to_drafts", "mark_editor_pick", "unmark_editor_pick"]

    fieldsets = (
        (
            "Editorial setup",
            {
                "fields": (
                    "category",
                    "author",
                    "status",
                    "is_featured",
                    "is_editor_pick",
                    "published_at",
                )
            },
        ),
        (
            "Issue placement",
            {
                "fields": (
                    "issue",
                    "issue_order",
                )
            },
        ),
        (
            "Cover",
            {
                "fields": (
                    "cover_image",
                    "cover_preview",
                    "cover_caption",
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
        js = ("core/admin-tabs.js",)

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("category", "author", "issue")
            .prefetch_related("translations", "category__translations", "issue__translations")
        )

    @admin.display(description="Article", ordering="translations__title")
    def title(self, obj):
        category = obj.category if obj.category_id else "No category"
        author = obj.author if obj.author_id else "No author"

        return format_html(
            '<span class="article-title-cell">'
            '<strong>{}</strong>'
            '<small>{} · {}</small>'
            "</span>",
            str(obj),
            category,
            author,
        )

    @admin.display(description="Languages")
    def translations_status(self, obj):
        return make_language_badges(obj.translations.all())

    @admin.display(description="Cover")
    def cover(self, obj):
        return image_preview(obj.cover_image, str(obj))

    @admin.display(description="Placement")
    def placement(self, obj):
        issue = obj.issue if obj.issue_id else "No issue"

        return format_html(
            '<span class="article-meta-cell">'
            '<strong>{}</strong>'
            '<small>Issue order: {}</small>'
            "</span>",
            issue,
            obj.issue_order,
        )

    @admin.display(description="Editorial")
    def editorial_flags(self, obj):
        flags = []

        if obj.is_featured:
            flags.append('<span class="status-pill is-featured">Featured</span>')

        if obj.is_editor_pick:
            flags.append('<span class="status-pill is-editor-pick">Editor pick</span>')

        if obj.cover_image:
            flags.append('<span class="status-pill is-neutral">Cover</span>')

        if not flags:
            return mark_safe('<span class="admin-muted">No flags</span>')

        return format_html('<span class="article-flags">{}</span>', mark_safe("".join(flags)))

    @admin.display(description="State", ordering="status")
    def publication_state(self, obj):
        if obj.status == Article.Status.PUBLISHED:
            return mark_safe('<span class="status-pill is-published">Published</span>')

        return mark_safe('<span class="status-pill">Draft</span>')

    @admin.display(description="Cover preview")
    def cover_preview(self, obj):
        return image_preview(obj.cover_image, str(obj))

    @admin.display(description="Site links")
    def preview_links(self, obj):
        if not obj.pk:
            return "Links will appear after the article is saved."

        links = []

        for translation in obj.translations.all():
            url = reverse("article_detail", args=[translation.language, translation.slug])
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

    @admin.action(description="Publish selected articles")
    def publish_articles(self, request, queryset):
        published_count = 0

        for article in queryset:
            article.status = Article.Status.PUBLISHED

            if article.published_at is None:
                article.published_at = now()

            article.save(update_fields=["status", "published_at", "updated_at"])
            published_count += 1

        self.message_user(request, f"Published articles: {published_count}", messages.SUCCESS)

    @admin.action(description="Move selected articles to drafts")
    def move_to_drafts(self, request, queryset):
        updated = queryset.update(status=Article.Status.DRAFT)
        self.message_user(request, f"Moved to drafts: {updated}", messages.SUCCESS)

    @admin.action(description="Mark as editor picks")
    def mark_editor_pick(self, request, queryset):
        updated = queryset.update(is_editor_pick=True)
        self.message_user(request, f"Marked as editor picks: {updated}", messages.SUCCESS)

    @admin.action(description="Remove from editor picks")
    def unmark_editor_pick(self, request, queryset):
        updated = queryset.update(is_editor_pick=False)
        self.message_user(request, f"Removed from editor picks: {updated}", messages.SUCCESS)
