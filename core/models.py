from django.db import models


LANGUAGE_CHOICES = [
    ("ru", "Russian"),
    ("en", "English"),
    ("lt", "Lithuanian"),
]


class Issue(models.Model):
    is_current = models.BooleanField("Current issue", default=False)

    cover_image = models.ImageField(
        "Issue cover image",
        upload_to="issues/",
        blank=True,
        null=True,
    )

    published_at = models.DateTimeField("Publication date", null=True, blank=True)
    created_at = models.DateTimeField("Created at", auto_now_add=True)
    updated_at = models.DateTimeField("Updated at", auto_now=True)

    class Meta:
        ordering = ["-published_at", "-created_at"]
        verbose_name = "Issue"
        verbose_name_plural = "Issues"

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

        return f"Issue #{self.pk}"

    def get_translation(self, language="ru"):
        return self.translations.filter(language=language).first()


class IssueTranslation(models.Model):
    issue = models.ForeignKey(
        Issue,
        on_delete=models.CASCADE,
        related_name="translations",
        verbose_name="Issue",
    )
    language = models.CharField(
        "Language",
        max_length=2,
        choices=LANGUAGE_CHOICES,
    )
    title = models.CharField("Title", max_length=250)
    slug = models.SlugField("Slug", max_length=260)
    description = models.TextField("Description", blank=True)

    class Meta:
        unique_together = [
            ("issue", "language"),
            ("language", "slug"),
        ]
        verbose_name = "Issue translation"
        verbose_name_plural = "Issue translations"

    def __str__(self):
        return f"{self.title} [{self.language}]"


class Subscriber(models.Model):
    email = models.EmailField("Email", unique=True)
    language = models.CharField(
        "Language",
        max_length=2,
        choices=LANGUAGE_CHOICES,
        default="ru",
    )
    is_active = models.BooleanField("Active", default=True)
    created_at = models.DateTimeField("Created at", auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Subscriber"
        verbose_name_plural = "Subscribers"

    def __str__(self):
        return self.email