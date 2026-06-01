from langchain_core.runnables import chain

from langchain_groq import ChatGroq  # Меняем импорт
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableBranch, RunnableLambda
from pydantic import BaseModel
import os

from config import agent_key

# Инициализация модели Groq
llm = ChatGroq(
    model="llama-3.3-70b-versatile", # Или другая доступная модель, например mixtral-8x7b-32768
    temperature=0.7,
    api_key=agent_key,
)

MY_STACK = """
УМЕЮ (основное):
- Python: парсинг (BeautifulSoup, Selenium, playwright), автоматизация, анализ данных (Pandas, NumPy)
- Telegram-боты: Aiogram, Pyrogram, Telebot
- Веб-сервисы: Flask, REST API
- БД: PostgreSQL, MySQL, SQLite + SQLAlchemy
- Инфраструктура: Docker, Linux, Nginx, деплой на VPS (Beget), Git
- Фронтенд (базовый): HTML/CSS/JavaScript, вёрстка по макетам Figma
- Доп: Asyncio, openpyxl, Tesseract (OCR), Unittest, Requests, langchain

ИЗУЧАЮ (могу взять несложное):
- Go (в процессе)

НЕ БЕРУСЬ:
- Мобильная разработка (iOS/Android)
- 1С, Bitrix, AmoCRM и подобное
- Чистый фронтенд / React / Vue (без Python-бэкенда)
- C++ / C# проекты (базовые знания, не коммерческий опыт)
- UI/UX дизайн с нуля (вёрстка по готовым макетам — да, дизайн сам — нет)
"""
class StackCheck(BaseModel):
    fits: bool          # подходит ли заказ под стек
    reason: str         # одна строка — почему да/нет
    unclear: bool       # ТЗ слишком размытое чтобы оценить?


stack_prompt = ChatPromptTemplate.from_messages([
    ("system", """Ты — технический фильтр для фрилансера.
Твоя задача: понять, сможет ли фрилансер выполнить этот заказ.

Стек фрилансера:
{stack}

Правила оценки:
- Оценивай что НУЖНО СДЕЛАТЬ, а не как это описано заказчиком
- Игнорируй пожелания заказчика про ИИ/без ИИ — это не про стек
- Если задача — парсинг, скрипт, автоматизация на Python → fits: true
- Если задача требует фронтенда, смотри есть ли Python-бэкенд в задаче
  Если фронтенд упомянут как часть задачи, но суть — бэкенд/скрипт → fits: true
- fits: false только если задача ЯВНО вне стека (1С, iOS, чистый React и т.д.)
- Если ТЗ размытое и невозможно оценить → unclear: true, fits: false
- reason — одна короткая фраза о сути задачи, не о причине отказа

Верни ТОЛЬКО валидный JSON, без пояснений."""),
    ("human", "Название: {название}\n\nТЗ: {тз}")
])

stack_chain = stack_prompt | llm.with_structured_output(StackCheck)
title_prompt = ChatPromptTemplate.from_messages([
    ("system", """Придумай короткое (2-4 слова) человекочитаемое название проекта на русском.
Примеры: "парсинг цен мебели", "телеграм-бот для магазина", "автоматизация выгрузки данных"
Верни ТОЛЬКО название, без кавычек и пояснений."""),
    ("human", "Название заказа: {название}\n\nТЗ: {тз}")
])
title_chain = title_prompt | llm | StrOutputParser()

response_prompt = ChatPromptTemplate.from_messages([(
    "system", """Ты — фрилансер с опытом, пишешь **реальный отклик заказчику** на Kwork.

    Стиль:
    - Живой разговорный русский
    - Начинаешь сразу по делу, без "Итак", "Здравствуйте", "Понял задачу" и т.д.
    - Пишешь так, как будто пишешь в чат заказчику
    - Используй "Вы" (вежливая форма)
    - Можно 1 эмодзи максимум
    - Будь конкретным и уверенным

    Запрещено:
    - Обращаться к заказчику на "ты"
    - Писать "ты также упоминаешь", "ты хочешь", "тебе нужен"
    - Слишком много объяснений "как я думаю"
    - Канцелярит и структурированные тексты

    Примеры хорошего отклика:

    Пример 1:
    "Смотрел ваше ТЗ по мебели. Сделаю скрипт, который будет искать цены по фото товаров через Google Lens / Yandex Images и автоматически обновлять их на сайте.

    Работал с похожим на Laravel + Python. Обычно использую Selenium + undetected-chromedriver, чтобы было стабильнее.

    Сколько товаров примерно нужно обработать? И какие основные магазины-конкуренты, у кого будем брать цены?"

    Пример 2:
    "Могу сделать парсер цен по картинкам. На Laravel стороне сделаю удобный запуск скрипта из админки.

    Скажите пожалуйста:
    — Сколько товаров в каталоге?
    — Как часто нужно обновлять цены?
    — Есть ли уже API или только через админку можно заходить?"
    """
),
    ("human", "Название: {название}\n\nТЗ: {тз}\n\nТЗ размытое: {unclear}")
])

response_chain = response_prompt | llm | StrOutputParser()
def check_fits(x):
    return x["stack_result"].fits

pipeline = (
    RunnableLambda(lambda x: {**x, "stack": MY_STACK})
    | RunnableLambda(lambda x: {
        **x,
        "stack_result": stack_chain.invoke(x),
        "short_title": title_chain.invoke(x),   # <-- добавили
    })
    | RunnableBranch(
        (
            check_fits,
            RunnableLambda(lambda x: {
                **x,
                "response": response_chain.invoke({
                    "название": x["название"],
                    "тз": x["тз"],
                    "unclear": x["stack_result"].unclear,
                }),
                "status": "approved",
            })
        ),
        RunnableLambda(lambda x: {
            **x,
            "response": None,
            "status": "rejected",
            "reason": x["stack_result"].reason,
        })
    )
)


