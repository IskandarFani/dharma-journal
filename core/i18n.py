UI_TEXT = {
    "ru": {
        "about": "О проекте",
        "journal_label": "Buddhist cultural journal",
        "site_subtitle": "Сдержанный журнал о буддийской культуре, практике, текстах, людях и повседневной Дхарме.",

        "nav_living_day": "Живой день",
        "nav_coffee_portrait": "Портрет с кофе",
        "nav_treasury": "Сокровищница",
        "nav_masters": "Мастера",
        "nav_silence": "Тишина и красота",

        "featured": "Избранное",
        "no_featured_title": "Пока нет главного материала",
        "no_featured_text": "Создай опубликованную статью в админке и поставь галочку “Главный материал”.",

        "materials": "Материалы",
        "add_more_articles": "Добавь ещё несколько опубликованных статей",
        "add_more_articles_text": "Они появятся в этой колонке автоматически.",

        "latest": "Последнее",
        "category": "Рубрика",
        "author": "Автор",
        "editorial": "Редакция",

        "current_issue": "Текущий выпуск",
        "issue_title": "Выпуск №1: Тишина в городе",
        "issue_text": "Первый выпуск посвящён тому, как сохранять ясность, внимание и мягкость внутри современной городской жизни.",
        "read_issue": "Читать выпуск",

        "subscription": "Подписка",
        "subscribe_title": "Получать новые материалы",
        "email_placeholder": "Ваш email",
        "subscribe_button": "Подписаться",

        "related": "Ещё по теме",
        "no_related": "Пока нет других материалов в этой рубрике.",
        "no_published": "Пока нет опубликованных материалов.",
    },

    "en": {
        "about": "About",
        "journal_label": "Buddhist cultural journal",
        "site_subtitle": "A restrained journal about Buddhist culture, practice, texts, people, and everyday Dharma.",

        "nav_living_day": "Living Day",
        "nav_coffee_portrait": "Portrait with Coffee",
        "nav_treasury": "Treasury",
        "nav_masters": "Masters",
        "nav_silence": "Silence and Beauty",

        "featured": "Featured",
        "no_featured_title": "No featured article yet",
        "no_featured_text": "Create a published article in the admin panel and mark it as featured.",

        "materials": "Articles",
        "add_more_articles": "Add a few more published articles",
        "add_more_articles_text": "They will appear in this column automatically.",

        "latest": "Latest",
        "category": "Category",
        "author": "Author",
        "editorial": "Editorial Team",

        "current_issue": "Current Issue",
        "issue_title": "Issue No. 1: Silence in the City",
        "issue_text": "The first issue is devoted to preserving clarity, attention, and gentleness within modern urban life.",
        "read_issue": "Read the Issue",

        "subscription": "Subscription",
        "subscribe_title": "Receive new articles",
        "email_placeholder": "Your email",
        "subscribe_button": "Subscribe",

        "related": "Related Articles",
        "no_related": "There are no other articles in this category yet.",
        "no_published": "There are no published articles yet.",
    },

    "lt": {
        "about": "Apie projektą",
        "journal_label": "Buddhist cultural journal",
        "site_subtitle": "Santūrus žurnalas apie budistinę kultūrą, praktiką, tekstus, žmones ir kasdienę Dharmą.",

        "nav_living_day": "Gyvoji diena",
        "nav_coffee_portrait": "Portretas su kava",
        "nav_treasury": "Lobynas",
        "nav_masters": "Mokytojai",
        "nav_silence": "Tyla ir grožis",

        "featured": "Svarbiausia",
        "no_featured_title": "Pagrindinio straipsnio dar nėra",
        "no_featured_text": "Sukurk publikuotą straipsnį administravimo skydelyje ir pažymėk jį kaip pagrindinį.",

        "materials": "Straipsniai",
        "add_more_articles": "Pridėk dar kelis publikuotus straipsnius",
        "add_more_articles_text": "Jie automatiškai atsiras šiame stulpelyje.",

        "latest": "Naujausia",
        "category": "Rubrika",
        "author": "Autorius",
        "editorial": "Redakcija",

        "current_issue": "Dabartinis numeris",
        "issue_title": "Numeris Nr. 1: Tyla mieste",
        "issue_text": "Pirmasis numeris skirtas aiškumui, dėmesiui ir švelnumui šiuolaikiniame miesto gyvenime.",
        "read_issue": "Skaityti numerį",

        "subscription": "Prenumerata",
        "subscribe_title": "Gauti naujus straipsnius",
        "email_placeholder": "Jūsų el. paštas",
        "subscribe_button": "Prenumeruoti",

        "related": "Susiję straipsniai",
        "no_related": "Šioje rubrikoje kol kas nėra kitų straipsnių.",
        "no_published": "Kol kas nėra publikuotų straipsnių.",
    },
}


def get_ui_text(language="ru"):
    return UI_TEXT.get(language, UI_TEXT["ru"])