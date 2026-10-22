
import os
import sqlite3
import logging
from contextlib import contextmanager

import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton


# =========================================================
# 1. الإعدادات الأساسية
# =========================================================

TOKEN = "8621524247:AAFgeDxavRVzFbt1KeqYHXRPIvVAKPdTznA"


if not TOKEN:
    raise RuntimeError(
        "يجب إضافة رمز البوت في متغير البيئة BOT_TOKEN."
    )

# ضع أرقام حسابات المشرفين في Render، مفصولة بفواصل.
# مثال: ADMIN_IDS=123456789,987654321
ADMIN_IDS = {
    int(value.strip())
    for value in os.getenv("ADMIN_IDS", "").split(",")
    if value.strip().isdigit()
}

# يفضّل وضع قاعدة البيانات على قرص دائم في Render.
DB_PATH = os.getenv("DATABASE_PATH", "bot_data.db")

bot = telebot.TeleBot(TOKEN, threaded=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# =========================================================
# 2. مواد المعهد
# =========================================================

SUBJECTS = [
    "علوم القرآن",
    "التجويد",
    "صحيح البخاري",
    "رياض الصالحين",
    "الأربعين النووية",
    "السيرة النبوية",
    "السنة والتحديات",
    "قصة الحديث",
    "تراجم العلماء",
    "الكواكب الزاهرة",
    "البيقونية",
    "التقريب والتيسير",
    "الفقه",
    "النحو",
    "الصرف",
    "العقيدة",
    "آداب الطالب",
    "ألفية السيوطي",
]

SECTIONS = {
    "text": "📄 الملفات النصية",
    "audio": "🎧 الملفات الصوتية",
    "video": "🎥 الملفات المرئية",
    "links": "🔗 الروابط الإثرائية",
}


# =========================================================
# 3. قاعدة البيانات
# =========================================================

@contextmanager
def db_connection():
    connection = sqlite3.connect(DB_PATH, timeout=30)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def initialize_database():
    with db_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS content (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject_id INTEGER NOT NULL,
                section TEXT NOT NULL,
                content_type TEXT NOT NULL,
                text_content TEXT,
                file_id TEXT,
                caption TEXT,
                created_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    logger.info("Database initialized.")


initialize_database()

# حالة إضافة المحتوى لكل مشرف.
# هذه الحالات مؤقتة وتُمسح عند إعادة تشغيل البوت.
admin_states = {}


def is_admin(user_id):
    return user_id in ADMIN_IDS


def get_content(subject_id, section):
    with db_connection() as conn:
        return conn.execute(
            """
            SELECT * FROM content
            WHERE subject_id = ? AND section = ?
            ORDER BY id DESC
            """,
            (subject_id, section)
        ).fetchall()


def get_content_by_id(content_id):
    with db_connection() as conn:
        return conn.execute(
            "SELECT * FROM content WHERE id = ?",
            (content_id,)
        ).fetchone()


def save_content(
    subject_id,
    section,
    content_type,
    text_content=None,
    file_id=None,
    caption=None,
    created_by=None,
):
    with db_connection() as conn:
        conn.execute(
            """
            INSERT INTO content (
                subject_id, section, content_type,
                text_content, file_id, caption, created_by
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                subject_id,
                section,
                content_type,
                text_content,
                file_id,
                caption,
                created_by,
            )
        )


def delete_content(content_id):
    with db_connection() as conn:
        cursor = conn.execute(
            "DELETE FROM content WHERE id = ?",
            (content_id,)
        )
        return cursor.rowcount > 0


# =========================================================
# 4. أدوات الواجهة
# =========================================================

def add_back_button(keyboard, text, callback_data):
    keyboard.add(
        InlineKeyboardButton(
            text=text,
            callback_data=callback_data
        )
    )


def subjects_keyboard(prefix="sub"):
    keyboard = InlineKeyboardMarkup(row_width=2)

    for i in range(0, len(SUBJECTS), 2):
        row = [
            InlineKeyboardButton(
                SUBJECTS[i],
                callback_data=f"{prefix}_{i}"
            )
        ]

        if i + 1 < len(SUBJECTS):
            row.append(
                InlineKeyboardButton(
                    SUBJECTS[i + 1],
                    callback_data=f"{prefix}_{i + 1}"
                )
            )

        keyboard.row(*row)

    return keyboard


def sections_keyboard(subject_id):
    keyboard = InlineKeyboardMarkup(row_width=1)

    for key, title in SECTIONS.items():
        keyboard.add(
            InlineKeyboardButton(
                title,
                callback_data=f"sec_{subject_id}_{key}"
            )
        )

    add_back_button(
        keyboard, "🔙 الرجوع إلى المواد", "show_subjects"
    )
    return keyboard


def welcome_keyboard():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton(
            "📚 تصفح مواد المعهد",
            callback_data="show_subjects"
        )
    )
    return keyboard


def admin_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton(
            "➕ إضافة محتوى",
            callback_data="admin_add"
        ),
        InlineKeyboardButton(
            "🗑 حذف محتوى",
            callback_data="admin_delete"
        ),
        InlineKeyboardButton(
            "📊 الإحصاءات",
            callback_data="admin_stats"
        ),
        InlineKeyboardButton(
            "🏠 القائمة الرئيسية",
            callback_data="home"
        )
    )
    return keyboard


def safe_edit(call, text, reply_markup=None):
    try:
        bot.edit_message_text(
            text,
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=reply_markup
        )
    except Exception:
        bot.send_message(
            call.message.chat.id,
            text,
            reply_markup=reply_markup
        )


# =========================================================
# 5. عرض المحتوى للطلاب
# =========================================================

def send_content_item(chat_id, item):
    content_type = item["content_type"]
    file_id = item["file_id"]
    text_content = item["text_content"]
    caption = item["caption"]

    try:
        if content_type == "text":
            bot.send_message(chat_id, text_content or "")

        elif content_type == "link":
            bot.send_message(
                chat_id,
                text_content or "",
                disable_web_page_preview=False
            )

        elif content_type == "document":
            bot.send_document(
                chat_id, file_id, caption=caption or None
            )

        elif content_type == "audio":
            bot.send_audio(
                chat_id, file_id, caption=caption or None
            )

        elif content_type == "voice":
            bot.send_voice(
                chat_id, file_id, caption=caption or None
            )

        elif content_type == "video":
            bot.send_video(
                chat_id, file_id, caption=caption or None
            )

        elif content_type == "photo":
            bot.send_photo(
                chat_id, file_id, caption=caption or None
            )

        else:
            bot.send_message(
                chat_id,
                "تعذر عرض هذا النوع من المحتوى."
            )

    except Exception:
        logger.exception("Failed to send content item %s", item["id"])
        bot.send_message(
            chat_id,
            "تعذر إرسال هذا الملف. يرجى إبلاغ إدارة المعهد."
        )


def show_section(chat_id, subject_id, section):
    items = get_content(subject_id, section)

    bot.send_message(
        chat_id,
        f"📚 المادة: {SUBJECTS[subject_id]}\n"
        f"{SECTIONS[section]}\n\n"
        f"عدد المواد المتاحة: {len(items)}"
    )

    if not items:
        bot.send_message(
            chat_id,
            "لا يوجد محتوى مضاف في هذا القسم حتى الآن."
        )
        return

    for number, item in enumerate(items, start=1):
        bot.send_message(chat_id, f"📌 المادة التعليمية رقم {number}")
        send_content_item(chat_id, item)


# =========================================================
# 6. أوامر البداية والإدارة
# =========================================================

@bot.message_handler(commands=["start", "help"])
def send_welcome(message):
    bot.send_message(
        message.chat.id,
        "أهلًا بك في بوت المعهد التخصصي للحديث النبوي الشريف وعلومه.\n\n"
        "نسأل الله أن ينفعك بالعلم، وأن يرزقك الإخلاص والقبول.\n\n"
        "اختر ما تريد من القائمة:",
        reply_markup=welcome_keyboard()
    )


@bot.message_handler(commands=["admin"])
def open_admin(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(
            message,
            "عذرًا، هذا الأمر مخصص للمشرفين المعتمدين."
        )
        return

    bot.send_message(
        message.chat.id,
        "⚙️ لوحة إدارة محتوى المعهد",
        reply_markup=admin_keyboard()
    )


@bot.message_handler(commands=["cancel"])
def cancel_action(message):
    admin_states.pop(message.from_user.id, None)
    bot.reply_to(message, "تم إلغاء العملية الحالية.")


# =========================================================
# 7. التفاعل مع الأزرار
# =========================================================

@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    try:
        bot.answer_callback_query(call.id)

        data = call.data
        user_id = call.from_user.id
        chat_id = call.message.chat.id

        if data == "home":
            safe_edit(
                call,
                "القائمة الرئيسية لبوت المعهد:",
                welcome_keyboard()
            )

        elif data == "show_subjects":
            safe_edit(
                call,
                "📚 اختر المادة التي تريد الاطلاع على محتواها:",
                subjects_keyboard()
            )

        elif data.startswith("sub_"):
            subject_id = int(data.split("_")[1])

            if 0 <= subject_id < len(SUBJECTS):
                safe_edit(
                    call,
                    f"المادة المختارة: {SUBJECTS[subject_id]}\n\n"
                    "اختر قسم المحتوى:",
                    sections_keyboard(subject_id)
                )

        elif data.startswith("sec_"):
            parts = data.split("_")
            subject_id = int(parts[1])
            section = parts[2]

            if (
                0 <= subject_id < len(SUBJECTS)
                and section in SECTIONS
            ):
                show_section(chat_id, subject_id, section)

        elif data == "admin_add":
            if not is_admin(user_id):
                return

            safe_edit(
                call,
                "اختر المادة التي تريد إضافة محتوى إليها:",
                subjects_keyboard("addsub")
            )

        elif data.startswith("addsub_"):
            if not is_admin(user_id):
                return

            subject_id = int(data.split("_")[1])

            if not 0 <= subject_id < len(SUBJECTS):
                return

            keyboard = InlineKeyboardMarkup(row_width=1)

            for key, title in SECTIONS.items():
                keyboard.add(
                    InlineKeyboardButton(
                        title,
                        callback_data=f"addsec_{subject_id}_{key}"
                    )
                )

            add_back_button(
                keyboard, "🔙 إلغاء والعودة للإدارة", "admin_home"
            )

            safe_edit(
                call,
                f"إضافة محتوى إلى مادة: {SUBJECTS[subject_id]}\n"
                "اختر القسم المناسب:",
                keyboard
            )

        elif data.startswith("addsec_"):
            if not is_admin(user_id):
                return

            parts = data.split("_")
            subject_id = int(parts[1])
            section = parts[2]

            if (
                not 0 <= subject_id < len(SUBJECTS)
                or section not in SECTIONS
            ):
                return

            admin_states[user_id] = {
                "stage": "await_content",
                "subject_id": subject_id,
                "section": section,
            }

            safe_edit(
                call,
                f"📥 إضافة محتوى جديد\n\n"
                f"المادة: {SUBJECTS[subject_id]}\n"
                f"القسم: {SECTIONS[section]}\n\n"
                "أرسل الآن المحتوى المطلوب:\n"
                "• رسالة نصية.\n"
                "• ملف PDF أو مستند.\n"
                "• ملفًا صوتيًا أو مرئيًا.\n"
                "• صورة.\n"
                "• رابطًا في رسالة نصية.\n\n"
                "للإلغاء أرسل /cancel."
            )

        elif data == "admin_delete":
            if not is_admin(user_id):
                return

            safe_edit(
                call,
                "اختر المادة التي تريد حذف محتوى منها:",
                subjects_keyboard("delsub")
            )

        elif data.startswith("delsub_"):
            if not is_admin(user_id):
                return

            subject_id = int(data.split("_")[1])

            if not 0 <= subject_id < len(SUBJECTS):
                return

            keyboard = InlineKeyboardMarkup(row_width=1)

            for key, title in SECTIONS.items():
                keyboard.add(
                    InlineKeyboardButton(
                        title,
                        callback_data=f"delsec_{subject_id}_{key}"
                    )
                )

            safe_edit(
                call,
                f"اختر القسم في مادة {SUBJECTS[subject_id]}:",
                keyboard
            )

        elif data.startswith("delsec_"):
            if not is_admin(user_id):
                return

            parts = data.split("_")
            subject_id = int(parts[1])
            section = parts[2]

            if (
                not 0 <= subject_id < len(SUBJECTS)
                or section not in SECTIONS
            ):
                return

            items = get_content(subject_id, section)
            keyboard = InlineKeyboardMarkup(row_width=1)

            for item in items[:50]:
                description = (
                    item["text_content"]
                    or item["caption"]
                    or item["content_type"]
                    or "محتوى"
                )
                description = description.replace("\n", " ")[:35]

                keyboard.add(
                    InlineKeyboardButton(
                        f"🗑 #{item['id']} - {description}",
                        callback_data=f"delete_{item['id']}"
                    )
                )

            add_back_button(
                keyboard, "🔙 لوحة الإدارة", "admin_home"
            )

            safe_edit(
                call,
                f"محتويات مادة {SUBJECTS[subject_id]}:\n"
                f"{SECTIONS[section]}\n\n"
                "اختر العنصر المراد حذفه:",
                keyboard
            )

        elif data.startswith("delete_"):
            if not is_admin(user_id):
                return

            content_id = int(data.split("_")[1])

            if delete_content(content_id):
                safe_edit(call, "✅ تم حذف المحتوى بنجاح.")
            else:
                safe_edit(call, "لم يُعثر على المحتوى المطلوب.")

        elif data == "admin_stats":
            if not is_admin(user_id):
                return

            with db_connection() as conn:
                total = conn.execute(
                    "SELECT COUNT(*) FROM content"
                ).fetchone()[0]

                by_section = conn.execute(
                    """
                    SELECT section, COUNT(*) AS total
                    FROM content
                    GROUP BY section
                    """
                ).fetchall()

            lines = [
                "📊 إحصاءات محتوى المعهد",
                "",
                f"إجمالي العناصر: {total}",
                "",
            ]

            for row in by_section:
                title = SECTIONS.get(row["section"], row["section"])
                lines.append(f"{title}: {row['total']}")

            bot.send_message(chat_id, "\n".join(lines))

        elif data == "admin_home":
            if not is_admin(user_id):
                return

            safe_edit(
                call,
                "⚙️ لوحة إدارة محتوى المعهد",
                admin_keyboard()
            )

    except Exception:
        logger.exception("Callback processing error")
        try:
            bot.send_message(
                call.message.chat.id,
                "حدث خطأ أثناء تنفيذ الطلب. حاول مرة أخرى."
            )
        except Exception:
            pass


# =========================================================
# 8. استقبال المحتوى الذي يرسله المشرف
# =========================================================

@bot.message_handler(
    content_types=[
        "text", "document", "audio", "voice",
        "video", "photo"
    ],
    func=lambda message: (
        message.from_user is not None
        and message.from_user.id in ADMIN_IDS
        and message.from_user.id in admin_states
        and admin_states[message.from_user.id].get("stage")
        == "await_content"
    )
)
def receive_content(message):
    user_id = message.from_user.id
    state = admin_states.get(user_id)

    if not state:
        return

    subject_id = state["subject_id"]
    section = state["section"]

    content_type = None
    text_content = None
    file_id = None
    caption = getattr(message, "caption", None)

    if message.content_type == "text":
        text = message.text.strip()

        if not text:
            bot.reply_to(message, "أرسل محتوى غير فارغ.")
            return

        # قسم الروابط: يحفظ الرابط أو النص الذي يحتوي عليه.
        if section == "links":
            content_type = "link"
            text_content = text

        # الرسائل النصية مسموحة في قسم النصوص أيضًا.
        elif section == "text":
            content_type = "text"
            text_content = text

        else:
            bot.reply_to(
                message,
                "هذا القسم مخصص للملفات. أرسل ملفًا مناسبًا "
                "أو ألغِ العملية بالأمر /cancel."
            )
            return

    elif message.content_type == "document":
        content_type = "document"
        file_id = message.document.file_id

    elif message.content_type == "audio":
        content_type = "audio"
        file_id = message.audio.file_id

    elif message.content_type == "voice":
        content_type = "voice"
        file_id = message.voice.file_id

    elif message.content_type == "video":
        content_type = "video"
        file_id = message.video.file_id

    elif message.content_type == "photo":
        content_type = "photo"
        file_id = message.photo[-1].file_id

    # التحقق من ملاءمة نوع المحتوى للقسم المختار.
    if section == "audio" and content_type not in (
        "audio", "voice", "document"
    ):
        bot.reply_to(
            message,
            "أرسل ملفًا صوتيًا أو مستندًا لهذا القسم."
        )
        return

    if section == "video" and content_type not in (
        "video", "document"
    ):
        bot.reply_to(
            message,
            "أرسل ملفًا مرئيًا أو مستندًا لهذا القسم."
        )
        return

    if section == "links" and content_type != "link":
        bot.reply_to(
            message,
            "قسم الروابط يقبل الروابط المرسلة كنص. "
            "أرسل الرابط في رسالة نصية."
        )
        return

    try:
        save_content(
            subject_id=subject_id,
            section=section,
            content_type=content_type,
            text_content=text_content,
            file_id=file_id,
            caption=caption,
            created_by=user_id,
        )

        admin_states.pop(user_id, None)

        bot.reply_to(
            message,
            "✅ تم حفظ المحتوى بنجاح.\n\n"
            f"المادة: {SUBJECTS[subject_id]}\n"
            f"القسم: {SECTIONS[section]}\n\n"
            "يمكنك إضافة محتوى آخر من خلال /admin."
        )

    except Exception:
        logger.exception("Failed to save content")
        bot.reply_to(
            message,
            "تعذر حفظ المحتوى. راجع سجلات التطبيق في Render."
        )


# =========================================================
# 9. تشغيل البوت
# =========================================================

if __name__ == "__main__":
    logger.info("Bot is starting...")
    bot.remove_webhook()
    bot.infinity_polling(
        skip_pending=True,
        timeout=30,
        long_polling_timeout=30
    )
