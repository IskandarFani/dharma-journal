from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path

from core.views import home
from articles.views import article_detail, category_detail


urlpatterns = [
    path("admin/", admin.site.urls),

    path("", home, {"language": "ru"}, name="home_default"),

    path("<str:language>/", home, name="home"),
    path("<str:language>/articles/<slug:slug>/", article_detail, name="article_detail"),
    path("<str:language>/categories/<slug:slug>/", category_detail, name="category_detail"),
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)