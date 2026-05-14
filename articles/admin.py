from django.contrib import admin

from .models import (
    Article,
    ArticleTranslation,
    Author,
    Category,
    CategoryTranslation,
)


class CategoryTranslationInline(admin.StackedInline):
    model = CategoryTranslation
    extra = 1
    prepopulated_fields = {"slug": ("title",)}


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    inlines = [CategoryTranslationInline]

    list_display = ["__str__", "order", "is_active"]
    list_editable = ["order", "is_active"]

    fields = ["order", "is_active", "cover_image"]


@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ["name", "slug"]
    prepopulated_fields = {"slug": ("name",)}


class ArticleTranslationInline(admin.StackedInline):
    model = ArticleTranslation
    extra = 1
    prepopulated_fields = {"slug": ("title",)}


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    inlines = [ArticleTranslationInline]

    list_display = [
        "__str__",
        "category",
        "issue",
        "issue_order",
        "author",
        "status",
        "is_featured",
        "is_editor_pick",
        "published_at",
    ]
    list_filter = ["status", "is_featured", "is_editor_pick", "category", "issue"]
    list_editable = ["issue_order", "status", "is_featured", "is_editor_pick"]
    date_hierarchy = "published_at"

    fieldsets = (
        (
            "Main information",
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
            "Issue",
            {
                "fields": (
                    "issue",
                    "issue_order",
                )
            },
        ),
        (
            "Cover image",
            {
                "fields": (
                    "cover_image",
                    "cover_caption",
                )
            },
        ),
    )