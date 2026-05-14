from django.db import models
from django.utils import timezone


LANGUAGE_CHOICES = [
    ("ru", "Russian"),
    ("en", "English"),
    ("lt", "Lithuanian"),
]


class Category(models.Model):
    order = models.PositiveIntegerField("Order", default=100)
    is_active = models.BooleanField("Active", default=True)

    cover_image = models.ImageField(
        "Category cover image",
        upload_to="categories/",
        blank=True,
        null=True,
    )

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "Category"
        verbose_name_plural = "Categories"

    def __str__(self):
        en_translation = self.translations.filter(language="en").first()
        if en_translation:
            return en_translation.title

        ru_translation = self.translations.filter(language="ru").first()
        if ru_translation:
            return ru_translation.title

        any_translation = self.translations.first()
        if any_translation:
            return any_translation.title

        return f"Category #{self.pk}"

    def get_translation(self, language="ru"):
        return self.translations.filter(language=language).first()


class CategoryTranslation(models.Model):
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="translations",
        verbose_name="Category",
    )
    language = models.CharField(
        "Language",
        max_length=2,
        choices=LANGUAGE_CHOICES,
    )
    title = models.CharField("Title", max_length=200)
    slug = models.SlugField("Slug", max_length=220)
    description = models.TextField("Description", blank=True)

    class Meta:
        unique_together = [
            ("category", "language"),
            ("language", "slug"),
        ]
        verbose_name = "Category translation"
        verbose_name_plural = "Category translations"

    def __str__(self):
        return f"{self.title} [{self.language}]"


class Author(models.Model):
    name = models.CharField("Name", max_length=200)
    slug = models.SlugField("Slug", max_length=220, unique=True)
    bio = models.TextField("Biography", blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Author"
        verbose_name_plural = "Authors"

    def __str__(self):
        return self.name


class Article(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"

    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="articles",
        verbose_name="Category",
    )
    author = models.ForeignKey(
        Author,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="articles",
        verbose_name="Author",
    )

    issue = models.ForeignKey(
        "core.Issue",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="articles",
        verbose_name="Issue",
    )
    issue_order = models.PositiveIntegerField("Issue order", default=100)

    status = models.CharField(
        "Status",
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    is_featured = models.BooleanField("Featured article", default=False)
    is_editor_pick = models.BooleanField("Editor’s pick", default=False)

    cover_image = models.ImageField(
        "Article cover image",
        upload_to="articles/",
        blank=True,
        null=True,
    )
    cover_caption = models.CharField(
        "Cover caption",
        max_length=300,
        blank=True,
    )

    published_at = models.DateTimeField("Publication date", null=True, blank=True)
    created_at = models.DateTimeField("Created at", auto_now_add=True)
    updated_at = models.DateTimeField("Updated at", auto_now=True)

    class Meta:
        ordering = ["-published_at", "-created_at"]
        verbose_name = "Article"
        verbose_name_plural = "Articles"

    def save(self, *args, **kwargs):
        if self.status == self.Status.PUBLISHED and self.published_at is None:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self):
        en_translation = self.translations.filter(language="en").first()
        if en_translation:
            return en_translation.title

        ru_translation = self.translations.filter(language="ru").first()
        if ru_translation:
            return ru_translation.title

        any_translation = self.translations.first()
        if any_translation:
            return any_translation.title

        return f"Article #{self.pk}"

    def get_translation(self, language="ru"):
        return self.translations.filter(language=language).first()


class ArticleTranslation(models.Model):
    article = models.ForeignKey(
        Article,
        on_delete=models.CASCADE,
        related_name="translations",
        verbose_name="Article",
    )
    language = models.CharField(
        "Language",
        max_length=2,
        choices=LANGUAGE_CHOICES,
    )

    title = models.CharField("Title", max_length=250)
    slug = models.SlugField("Slug", max_length=260)
    subtitle = models.CharField("Subtitle", max_length=300, blank=True)
    excerpt = models.TextField("Excerpt", blank=True)
    body = models.TextField("Article body")

    seo_title = models.CharField("SEO title", max_length=250, blank=True)
    seo_description = models.TextField("SEO description", blank=True)

    class Meta:
        unique_together = [
            ("article", "language"),
            ("language", "slug"),
        ]
        verbose_name = "Article translation"
        verbose_name_plural = "Article translations"

    def __str__(self):
        return f"{self.title} [{self.language}]"