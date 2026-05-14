from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from articles.models import Article, ArticleTranslation, Category, CategoryTranslation
from core.i18n import get_ui_text


AVAILABLE_LANGUAGES = [
    ("ru", "RU"),
    ("en", "EN"),
    ("lt", "LT"),
]


def normalize_language(language):
    available_codes = [code for code, label in AVAILABLE_LANGUAGES]

    if language not in available_codes:
        return "ru"

    return language


def make_article_card(article, language):
    translation = article.get_translation(language)

    if not translation:
        return None

    category_translation = article.category.get_translation(language)

    return {
        "article": article,
        "translation": translation,
        "category_translation": category_translation,
    }


def get_navigation_categories(language):
    categories = (
        Category.objects.filter(is_active=True)
        .prefetch_related("translations")
        .order_by("order", "id")
    )

    navigation_categories = []

    for category in categories:
        translation = category.get_translation(language)

        if not translation:
            continue

        navigation_categories.append(
            {
                "category": category,
                "translation": translation,
            }
        )

    return navigation_categories


def make_language_links_for_article(article, current_language):
    links = []

    for code, label in AVAILABLE_LANGUAGES:
        translation = article.get_translation(code)

        if translation:
            url = reverse("article_detail", args=[code, translation.slug])
        else:
            url = reverse("home", args=[code])

        links.append(
            {
                "code": code,
                "label": label,
                "url": url,
                "is_current": code == current_language,
            }
        )

    return links


def make_language_links_for_category(category, current_language):
    links = []

    for code, label in AVAILABLE_LANGUAGES:
        translation = category.get_translation(code)

        if translation:
            url = reverse("category_detail", args=[code, translation.slug])
        else:
            url = reverse("home", args=[code])

        links.append(
            {
                "code": code,
                "label": label,
                "url": url,
                "is_current": code == current_language,
            }
        )

    return links


def article_detail(request, language, slug):
    language = normalize_language(language)

    translation = get_object_or_404(
        ArticleTranslation.objects.select_related("article", "article__category", "article__author"),
        language=language,
        slug=slug,
        article__status=Article.Status.PUBLISHED,
    )

    article = translation.article
    category_translation = article.category.get_translation(language)

    related_articles = (
        Article.objects.filter(
            status=Article.Status.PUBLISHED,
            category=article.category,
        )
        .exclude(id=article.id)
        .select_related("category", "author")
        .prefetch_related("translations", "category__translations")[:3]
    )

    related_cards = []

    for related_article in related_articles:
        card = make_article_card(related_article, language)

        if not card:
            continue

        related_cards.append(card)

    context = {
        "language": language,
        "available_languages": AVAILABLE_LANGUAGES,
        "language_links": make_language_links_for_article(article, language),
        "navigation_categories": get_navigation_categories(language),
        "ui": get_ui_text(language),

        "article": article,
        "translation": translation,
        "category_translation": category_translation,
        "related_cards": related_cards,
    }

    return render(request, "articles/article_detail.html", context)


def category_detail(request, language, slug):
    language = normalize_language(language)

    category_translation = get_object_or_404(
        CategoryTranslation.objects.select_related("category"),
        language=language,
        slug=slug,
        category__is_active=True,
    )

    category = category_translation.category

    articles = (
        Article.objects.filter(
            status=Article.Status.PUBLISHED,
            category=category,
        )
        .select_related("category", "author")
        .prefetch_related("translations", "category__translations")
    )

    article_cards = []

    for article in articles:
        card = make_article_card(article, language)

        if not card:
            continue

        article_cards.append(card)

    context = {
        "language": language,
        "available_languages": AVAILABLE_LANGUAGES,
        "language_links": make_language_links_for_category(category, language),
        "navigation_categories": get_navigation_categories(language),
        "ui": get_ui_text(language),

        "category": category,
        "category_translation": category_translation,
        "article_cards": article_cards,
    }

    return render(request, "articles/category_detail.html", context)