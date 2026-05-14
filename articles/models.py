from django.db import models
from django.utils import timezone


LANGUAGE_CHOICES = [
    ("ru", "Русский"),
    ("en", "English"),
    ("lt", "Lietuvių"),
]


class Category(models.Model):
    order = models.PositiveIntegerField("Порядок", default=100)
    is_active = models.BooleanField("Активна", default=True)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "Рубрика"
        verbose_name_plural = "Рубрики"

    def __str__(self):
        ru_translation = self.translations.filter(language="ru").first()
        if ru_translation:
            return ru_translation.title
        return f"Рубрика #{self.pk}"

    def get_translation(self, language="ru"):
        return self.translations.filter(language=language).first()


class CategoryTranslation(models.Model):
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="translations",
        verbose_name="Рубрика",
    )
    language = models.CharField(
        "Язык",
        max_length=2,
        choices=LANGUAGE_CHOICES,
    )
    title = models.CharField("Название", max_length=200)
    slug = models.SlugField("URL-имя", max_length=220)
    description = models.TextField("Описание", blank=True)

    class Meta:
        unique_together = [
            ("category", "language"),
            ("language", "slug"),
        ]
        verbose_name = "Перевод рубрики"
        verbose_name_plural = "Переводы рубрик"

    def __str__(self):
        return f"{self.title} [{self.language}]"


class Author(models.Model):
    name = models.CharField("Имя", max_length=200)
    slug = models.SlugField("URL-имя", max_length=220, unique=True)
    bio = models.TextField("Биография", blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Автор"
        verbose_name_plural = "Авторы"

    def __str__(self):
        return self.name


class Article(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Черновик"
        PUBLISHED = "published", "Опубликовано"

    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="articles",
        verbose_name="Рубрика",
    )
    author = models.ForeignKey(
        Author,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="articles",
        verbose_name="Автор",
    )

    status = models.CharField(
        "Статус",
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    is_featured = models.BooleanField("Главный материал", default=False)

    published_at = models.DateTimeField("Дата публикации", null=True, blank=True)
    created_at = models.DateTimeField("Создано", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлено", auto_now=True)

    class Meta:
        ordering = ["-published_at", "-created_at"]
        verbose_name = "Статья"
        verbose_name_plural = "Статьи"

    def save(self, *args, **kwargs):
        if self.status == self.Status.PUBLISHED and self.published_at is None:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self):
        ru_translation = self.translations.filter(language="ru").first()
        if ru_translation:
            return ru_translation.title
        return f"Статья #{self.pk}"

    def get_translation(self, language="ru"):
        return self.translations.filter(language=language).first()


class ArticleTranslation(models.Model):
    article = models.ForeignKey(
        Article,
        on_delete=models.CASCADE,
        related_name="translations",
        verbose_name="Статья",
    )
    language = models.CharField(
        "Язык",
        max_length=2,
        choices=LANGUAGE_CHOICES,
    )

    title = models.CharField("Заголовок", max_length=250)
    slug = models.SlugField("URL-имя", max_length=260)
    subtitle = models.CharField("Подзаголовок", max_length=300, blank=True)
    excerpt = models.TextField("Краткое описание", blank=True)
    body = models.TextField("Текст статьи")

    seo_title = models.CharField("SEO title", max_length=250, blank=True)
    seo_description = models.TextField("SEO description", blank=True)

    class Meta:
        unique_together = [
            ("article", "language"),
            ("language", "slug"),
        ]
        verbose_name = "Перевод статьи"
        verbose_name_plural = "Переводы статей"

    def __str__(self):
        return f"{self.title} [{self.language}]"