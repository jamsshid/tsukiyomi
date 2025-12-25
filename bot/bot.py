import asyncio
import json
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

bot = Bot(token="8552455101:AAH01JwjFmm9hfgRf0AmFWuZRq1aJXwrjms")
dp = Dispatcher()


class AdminState(StatesGroup):
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
                web_app=types.WebAppInfo(url="https://98933d9e802b1d.lhr.life"),
            )
        ]
    ]
    markup = types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
    await message.answer(
        "Xush kelibsiz! Buyurtma berish uchun menuni oching.", reply_markup=markup
    )


@dp.message(F.web_app_data)
async def web_app_receive(message: types.Message, state: FSMContext):
    data = json.loads(message.web_app_data.data)
    await state.update_data(cart=data)
    await message.answer("Ismingizni kiriting:")
    await state.set_state(OrderState.waiting_for_name)


@dp.message(OrderState.waiting_for_name)
async def get_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    kb = [[types.KeyboardButton(text="📞 Kontaktni ulashish", request_contact=True)]]
    await message.answer(
        "Telefon raqamingizni yuboring:",
        reply_markup=types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True),
    )
    await state.set_state(OrderState.waiting_for_phone)


@dp.message(OrderState.waiting_for_phone, F.contact)
async def get_phone(message: types.Message, state: FSMContext):
    await state.update_data(phone=message.contact.phone_number)
    kb = [[types.KeyboardButton(text="📍 Lokatsiyani ulashish", request_location=True)]]
    await message.answer(
        "Manzilingizni yuboring:",
        reply_markup=types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True),
    )
    await state.set_state(OrderState.waiting_for_loc)


@dp.message(OrderState.waiting_for_loc, F.location)
async def ask_confirmation(message: types.Message, state: FSMContext):
    await state.update_data(
        lat=message.location.latitude, lon=message.location.longitude
    )
    user_data = await state.get_data()

    cart = user_data[
        "cart"
    ]  
    total_price = 0
    cart_details = ""

    for item_id, item in cart.items():
        subtotal = item["price"] * item["qty"]
        total_price += subtotal
        cart_details += f"🔸 {item['name']}\n      {item['qty']} x {item['price']:,} = {subtotal:,} so'm\n"

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
    await state.update_data(
        total_price=total_price, cart_details=cart_details
    )  # Keyinroq kerak bo'ladi
    await state.set_state(OrderState.waiting_for_confirm)


@dp.callback_query(F.data == "confirm_order", OrderState.waiting_for_confirm)
async def finalize_order(callback: types.CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    channel_id = "-1002498829698"

    order_text = (
        f"🆕 **YANGI BUYURTMA!**\n\n"
        f"👤 Ism: {user_data['name']}\n"
        f"📞 Tel: {user_data['phone']}\n"
        f"🛒 **MAHSULOTLAR:**\n{user_data['cart_details']}\n"
        f"💰 **UMUMIY SUMMA: {user_data['total_price']:,} so'm**\n\n"
        f"📍 Lokatsiya: https://www.google.com/maps?q={user_data['lat']},{user_data['lon']}"
    )

    await bot.send_message(channel_id, order_text, parse_mode="Markdown")
    await callback.message.edit_text("✅ Rahmat! Buyurtmangiz qabul qilindi.")
    await state.clear()

from main.models import Category, Product 
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

ADMIN_ID = 6896519874


# 1. Admin panelni boshlash va kategoriyani tanlash
@dp.message(Command("admin"), F.from_user.id == ADMIN_ID)
async def admin_start(message: types.Message, state: FSMContext):
    # Bazadagi barcha kategoriyalarni olamiz
    categories = Category.objects.all()

    if not categories:
        return await message.answer("Avval Django admin panelda kategoriya yarating!")

    # Kategoriyalar ro'yxatini chiqarish
    kb = [[KeyboardButton(text=cat.name_uz)] for cat in categories]
    markup = ReplyKeyboardMarkup(
        keyboard=kb, resize_keyboard=True, one_time_keyboard=True
    )

    await message.answer(
        "🛠 Yangi mahsulot qo'shish.\nKategoriyani tanlang:", reply_markup=markup
    )
    await state.set_state(AdminState.waiting_for_cat)


# 2. Tanlangan kategoriyani saqlash va Nom (UZ) so'rash
@dp.message(AdminState.waiting_for_cat)
async def process_category(message: types.Message, state: FSMContext):
    try:
        category = Category.objects.get(name_uz=message.text)
        await state.update_data(cat_id=category.id)
        await message.answer(
            "Mahsulot nomini kiriting (UZ):", reply_markup=ReplyKeyboardRemove()
        )
        await state.set_state(AdminState.waiting_for_name_uz)
    except Category.DoesNotExist:
        await message.answer("Iltimos, tugmalar orqali tanlang!")


# 3. Nom (RU) so'rash
@dp.message(AdminState.waiting_for_name_uz)
async def process_name_uz(message: types.Message, state: FSMContext):
    await state.update_data(name_uz=message.text)
    await message.answer("Mahsulot nomini kiriting (RU):")
    await state.set_state(AdminState.waiting_for_name_ru)


# 4. Narxni so'rash
@dp.message(AdminState.waiting_for_name_ru)
async def process_name_ru(message: types.Message, state: FSMContext):
    await state.update_data(name_ru=message.text)
    await message.answer("Narxini kiriting (faqat raqam):")
    await state.set_state(AdminState.waiting_for_price)


# 5. Rasmni so'rash
@dp.message(AdminState.waiting_for_price)
async def process_price(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        return await message.answer("Narxni faqat raqamda yozing!")

    await state.update_data(price=int(message.text))
    await message.answer("Mahsulot rasmini yuboring:")
    await state.set_state(AdminState.waiting_for_photo)


# 6. Rasmni qabul qilish va Django bazasiga saqlash
@dp.message(AdminState.waiting_for_photo, F.photo)
async def process_photo(message: types.Message, state: FSMContext):
    photo = message.photo[-1]
    file_info = await bot.get_file(photo.file_id)

    # Rasmni yuklab olish
    import os
    from django.core.files import File
    from io import BytesIO

    file_content = await bot.download_file(file_info.file_path)
    data = await state.get_data()

    # Django ORM orqali mahsulot yaratish
    new_product = Product(
        category_id=data["cat_id"],
        name_uz=data["name_uz"],
        name_ru=data["name_ru"],
        price=data["price"],
    )
    # Rasmni Django ImageField-ga moslab saqlash
    new_product.image.save(f"{photo.file_id}.jpg", File(file_content))
    new_product.save()

    await message.answer(
        f"✅ Mahsulot muvaffaqiyatli saqlandi!\nNom: {data['name_uz']}"
    )
    await state.clear()


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
