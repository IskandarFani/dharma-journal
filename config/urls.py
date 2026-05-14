from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path

from articles.views import article_detail, category_detail
from core.views import about, home, issue_detail, subscribe


admin.site.site_header = "Dharma Journal Administration"
admin.site.site_title = "Dharma Journal Admin"
admin.site.index_title = "Editorial dashboard"


urlpatterns = [
    path("admin/", admin.site.urls),

    path("", home, {"language": "ru"}, name="home_default"),

    path("<str:language>/", home, name="home"),
    path("<str:language>/about/", about, name="about"),
    path("<str:language>/subscribe/", subscribe, name="subscribe"),
    path("<str:language>/issues/<slug:slug>/", issue_detail, name="issue_detail"),
    path("<str:language>/articles/<slug:slug>/", article_detail, name="article_detail"),
    path("<str:language>/categories/<slug:slug>/", category_detail, name="category_detail"),
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)