import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ضع توكن البوت الخاص بك هنا بين علامتي التنصيص
TOKEN = "8621524247:AAFgeDxavRVzFbt1KeqYHXRPIvVAKPdTznA"
bot = telebot.TeleBot(TOKEN)

def get_subjects_keyboard() -> InlineKeyboardMarkup:
    """إنشاء لوحة المفاتيح التفاعلية لمواد المعهد (18 مادة) مرتبة في صفوف ثنائية"""
    subjects = [
        "علوم القرآن", "التجويد",
        "صحيح البخاري", "رياض الصالحين",
        "الأربعين النووية", "السيرة النبوية",
        "السنة والتحديات", "قصة الحديث",
        "تراجم العلماء", "الكواكب الزاهرة",
        "البيقونية", "التقريب والتيسير",
        "الفقه", "النحو",
        "الصرف", "العقيدة",
        "آداب الطالب", "ألفية السيوطي"
    ]
    
    keyboard = InlineKeyboardMarkup()
    for i in range(0, len(subjects), 2):
        row = [InlineKeyboardButton(text=subjects[i], callback_data=f"sub_{i}")]
        if i + 1 < len(subjects):
            row.append(InlineKeyboardButton(text=subjects[i+1], callback_data=f"sub_{i+1}"))
        keyboard.add(*row)
    
    keyboard.add(InlineKeyboardButton(text="🔙 الرجوع", callback_data="back_to_welcome"))
    return keyboard

def get_sections_keyboard() -> InlineKeyboardMarkup:
    """إنشاء لوحة مفاتيح أقسام الملفات للمادة المحددة"""
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(text="📄 الملفات النصية", callback_data="sec_text"))
    keyboard.add(InlineKeyboardButton(text="🎧 الملفات الصوتية", callback_data="sec_audio"))
    keyboard.add(InlineKeyboardButton(text="🎥 الملفات المرئية", callback_data="sec_video"))
    keyboard.add(InlineKeyboardButton(text="🔗 روابط إثرائية", callback_data="sec_links"))
    keyboard.add(InlineKeyboardButton(text="🔙 الرجوع للمواد", callback_data="back_to_subjects"))
    return keyboard

@bot.message_handler(commands=['start'])
def send_welcome(message):
    """الترحيب بالمستخدم عند إرسال الأمر /start"""
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(text="✨ السلام عليكم و رحمة الله", callback_data="say_salam"))
    bot.send_message(
        message.chat.id, 
        "أهلاً بك في بوت المعهد التخصصي للحديث الشريف و علومه:", 
        reply_markup=keyboard
    )

@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    """إدارة كافة التفاعلات والأزرار في البوت"""
    try:
        if call.data == "say_salam":
            keyboard = InlineKeyboardMarkup()
            keyboard.add(InlineKeyboardButton(text="📚 ملفات مواد المعهد", callback_data="show_subjects"))
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text="وعليكم السلام ورحمة الله وبركاته، أهلاً بك في بوت المعهد التخصصي للحديث الشريف وعلومه.",
                reply_markup=keyboard
            )
        
        elif call.data == "show_subjects":
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text="الرجاء اختيار المادة المطلوبة من القائمة أدناه:",
                reply_markup=get_subjects_keyboard()
            )
            
        elif call.data.startswith("sub_"):
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text="اختر نوع المحتوى أو الملفات المطلوبة للمادة:",
                reply_markup=get_sections_keyboard()
            )
            
        elif call.data in ["sec_text", "sec_audio", "sec_video", "sec_links"]:
            bot.answer_callback_query(call.id, "جاري تحميل القسم المطلوب...")
            bot.send_message(call.message.chat.id, "📁 عتبة القسم قيد التفعيل، سيتم إدراج المحتوى قريباً.")
            
        elif call.data == "back_to_welcome":
            keyboard = InlineKeyboardMarkup()
            keyboard.add(InlineKeyboardButton(text="✨ السلام عليكم و رحمة الله", callback_data="say_salam"))
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text="أهلاً بك مجدداً في بوت المعهد:",
                reply_markup=keyboard
            )
            
        elif call.data == "back_to_subjects":
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text="قائمة مواد المعهد:",
                reply_markup=get_subjects_keyboard()
            )
    except Exception as e:
        print(f"Error handling callback: {e}")

if __name__ == "__main__":
    print("Bot is starting and polling...")
    bot.remove_webhook()
    bot.infinity_polling(skip_pending=True)
