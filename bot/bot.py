import asyncio
import json
import logging
import os
import sys
import django

# --- DJANGO SETUP ---
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(BASE_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from main.models import Category, Product

# --------------------

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
)
import os
from dotenv import load_dotenv
load_dotenv()
BOT_TOKEN = os.getenv("token")
raw_admins = os.getenv("ADMIN_ID", "")
ADMIN_IDS = [int(x) for x in raw_admins.split(",") if x.strip()]
raw_channels = os.getenv("CHANNEL_ID", "")
CHANNEL_IDS = [int(x) for x in raw_channels.split(",") if x.strip()]
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

DELETE_AFTER = 10 

def yuborilmadi_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Yuborilmadi ❌", callback_data="send")]
    ])


class AdminState(StatesGroup):
    choosing_cat_action = State() 
    adding_new_cat = State()  
    waiting_for_cat = State()  
    waiting_for_name_uz = State()
    waiting_for_name_ru = State()
    waiting_for_price = State()
    waiting_for_photo = State()


class OrderState(StatesGroup):
    waiting_for_name = State()
    waiting_for_phone = State()
    waiting_for_loc = State()
    waiting_for_confirm = State()


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    kb = [
        [
            types.KeyboardButton(
                text="Menuni ko'rish",
                web_app=types.WebAppInfo(url="https://tsukiyomi.pythonanywhere.com/"),
            )
        ]
    ]
    markup = ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
    await message.answer(
        "Xush kelibsiz! Buyurtma berish uchun menuni oching.", reply_markup=markup
    )


@dp.message(F.web_app_data)
async def web_app_receive(message: types.Message, state: FSMContext):
    data = json.loads(message.web_app_data.data)
    await state.update_data(cart=data)
    await message.answer("Ismingizni kiriting:", reply_markup=ReplyKeyboardRemove())
    await state.set_state(OrderState.waiting_for_name)


@dp.message(OrderState.waiting_for_name)
async def get_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    kb = [[KeyboardButton(text="📞 Kontaktni ulashish", request_contact=True)]]
    await message.answer(
        "Telefon raqamingizni yuboring:",
        reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True),
    )
    await state.set_state(OrderState.waiting_for_phone)


@dp.message(OrderState.waiting_for_phone, F.contact)
async def get_phone(message: types.Message, state: FSMContext):
    await state.update_data(phone=message.contact.phone_number)
    kb = [[KeyboardButton(text="📍 Lokatsiyani ulashish", request_location=True)]]
    await message.answer(
        "Manzilingizni yuboring:",
        reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True),
    )
    await state.set_state(OrderState.waiting_for_loc)


@dp.message(OrderState.waiting_for_loc, F.location)
async def ask_confirmation(message: types.Message, state: FSMContext):
    await state.update_data(
        lat=message.location.latitude, lon=message.location.longitude
    )
    user_data = await state.get_data()
    cart = user_data.get("cart", {})

    total_price = 0
    cart_details = ""

    # FIX: Convert string values from WebApp to integers
    for item_id, item in cart.items():
        try:
            price = int(float(item["price"]))  # Handles both '15000' and '15000.0'
            qty = int(item["qty"])
            subtotal = price * qty
            total_price += subtotal
            cart_details += (
                f"🔸 {item['name']}\n      {qty} x {price:,} = {subtotal:,} so'm\n"
            )
        except (ValueError, KeyError):
            continue

    summary = (
        f"📋 **BUYURTMANGIZNI TASDIQLANG:**\n\n"
        f"👤 Ism: {user_data['name']}\n"
        f"📞 Tel: {user_data['phone']}\n"
        f"--------------------------\n"
        f"{cart_details}"
        f"--------------------------\n"
        f"💰 **JAMI: {total_price:,} so'm**"
    )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Tasdiqlash", callback_data="confirm_order"
                ),
                InlineKeyboardButton(
                    text="❌ Bekor qilish", callback_data="cancel_order"
                ),
            ]
        ]
    )

    await message.answer(summary, reply_markup=kb, parse_mode="Markdown")
    await state.update_data(total_price=total_price, cart_details=cart_details)
    await state.set_state(OrderState.waiting_for_confirm)


@dp.callback_query(F.data == "confirm_order", OrderState.waiting_for_confirm)
async def finalize_order(callback: types.CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    for channel_id in CHANNEL_IDS:

    # Improved Google Maps Link
        loc_url = f"https://www.google.com/maps?q={user_data['lat']},{user_data['lon']}"

        order_text = (
            f"🆕 **YANGI BUYURTMA!**\n\n"
            f"👤 Ism: {user_data['name']}\n"
            f"📞 Tel: {user_data['phone']}\n"
            f"🛒 **MAHSULOTLAR:**\n{user_data['cart_details']}\n"
            f"💰 **UMUMIY SUMMA: {user_data['total_price']:,} so'm**\n\n"
            f"📍 [Lokatsiyani ko'rish]({loc_url})"
        )

        sent_msg = await bot.send_message(
    channel_id,
    order_text,
    reply_markup=yuborilmadi_keyboard(),  # bu yerda tugma qo‘shildi
    parse_mode="Markdown",
    disable_web_page_preview=False
)

    await callback.message.edit_text("✅ Rahmat! Buyurtmangiz qabul qilindi.")
    await state.clear()


@dp.callback_query(F.data == "send")
async def send_handler(callback: types.CallbackQuery):
    user_id = callback.from_user.id

    # Faqat admin tugmani bosishi mumkin
    if user_id not in ADMIN_IDS:
        await callback.answer("⛔ Siz admin emassiz!", show_alert=True)
        return

    # Tugma Yuborildi ✅ ga o'zgaradi
    await callback.message.edit_reply_markup(
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Yuborildi ✅", callback_data="done")]
        ])
    )
    await callback.answer("Yuborildi ✅")

    # Belgilangan vaqtdan keyin xabar o'chadi
    await asyncio.sleep(DELETE_AFTER)
    await callback.message.delete()


from asgiref.sync import sync_to_async
from django.core.files.base import ContentFile

# --- ADMIN PANEL: PRODUCT MANAGEMENT ---


@dp.message(Command("admin"), F.from_user.id.in_(ADMIN_IDS))
async def admin_start(message: types.Message, state: FSMContext):
    get_categories = sync_to_async(lambda: list(Category.objects.all()))
    categories = await get_categories()

    kb = [[KeyboardButton(text="➕ Yangi kategoriya")]]
    if categories:
        kb.extend([[KeyboardButton(text=cat.name_uz)] for cat in categories])

    markup = ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
    await message.answer(
        "🛠 Kategoriyani tanlang yoki yangisini qo'shing:", reply_markup=markup
    )
    await state.set_state(AdminState.waiting_for_cat)


@dp.message(AdminState.waiting_for_cat, F.text == "➕ Yangi kategoriya")
async def add_cat_start(message: types.Message, state: FSMContext):
    await message.answer(
        "Yangi kategoriya nomini kiriting (UZ):", reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(AdminState.adding_new_cat)


@dp.message(AdminState.adding_new_cat)
async def add_cat_finish(message: types.Message, state: FSMContext):
    def create_cat(name):
        return Category.objects.create(name_uz=name, name_ru=name)

    new_cat = await sync_to_async(create_cat)(message.text)
    await state.update_data(cat_id=new_cat.id)
    await message.answer(
        f"✅ Kategoriya '{new_cat.name_uz}' yaratildi.\n\nEndi mahsulot nomini kiriting (UZ):"
    )
    await state.set_state(AdminState.waiting_for_name_uz)


@dp.message(AdminState.waiting_for_cat)
async def process_category_selection(message: types.Message, state: FSMContext):
    def get_cat(name):
        return Category.objects.filter(name_uz=name).first()

    category = await sync_to_async(get_cat)(message.text)
    if category:
        await state.update_data(cat_id=category.id)
        await message.answer(
            f"'{category.name_uz}' tanlandi.\nMahsulot nomini kiriting (UZ):",
            reply_markup=ReplyKeyboardRemove(),
        )
        await state.set_state(AdminState.waiting_for_name_uz)
    else:
        await message.answer(
            "Iltimos, ro'yxatdan tanlang yoki yangi kategoriya qo'shing!"
        )


@dp.message(AdminState.waiting_for_name_uz)
async def process_name_uz(message: types.Message, state: FSMContext):
    await state.update_data(name_uz=message.text)
    await message.answer("Mahsulot nomini kiriting (RU):")
    await state.set_state(AdminState.waiting_for_name_ru)


@dp.message(AdminState.waiting_for_name_ru)
async def process_name_ru(message: types.Message, state: FSMContext):
    await state.update_data(name_ru=message.text)
    await message.answer("Narxini kiriting (faqat raqam):")
    await state.set_state(AdminState.waiting_for_price)


@dp.message(AdminState.waiting_for_price)
async def process_price(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        return await message.answer("Narxni faqat raqamda yozing!")
    await state.update_data(price=int(message.text))
    await message.answer("Mahsulot rasmini yuboring:")
    await state.set_state(AdminState.waiting_for_photo)


@dp.message(AdminState.waiting_for_photo, F.photo)
async def process_photo(message: types.Message, state: FSMContext):
    photo = message.photo[-1]
    file_info = await bot.get_file(photo.file_id)
    downloaded_file = await bot.download_file(file_info.file_path)
    data = await state.get_data()

    def save_to_db(prod_data, file_obj, filename):
        product = Product(
            category_id=prod_data["cat_id"],
            name_uz=prod_data["name_uz"],
            name_ru=prod_data["name_ru"],
            price=prod_data["price"],
        )
        product.image.save(filename, ContentFile(file_obj.read()), save=True)
        return product

    await sync_to_async(save_to_db)(data, downloaded_file, f"{photo.file_id}.jpg")
    await message.answer(
        f"✅ Mahsulot muvaffaqiyatli saqlandi!\nNom: {data['name_uz']}"
    )
    await state.clear()


async def main():
    for ADMIN_ID in ADMIN_IDS:
        await bot.send_message(chat_id=ADMIN_ID, text="bot ishga tushdi...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
