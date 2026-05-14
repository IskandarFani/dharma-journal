from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from articles.models import Article, Category
from core.i18n import get_about_content, get_ui_text
from core.models import Issue, IssueTranslation, Subscriber


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


def make_language_links_for_home(current_language):
    links = []

    for code, label in AVAILABLE_LANGUAGES:
        links.append(
            {
                "code": code,
                "label": label,
                "url": reverse("home", args=[code]),
                "is_current": code == current_language,
            }
        )

    return links


def make_language_links_for_about(current_language):
    links = []

    for code, label in AVAILABLE_LANGUAGES:
        links.append(
            {
                "code": code,
                "label": label,
                "url": reverse("about", args=[code]),
                "is_current": code == current_language,
            }
        )

    return links


def make_language_links_for_issue(issue, current_language):
    links = []

    for code, label in AVAILABLE_LANGUAGES:
        translation = issue.get_translation(code)

        if translation:
            url = reverse("issue_detail", args=[code, translation.slug])
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


def make_issue_card(issue, language):
    if not issue:
        return None

    translation = issue.get_translation(language)

    if not translation:
        return None

    return {
        "issue": issue,
        "translation": translation,
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


def get_current_issue_card(language):
    current_issue = (
        Issue.objects.filter(is_current=True)
        .prefetch_related("translations")
        .first()
    )

    return make_issue_card(current_issue, language)


def get_subscription_status(request):
    status = request.GET.get("subscription")

    if status in ["success", "exists", "error"]:
        return status

    return None


def home(request, language="ru"):
    language = normalize_language(language)

    articles = (
        Article.objects.filter(status=Article.Status.PUBLISHED)
        .select_related("category", "author", "issue")
        .prefetch_related("translations", "category__translations")
    )

    featured_article = articles.filter(is_featured=True).first()

    if not featured_article:
        featured_article = articles.first()

    featured_card = None
    used_article_ids = set()

    if featured_article:
        featured_card = make_article_card(featured_article, language)

        if featured_card:
            used_article_ids.add(featured_article.id)

    secondary_cards = []

    editor_pick_articles = articles.filter(is_editor_pick=True).exclude(
        id__in=used_article_ids
    )

    for article in editor_pick_articles:
        card = make_article_card(article, language)

        if not card:
            continue

        secondary_cards.append(card)
        used_article_ids.add(article.id)

        if len(secondary_cards) >= 3:
            break

    latest_cards = []

    latest_articles = articles.exclude(id__in=used_article_ids)

    for article in latest_articles:
        card = make_article_card(article, language)

        if not card:
            continue

        latest_cards.append(card)
        used_article_ids.add(article.id)

        if len(latest_cards) >= 5:
            break

    context = {
        "language": language,
        "available_languages": AVAILABLE_LANGUAGES,
        "language_links": make_language_links_for_home(language),
        "navigation_categories": get_navigation_categories(language),
        "ui": get_ui_text(language),
        "featured_card": featured_card,
        "secondary_cards": secondary_cards,
        "latest_cards": latest_cards,
        "current_issue_card": get_current_issue_card(language),
        "subscription_status": get_subscription_status(request),
    }

    return render(request, "core/home.html", context)


def subscribe(request, language="ru"):
    language = normalize_language(language)

    if request.method != "POST":
        return redirect("home", language=language)

    email = request.POST.get("email", "").strip().lower()

    try:
        validate_email(email)
    except ValidationError:
        return redirect(f"{reverse('home', args=[language])}?subscription=error#subscribe")

    subscriber, created = Subscriber.objects.get_or_create(
        email=email,
        defaults={
            "language": language,
            "is_active": True,
        },
    )

    if not created:
        if not subscriber.is_active:
            subscriber.is_active = True
            subscriber.language = language
            subscriber.save(update_fields=["is_active", "language"])

        return redirect(f"{reverse('home', args=[language])}?subscription=exists#subscribe")

    return redirect(f"{reverse('home', args=[language])}?subscription=success#subscribe")


def about(request, language="ru"):
    language = normalize_language(language)

    context = {
        "language": language,
        "available_languages": AVAILABLE_LANGUAGES,
        "language_links": make_language_links_for_about(language),
        "navigation_categories": get_navigation_categories(language),
        "ui": get_ui_text(language),
        "about_content": get_about_content(language),
    }

    return render(request, "core/about.html", context)


def issue_detail(request, language, slug):
    language = normalize_language(language)

    issue_translation = get_object_or_404(
        IssueTranslation.objects.select_related("issue"),
        language=language,
        slug=slug,
    )

    issue = issue_translation.issue

    articles = (
        Article.objects.filter(
            status=Article.Status.PUBLISHED,
            issue=issue,
        )
        .select_related("category", "author", "issue")
        .prefetch_related("translations", "category__translations")
        .order_by("issue_order", "-published_at", "-created_at")
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
        "language_links": make_language_links_for_issue(issue, language),
        "navigation_categories": get_navigation_categories(language),
        "ui": get_ui_text(language),
        "issue": issue,
        "issue_translation": issue_translation,
        "article_cards": article_cards,
    }

    return render(request, "core/issue_detail.html", context)