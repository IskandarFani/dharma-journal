import json
import logging
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from articles.models import Article, ArticleImage, ArticleTranslation, Author, Category


logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"
TELEGRAM_FILE_API = "https://api.telegram.org/file/bot{token}/{file_path}"
MAX_MESSAGE_LENGTH = 3900
SESSION_FILE = ".editorial_bot_sessions.json"

LANGUAGE_LABELS = {
    "ru": "Russian",
    "en": "English",
    "lt": "Lithuanian",
}

CYRILLIC_MAP = {
    "а": "a",
    "б": "b",
    "в": "v",
    "г": "g",
    "д": "d",
    "е": "e",
    "ё": "e",
    "ж": "zh",
    "з": "z",
    "и": "i",
    "й": "y",
    "к": "k",
    "л": "l",
    "м": "m",
    "н": "n",
    "о": "o",
    "п": "p",
    "р": "r",
    "с": "s",
    "т": "t",
    "у": "u",
    "ф": "f",
    "х": "h",
    "ц": "c",
    "ч": "ch",
    "ш": "sh",
    "щ": "sch",
    "ъ": "",
    "ы": "y",
    "ь": "",
    "э": "e",
    "ю": "yu",
    "я": "ya",
}


@dataclass
class Session:
    mode: str = "idle"
    waiting_for: str = ""
    data: dict = field(default_factory=dict)


class TelegramClient:
    def __init__(self, token):
        self.token = token

    def call(self, method, payload=None, timeout=15):
        url = TELEGRAM_API.format(token=self.token, method=method)
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST" if payload is not None else "GET",
        )

        with urllib.request.urlopen(request, timeout=timeout) as response:
            result = json.loads(response.read().decode("utf-8"))

        if not result.get("ok"):
            raise RuntimeError(result)

        return result["result"]

    def get_updates(self, offset=None):
        payload = {"timeout": 25, "allowed_updates": ["message"]}
        if offset is not None:
            payload["offset"] = offset
        return self.call("getUpdates", payload, timeout=35)

    def send_message(self, chat_id, text):
        for chunk in split_message(text):
            self.call(
                "sendMessage",
                {
                    "chat_id": chat_id,
                    "text": chunk,
                    "disable_web_page_preview": True,
                },
                timeout=5,
            )

    def get_file(self, file_id):
        return self.call("getFile", {"file_id": file_id}, timeout=10)

    def download_file(self, file_path):
        url = TELEGRAM_FILE_API.format(token=self.token, file_path=file_path)
        with urllib.request.urlopen(url, timeout=60) as response:
            return response.read()


def split_message(text):
    if len(text) <= MAX_MESSAGE_LENGTH:
        return [text]

    chunks = []
    rest = text
    while rest:
        chunk = rest[:MAX_MESSAGE_LENGTH]
        split_at = chunk.rfind("\n")
        if split_at < 1000:
            split_at = len(chunk)
        chunks.append(rest[:split_at])
        rest = rest[split_at:].lstrip()
    return chunks


def transliterate(value):
    return "".join(CYRILLIC_MAP.get(char, char) for char in value.lower())


def normalize(value):
    value = value.casefold().replace("ё", "е")
    value = re.sub(r"[^\w\sа-яa-z0-9]", " ", value, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", value).strip()


def edit_distance(left, right, limit=2):
    if abs(len(left) - len(right)) > limit:
        return limit + 1

    previous = list(range(len(right) + 1))
    for left_index, left_char in enumerate(left, start=1):
        current = [left_index]
        row_min = current[0]
        for right_index, right_char in enumerate(right, start=1):
            cost = 0 if left_char == right_char else 1
            current.append(
                min(
                    previous[right_index] + 1,
                    current[right_index - 1] + 1,
                    previous[right_index - 1] + cost,
                )
            )
            row_min = min(row_min, current[-1])
        if row_min > limit:
            return limit + 1
        previous = current
    return previous[-1]


def fuzzy_equals(value, candidates, limit=1):
    text = normalize(value)
    if not text:
        return False

    for candidate in candidates:
        candidate = normalize(candidate)
        if text == candidate:
            return True
        if len(text) >= 4 and edit_distance(text, candidate, limit=limit) <= limit:
            return True
    return False


def contains_fuzzy_word(value, candidates, limit=1):
    words = normalize(value).split()
    for word in words:
        if fuzzy_equals(word, candidates, limit=limit):
            return True
    return False


def is_yes(value):
    return fuzzy_equals(value, {"да", "yes", "ок", "okay"}, limit=1)


def is_no(value):
    return fuzzy_equals(value, {"нет", "no", "не надо", "отмена", "отбой", "стоп", "cancel"}, limit=1)


def is_publish_command(value):
    return fuzzy_equals(value, {"опубликовать", "опубликуй", "публикуй", "публикуем", "в публикацию"}, limit=2)


def is_draft_command(value):
    return fuzzy_equals(value, {"черновик", "сохранить черновик", "сохрани черновик", "в черновик", "пока черновик"}, limit=2)


def is_done_command(value):
    return fuzzy_equals(value, {"готово", "все", "всё", "это все", "это всё", "закончила", "закончил", "проверь", "посмотри"}, limit=2)


def make_slug(title, language, current_translation=None):
    base = slugify(transliterate(title)) or "article"
    slug = base[:220].strip("-") or "article"
    candidate = slug
    counter = 2

    queryset = ArticleTranslation.objects.filter(language=language, slug=candidate)
    if current_translation is not None:
        queryset = queryset.exclude(pk=current_translation.pk)

    while queryset.exists():
        suffix = f"-{counter}"
        candidate = f"{slug[:260 - len(suffix)]}{suffix}"
        queryset = ArticleTranslation.objects.filter(language=language, slug=candidate)
        if current_translation is not None:
            queryset = queryset.exclude(pk=current_translation.pk)
        counter += 1

    return candidate


def get_editorial_author():
    return Author.objects.get_or_create(slug="editorial", defaults={"name": "Editorial"})[0]


def get_categories():
    return Category.objects.filter(is_active=True).prefetch_related("translations").order_by("order", "id")


def category_title(category):
    translation = category.get_translation("ru") or category.translations.first()
    return translation.title if translation else str(category)


def article_title(article):
    translation = article.get_translation("ru") or article.translations.first()
    return translation.title if translation else str(article)


def article_url(translation):
    return f"https://sanghaya.art/{translation.language}/articles/{translation.slug}/"


def parse_language(text):
    value = normalize(text)
    if re.search(r"\b(en|eng|english|англ|англий)", value) or contains_fuzzy_word(value, {"английский", "английском"}, limit=2):
        return "en"
    if re.search(r"\b(lt|lit|lithuanian|литов)", value) or contains_fuzzy_word(value, {"литовский", "литовском"}, limit=2):
        return "lt"
    if re.search(r"\b(ru|rus|russian|рус)", value) or contains_fuzzy_word(value, {"русский", "русском"}, limit=2):
        return "ru"
    return ""


def extract_labeled_fields(text):
    fields = {}
    labels = {
        "title": r"(?:заголовок|название|title)",
        "subtitle": r"(?:подзаголовок|subtitle)",
        "excerpt": r"(?:анонс|описание|лид|excerpt|description)",
        "category": r"(?:рубрика|категория|раздел|category)",
        "language": r"(?:язык|language)",
        "body": r"(?:текст|статья|body)",
    }
    label_pattern = "|".join(f"(?P<{name}>{pattern})" for name, pattern in labels.items())
    pattern = re.compile(rf"^\s*(?:{label_pattern})\s*[:\-]\s*(.*)$", re.IGNORECASE | re.MULTILINE)
    matches = list(pattern.finditer(text))

    for index, match in enumerate(matches):
        field_name = next(name for name in labels if match.group(name) is not None)
        value_start = match.start(7) if False else match.end()
        value = match.group(match.lastindex).strip()

        if field_name == "body":
            next_start = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            value = text[match.end() : next_start].strip() or value

        if value:
            fields[field_name] = value

    return fields


def infer_title_and_body(text):
    clean_lines = [line.strip() for line in text.strip().splitlines() if line.strip()]
    clean_lines = [
        line
        for line in clean_lines
        if normalize(line) not in {"новая статья", "создать статью", "хочу создать статью", "опубликовать статью"}
    ]

    if not clean_lines:
        return "", ""

    first_line = clean_lines[0]
    rest = "\n\n".join(clean_lines[1:]).strip()
    if len(first_line) <= 140 and rest:
        return first_line, rest
    if len(text) > 500:
        return "", text.strip()
    return "", ""


class EditorBot:
    def __init__(self, client, allowed_user_ids):
        self.client = client
        self.allowed_user_ids = set(allowed_user_ids)
        self.sessions = self.load_sessions()

    def run(self):
        offset = self.drop_stale_updates()
        while True:
            try:
                updates = self.client.get_updates(offset=offset)
                for update in updates:
                    offset = update["update_id"] + 1
                    started_at = time.monotonic()
                    try:
                        self.handle_update(update)
                    except Exception:
                        logger.exception("Failed to handle Telegram update")
                        chat_id = update.get("message", {}).get("chat", {}).get("id")
                        if chat_id:
                            self.client.send_message(chat_id, "Я запутался в этом сообщении. Напишите «отмена» и начнём заново.")
                    finally:
                        elapsed = time.monotonic() - started_at
                        if elapsed > 2:
                            logger.warning("Slow Telegram update handling: %.2fs", elapsed)
            except (urllib.error.URLError, TimeoutError, RuntimeError) as exc:
                logger.warning("Telegram polling error: %s", exc)
                time.sleep(3)

    def session_path(self):
        return Path(settings.BASE_DIR) / SESSION_FILE

    def load_sessions(self):
        path = self.session_path()
        if not path.exists():
            return {}
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            return {int(user_id): Session(**data) for user_id, data in raw.items()}
        except Exception:
            logger.exception("Could not load bot sessions")
            return {}

    def save_sessions(self):
        raw = {
            str(user_id): {"mode": session.mode, "waiting_for": session.waiting_for, "data": session.data}
            for user_id, session in self.sessions.items()
        }
        self.session_path().write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")

    def session(self, user_id):
        session = self.sessions.setdefault(user_id, Session())
        self.save_sessions()
        return session

    def set_session(self, user_id, session):
        self.sessions[user_id] = session
        self.save_sessions()

    def reset_session(self, user_id):
        self.sessions[user_id] = Session()
        self.save_sessions()

    def drop_stale_updates(self):
        try:
            updates = self.client.call("getUpdates", {"offset": -1, "timeout": 0, "allowed_updates": ["message"]}, timeout=5)
        except Exception:
            logger.exception("Could not drop stale Telegram updates")
            return None
        return updates[-1]["update_id"] + 1 if updates else None

    def is_allowed(self, user_id):
        return user_id in self.allowed_user_ids

    def handle_update(self, update):
        message = update.get("message")
        if not message:
            return

        user_id = message["from"]["id"]
        chat_id = message["chat"]["id"]
        if not self.is_allowed(user_id):
            self.client.send_message(chat_id, "Доступ закрыт.")
            return

        text = message.get("text", "").strip()
        if text.startswith("/start") or normalize(text) in {"помощь", "help", "/help"}:
            self.reset_session(user_id)
            self.client.send_message(chat_id, self.help_text())
            return

        if normalize(text) in {"отмена", "сброс", "стоп", "cancel", "/cancel"}:
            self.reset_session(user_id)
            self.client.send_message(chat_id, "Хорошо, сбросила текущий черновик. Можно начать заново: «новая статья».")
            return

        photos = message.get("photo", [])
        if photos:
            self.handle_photo(user_id, chat_id, photos[-1]["file_id"])
            return

        self.handle_text(user_id, chat_id, text)

    def help_text(self):
        return (
            "Я редакторский помощник Sanghaya. Кнопок нет, можно писать обычными фразами.\n\n"
            "Примеры:\n"
            "«Новая статья»\n"
            "«Заголовок: Ароматы Дхармы»\n"
            "«Рубрика: Сокровищница»\n"
            "«Текст: ...»\n"
            "«Сохрани черновик»\n"
            "«Опубликуй»\n\n"
            "Также можно написать «черновики», «последние статьи» или «отмена»."
        )

    def handle_text(self, user_id, chat_id, text):
        lowered = normalize(text)
        session = self.session(user_id)

        if lowered in {"черновики", "покажи черновики", "drafts"}:
            self.list_articles(chat_id, Article.objects.filter(status=Article.Status.DRAFT), "Черновики")
            return

        if lowered in {"последние", "последние статьи", "latest"}:
            self.list_articles(chat_id, Article.objects.all(), "Последние статьи")
            return

        if session.mode == "confirm_publish":
            if is_publish_command(text):
                self.create_article(user_id, chat_id, Article.Status.PUBLISHED)
            elif is_draft_command(text):
                self.create_article(user_id, chat_id, Article.Status.DRAFT)
            elif is_yes(text):
                self.client.send_message(chat_id, "Подтвердите точнее: «опубликовать» или «сохранить черновик».")
            elif is_no(text):
                session.mode = "draft"
                session.waiting_for = "body_more"
                self.set_session(user_id, session)
                self.client.send_message(chat_id, "Хорошо, не публикую. Можно прислать правки или продолжение текста.")
            else:
                session.mode = "draft"
                session.waiting_for = "body_more"
                existing = session.data.get("body", "")
                session.data["body"] = f"{existing}\n\n{text}".strip() if existing else text
                self.set_session(user_id, session)
                self.client.send_message(
                    chat_id,
                    "Добавила это к тексту статьи. Можно прислать ещё продолжение. Когда текст закончен, напишите «готово».",
                )
            return

        if is_publish_command(text):
            if session.mode != "draft":
                self.client.send_message(chat_id, "Сейчас нет готового черновика. Сначала напишите «новая статья».")
                return
            self.confirm_or_ask_next(user_id, chat_id, want_publish=True)
            return

        if is_draft_command(text):
            if session.mode != "draft":
                self.client.send_message(chat_id, "Сейчас нет готового черновика. Сначала напишите «новая статья».")
                return
            self.confirm_or_ask_next(user_id, chat_id, want_publish=False)
            return

        if is_done_command(text):
            if session.mode != "draft":
                self.client.send_message(chat_id, "Сейчас нет открытой статьи. Если хотите начать, напишите «новая статья».")
                return
            self.show_preview(user_id, chat_id)
            return

        starts_new = any(phrase in lowered for phrase in ["новая статья", "создать статью", "хочу статью", "опубликовать статью"])
        if starts_new and session.mode != "draft":
            session = Session(mode="draft", waiting_for="", data={"language": "ru"})
            self.set_session(user_id, session)

        if session.mode != "draft":
            self.client.send_message(
                chat_id,
                "Я могу помочь со статьёй. Напишите «новая статья», а дальше присылайте заголовок, рубрику, текст и фото обычными сообщениями.",
            )
            return

        self.absorb_text(session, text)
        self.set_session(user_id, session)
        self.ask_next(user_id, chat_id)

    def absorb_text(self, session, text):
        fields = extract_labeled_fields(text)

        language = fields.get("language") or parse_language(text)
        if language:
            session.data["language"] = language

        if "title" in fields:
            session.data["title"] = fields["title"]
        if "subtitle" in fields:
            session.data["subtitle"] = fields["subtitle"]
        if "excerpt" in fields:
            session.data["excerpt"] = fields["excerpt"]
        if "body" in fields:
            session.data["body"] = fields["body"]
        if "category" in fields:
            category = self.find_category(fields["category"])
            if category:
                session.data["category_id"] = category.pk

        if session.waiting_for == "category":
            category = self.find_category(text)
            if category:
                session.data["category_id"] = category.pk
                session.waiting_for = ""
                return

        if session.waiting_for == "body" and text:
            existing = session.data.get("body", "")
            session.data["body"] = f"{existing}\n\n{text.strip()}".strip() if existing else text.strip()
            session.waiting_for = "body_more"
            return

        if session.waiting_for == "body_more" and text:
            existing = session.data.get("body", "")
            session.data["body"] = f"{existing}\n\n{text.strip()}".strip() if existing else text.strip()
            return

        if session.waiting_for in {"title", "excerpt"} and text:
            session.data[session.waiting_for] = text.strip()
            session.waiting_for = ""
            return

        title, body = infer_title_and_body(text)
        if title and "title" not in session.data:
            session.data["title"] = title
        if body and "body" not in session.data:
            session.data["body"] = body

        if len(text) > 500 and "body" not in session.data:
            session.data["body"] = text.strip()

    def handle_photo(self, user_id, chat_id, file_id):
        session = self.session(user_id)
        if session.mode != "draft":
            session = Session(mode="draft", data={"language": "ru"})
        photo_file_ids = session.data.setdefault("photo_file_ids", [])
        photo_file_ids.append(file_id)
        session.data["photo_file_id"] = photo_file_ids[0]
        self.set_session(user_id, session)
        self.client.send_message(chat_id, f"Фото приняла. В статье сейчас фото: {len(photo_file_ids)}.")
        self.ask_next(user_id, chat_id)

    def ask_next(self, user_id, chat_id):
        session = self.session(user_id)
        missing = self.missing_fields(session)

        if not missing:
            if session.waiting_for == "body_more":
                self.set_session(user_id, session)
                self.client.send_message(
                    chat_id,
                    "Текст приняла. Можно прислать ещё продолжение. Когда статья закончена, напишите «готово».",
                )
            else:
                self.show_preview(user_id, chat_id)
            return

        field_name = missing[0]
        session.waiting_for = field_name
        self.set_session(user_id, session)

        if field_name == "category":
            self.client.send_message(chat_id, self.category_question())
        elif field_name == "title":
            self.client.send_message(chat_id, "Какой заголовок у статьи?")
        elif field_name == "body":
            self.client.send_message(
                chat_id,
                "Пришлите текст статьи. Можно одним большим сообщением или несколькими частями. Когда закончите, напишите «готово».",
            )
        elif field_name == "excerpt":
            self.client.send_message(chat_id, "Пришлите короткий анонс. Если не нужен, напишите «без анонса».")

    def show_preview(self, user_id, chat_id):
        session = self.session(user_id)
        missing = self.missing_fields(session)
        if missing:
            self.ask_next(user_id, chat_id)
            return
        session.mode = "confirm_publish"
        session.waiting_for = ""
        self.set_session(user_id, session)
        self.client.send_message(chat_id, self.preview_text(session))

    def confirm_or_ask_next(self, user_id, chat_id, want_publish):
        session = self.session(user_id)
        missing = self.missing_fields(session)
        if missing:
            self.ask_next(user_id, chat_id)
            return
        status = Article.Status.PUBLISHED if want_publish else Article.Status.DRAFT
        self.create_article(user_id, chat_id, status)

    def missing_fields(self, session):
        missing = []
        for field_name in ["category", "title", "body"]:
            key = "category_id" if field_name == "category" else field_name
            if not session.data.get(key):
                missing.append(field_name)
        return missing

    def preview_text(self, session):
        data = session.data
        category = Category.objects.get(pk=data["category_id"])
        photo_file_ids = data.get("photo_file_ids") or ([data["photo_file_id"]] if data.get("photo_file_id") else [])
        photo = str(len(photo_file_ids)) if photo_file_ids else "нет"
        excerpt = data.get("excerpt") or "нет"
        return (
            "Черновик готов.\n\n"
            f"Язык: {LANGUAGE_LABELS.get(data.get('language', 'ru'))}\n"
            f"Рубрика: {category_title(category)}\n"
            f"Заголовок: {data['title']}\n"
            f"Анонс: {excerpt}\n"
            f"Фото: {photo}\n"
            f"Текст: {len(data['body'])} символов\n\n"
            "Напишите «опубликовать» или «сохранить черновик»."
        )

    def category_question(self):
        lines = ["В какую рубрику поставить статью? Можно написать название или номер:"]
        for index, category in enumerate(get_categories(), start=1):
            lines.append(f"{index}. {category_title(category)}")
        return "\n".join(lines)

    def find_category(self, value):
        value = normalize(value)
        categories = list(get_categories())

        if value.isdigit():
            index = int(value) - 1
            if 0 <= index < len(categories):
                return categories[index]

        for category in categories:
            title = normalize(category_title(category))
            if value == title or value in title or title in value:
                return category
            title_words = title.split()
            value_words = value.split()
            if value_words and all(any(edit_distance(word, title_word, limit=2) <= 2 for title_word in title_words) for word in value_words):
                return category

        aliases = {
            "сокровищ": "treasury",
            "сокровиш": "treasury",
            "мастер": "masters",
            "мастера": "masters",
            "мастерская": "dharma workshop",
            "дхарма": "dharma workshop",
            "живой": "living day",
            "день": "living day",
            "житей": "everyday life",
            "повседнев": "everyday life",
            "жизнь": "everyday life",
        }
        for alias, target in aliases.items():
            if alias in value or contains_fuzzy_word(value, {alias}, limit=2):
                for category in categories:
                    if target in normalize(category_title(category)):
                        return category
        return None

    @transaction.atomic
    def create_article(self, user_id, chat_id, status):
        session = self.session(user_id)
        data = session.data
        category = Category.objects.get(pk=data["category_id"])
        language = data.get("language", "ru")
        excerpt = data.get("excerpt", "")
        if normalize(excerpt) in {"без анонса", "не нужен", "нет"}:
            excerpt = ""

        article = Article.objects.create(
            category=category,
            author=get_editorial_author(),
            status=status,
            published_at=timezone.now() if status == Article.Status.PUBLISHED else None,
        )
        translation = ArticleTranslation.objects.create(
            article=article,
            language=language,
            title=data["title"],
            slug=make_slug(data["title"], language),
            subtitle=data.get("subtitle", ""),
            excerpt=excerpt,
            body=data["body"],
            seo_title=data["title"],
            seo_description=excerpt,
        )

        photo_file_ids = data.get("photo_file_ids") or ([data["photo_file_id"]] if data.get("photo_file_id") else [])
        if photo_file_ids:
            self.attach_photos(article, photo_file_ids, translation.slug)
            article.save(update_fields=["cover_image", "updated_at"])

        self.reset_session(user_id)
        label = "опубликована" if status == Article.Status.PUBLISHED else "сохранена как черновик"
        self.client.send_message(chat_id, f"Готово, статья {label}.\n\n{translation.title}\n{article_url(translation)}")

    def attach_photos(self, article, file_ids, slug):
        for index, file_id in enumerate(file_ids, start=1):
            image_name, content = self.download_photo(file_id, slug, index)
            if index == 1:
                article.cover_image.save(image_name, ContentFile(content), save=False)
            ArticleImage.objects.create(
                article=article,
                image=ContentFile(content, name=image_name),
                order=index,
            )

    def download_photo(self, file_id, slug, index):
        file_data = self.client.get_file(file_id)
        file_path = file_data["file_path"]
        extension = Path(file_path).suffix or ".jpg"
        content = self.client.download_file(file_path)
        return f"{slug}-{index}{extension}", content

    def list_articles(self, chat_id, queryset, title):
        articles = queryset.prefetch_related("translations").order_by("-published_at", "-created_at")[:10]
        lines = [title]
        for article in articles:
            status = "опубликована" if article.status == Article.Status.PUBLISHED else "черновик"
            lines.append(f"#{article.pk} — {article_title(article)} ({status})")
        if len(lines) == 1:
            lines.append("Пока пусто.")
        self.client.send_message(chat_id, "\n".join(lines))


class Command(BaseCommand):
    help = "Runs the private Telegram editorial bot."

    def handle(self, *args, **options):
        token = getattr(settings, "TELEGRAM_EDITOR_BOT_TOKEN", "")
        allowed_user_ids = getattr(settings, "TELEGRAM_EDITOR_ALLOWED_USER_IDS", [])

        if not token:
            raise CommandError("TELEGRAM_EDITOR_BOT_TOKEN is not configured.")

        if not allowed_user_ids:
            raise CommandError("TELEGRAM_EDITOR_ALLOWED_USER_IDS is empty.")

        logging.basicConfig(level=logging.INFO)
        self.stdout.write(self.style.SUCCESS("Starting Sanghaya editorial bot."))
        EditorBot(TelegramClient(token), allowed_user_ids).run()
