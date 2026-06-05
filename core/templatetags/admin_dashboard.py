from django import template
from django.db.models import Count

from articles.models import Article, Author, Category
from core.models import Issue, Subscriber


register = template.Library()


@register.simple_tag
def editorial_dashboard():
    required_language_count = 3

    current_issue = (
        Issue.objects.filter(is_current=True)
        .prefetch_related("translations")
        .first()
    )
    recent_articles = (
        Article.objects.select_related("category", "author", "issue")
        .prefetch_related("translations")
        .order_by("-updated_at")[:6]
    )

    return {
        "article_count": Article.objects.count(),
        "draft_count": Article.objects.filter(status=Article.Status.DRAFT).count(),
        "published_count": Article.objects.filter(status=Article.Status.PUBLISHED).count(),
        "editor_pick_count": Article.objects.filter(is_editor_pick=True).count(),
        "featured_count": Article.objects.filter(is_featured=True).count(),
        "missing_translation_count": (
            Article.objects.annotate(language_count=Count("translations", distinct=True))
            .filter(language_count__lt=required_language_count)
            .count()
        ),
        "category_count": Category.objects.count(),
        "active_category_count": Category.objects.filter(is_active=True).count(),
        "author_count": Author.objects.count(),
        "issue_count": Issue.objects.count(),
        "current_issue": current_issue,
        "subscriber_count": Subscriber.objects.count(),
        "active_subscriber_count": Subscriber.objects.filter(is_active=True).count(),
        "recent_articles": recent_articles,
    }
