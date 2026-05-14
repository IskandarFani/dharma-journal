from django.shortcuts import render
from django.urls import reverse

from articles.models import Article, Category, LANGUAGE_CHOICES
from .i18n import get_ui_text


AVAILABLE_LANGUAGES = [code for code, _name in LANGUAGE_CHOICES]


def normalize_language(language):
    if language not in AVAILABLE_LANGUAGES:
        return "ru"
    return language


def make_language_links_for_home(current_language):
    links = []

    for code in AVAILABLE_LANGUAGES:
        links.append({
            "code": code,
            "url": reverse("home", args=[code]),
            "is_current": code == current_language,
        })

    return links


def make_article_card(article, language):
    translation = article.get_translation(language)

    if translation is None:
        return None

    category_translation = article.category.get_translation(language)

    return {
        "article": article,
        "translation": translation,
        "category_translation": category_translation,
    }


def get_navigation_categories(language):
    categories = (
        Category.objects
        .filter(is_active=True, translations__language=language)
        .prefetch_related("translations")
        .distinct()
    )

    navigation_categories = []

    for category in categories:
        translation = category.get_translation(language)

        if translation:
            navigation_categories.append({
                "category": category,
                "translation": translation,
                "url": reverse("category_detail", args=[language, translation.slug]),
            })

    return navigation_categories


def home(request, language="ru"):
    language = normalize_language(language)

    published_articles = (
        Article.objects
        .filter(
            status=Article.Status.PUBLISHED,
            translations__language=language,
        )
        .select_related("category", "author")
        .prefetch_related("translations", "category__translations")
        .distinct()
    )

    featured_article = (
        published_articles
        .filter(is_featured=True)
        .first()
    )

    featured_card = None

    if featured_article:
        featured_card = make_article_card(featured_article, language)

    secondary_articles = published_articles

    if featured_article:
        secondary_articles = secondary_articles.exclude(id=featured_article.id)

    secondary_cards = []

    for article in secondary_articles[:3]:
        card = make_article_card(article, language)

        if card:
            secondary_cards.append(card)

    latest_cards = []

    for article in published_articles[:5]:
        card = make_article_card(article, language)

        if card:
            latest_cards.append(card)

    context = {
        "language": language,
        "available_languages": AVAILABLE_LANGUAGES,
        "language_links": make_language_links_for_home(language),
        "navigation_categories": get_navigation_categories(language),
        "ui": get_ui_text(language),
        "featured_card": featured_card,
        "secondary_cards": secondary_cards,
        "latest_cards": latest_cards,
    }

    return render(request, "core/home.html", context)