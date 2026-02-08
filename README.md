# Rubika Bot API v3 - پروژه حرفه‌ای بات روبیکا

این پروژه یک فریم‌ورک **Production-Ready** برای ساخت بات روبیکا (Rubika Bot API v3) است که بر پایه‌ی **Webhook** طراحی شده و تمرکز ویژه روی سرعت (Ack زیر 100ms)، پایداری، امنیت، توسعه‌پذیری و قابلیت‌های مدیریتی دارد.

## ویژگی‌های اصلی

- **زبان**: Python
- **Webhook**: پشتیبانی کامل از `/receiveUpdate` و `/receiveInlineMessage`
- **SQLite** با لایه دسترسی تمیز + مهاجرت خودکار و نسخه‌بندی اسکیمـا
- معماری **ماژولار و پلاگین‌پذیر** (Anti، Moderation، Fun، Panel، Commands، Filters، Logging)
- Ack سریع + پردازش Async با صف داخلی
- لاگ‌گیری چرخشی، مدیریت استثنا و ردیابی رخدادها
- تست‌های Unit/Integration برای بخش‌های کلیدی

## ساختار پوشه‌ها

```
app/
  cli/              ابزار botctl
  db/               مهاجرت‌ها + Repository
  services/         کلاینت API، dispatcher و handler ها
  services/plugins/ پلاگین‌ها
  utils/            ابزارهای عمومی
  webhook/          روت‌های وبهوک
  main.py           نقطه ورود FastAPI
requirements.txt
tests/
README.md
```

## نصب و اجرا

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export RUBIKA_BOT_TOKEN=YOUR_TOKEN
export RUBIKA_API_BASE_URL=https://botapi.rubika.ir/v3
export RUBIKA_WEBHOOK_BASE_URL=https://your-domain.example

uvicorn app.main:app --host 0.0.0.0 --port 8080
```

### راه‌اندازی سریع با یک دستور (UI تعاملی)

این دستور یک UI ساده و زیبا نمایش می‌دهد، اطلاعات اصلی را می‌گیرد و در SQLite ذخیره می‌کند، سپس در صورت تایید سرویس را اجرا می‌کند:

```bash
python -m app.cli.botctl quickstart
```

اگر فقط بخواهید تنظیمات را ذخیره کنید:

```bash
python -m app.cli.botctl setup
```

### نصب خودکار با یک خط در لینوکس (دانلود از GitHub + سرویس خودکار)

```bash
curl -fsSL https://raw.githubusercontent.com/Opselon/rubica-bot/main/scripts/bootstrap.sh | bash
```

با این دستور، پروژه از GitHub دریافت می‌شود، ویزارد تنظیمات اجرا می‌شود و سرویس systemd به‌صورت خودکار ساخته و اجرا می‌گردد.

## تنظیم وبهوک و Endpoint

در `startup` اگر `RUBIKA_WEBHOOK_BASE_URL` تنظیم باشد، متد `updateBotEndpoints` برای ثبت آدرس‌های زیر فراخوانی می‌شود:

- `/receiveUpdate`
- `/receiveInlineMessage`

## امنیت و کنترل ترافیک

- **Signature**: اگر `RUBIKA_WEBHOOK_SECRET` تنظیم شود، امضای HMAC بررسی می‌شود.
- **Rate Limit**: محدودیت تعداد درخواست در دقیقه.
- **Dedup**: جلوگیری از پردازش تکراری آپدیت‌ها با TTL.

## معماری پلاگین‌ها

هر پلاگین یک کلاس مستقل است و در Pipeline قرار می‌گیرد:

- `MessageLoggingPlugin`
- `AntiLinkPlugin`
- `AntiFloodPlugin`
- `FilterWordsPlugin`
- `CommandsPlugin`
- `PanelPlugin`

## قابلیت‌های مدیریتی گروه

- تشخیص نوع چت و تنظیمات Anti در DB
- حذف پیام، بن/آن‌بن و مدیریت فیلترها
- پنل مدیریتی با InlineKeypad

## قابلیت‌های Anti Everything

### Anti Link
- تشخیص لینک با Regex قوی
- حذف پیام و بن کردن کاربر
- گزارش اختیاری در گروه

### Anti Flood
- محدودیت تعداد پیام در بازه زمانی
- حذف پیام و بن کاربر

### Anti BadWords (Filters)
- لیست فیلتر قابل تنظیم با دستور `/filter`
- پشتیبانی از Regex (قابل توسعه)

## دستورات اصلی

- `/help` نمایش راهنما
- `/setcmd` ثبت دستورات در روبیکا
- `/panel` پنل تنظیمات
- `/antilink on|off` مدیریت ضد لینک
- `/antiflood on|off` مدیریت ضد فلود
- `/flood <n>` تنظیم حداکثر پیام مجاز در بازه
- `/filter add|del|list <word>` مدیریت فیلترها
- `/del <n>` حذف انبوه پیام‌های اخیر
- `/ban <user_id>` / `/unban <user_id>`
- `/admin add|del|list <user_id>` مدیریت ادمین‌های گروه
- `/ping` / `/joke` / `/roll` / `/coin`

> نکته: اگر لیست ادمین‌ها در دیتابیس خالی باشد، اولین اجرای دستورات مدیریتی اجازه خواهد داشت تا ادمین اولیه ثبت شود.

## بات روبیکا - متدها (چکیده کاربردی)

### معرفی
در این پروژه تمام درخواست‌ها به شکل زیر ارسال می‌شود:

```
POST https://botapi.rubika.ir/v3/{token}/{method}
```

### فهرست موضوعات
- گرفتن اطلاعات بات: `getMe`
- ارسال پیام (Text/Keypad/InlineKeypad): `sendMessage`
- ارسال نظرسنجی: `sendPoll`
- ارسال موقعیت مکانی: `sendLocation`
- ارسال مخاطب: `sendContact`
- گرفتن اطلاعات چت: `getChat`
- گرفتن آخرین آپدیت‌ها: `getUpdates`
- فوروارد پیام: `forwardMessage`
- ویرایش متن پیام: `editMessageText`
- ویرایش InlineKeypad: `editMessageKeypad`
- حذف پیام: `deleteMessage`
- تنظیم دستورها: `setCommands`
- آپدیت آدرس بات: `updateBotEndpoints`
- حذف keypad: `editChatKeypad` با `Remove`
- ویرایش keypad: `editChatKeypad` با `New`
- دریافت فایل: `getFile`
- ارسال فایل: `sendFile`
- آپلود فایل: `requestSendFile`
- مسدود کردن کاربر: `banChatMember`
- رفع مسدودیت کاربر: `unbanChatMember`

### گرفتن اطلاعات بات (getMe)
```python
import requests

url = f"https://botapi.rubika.ir/v3/{token}/getMe"
response = requests.post(url)
print(response.text)
```

### ارسال پیام (sendMessage)
```python
import requests

data = {"chat_id": chat_id, "text": "Hello user, this is my text"}
url = f"https://botapi.rubika.ir/v3/{token}/sendMessage"
response = requests.post(url, json=data)
print(response.text)
```

### ارسال Keypad (sendMessage + chat_keypad)
```python
import requests

data = {
    "chat_id": chat_id,
    "text": "Welcome",
    "chat_keypad_type": "New",
    "chat_keypad": {
        "rows": [
            {"buttons": [{"id": "100", "type": "Simple", "button_text": "Add Account"}]},
            {
                "buttons": [
                    {"id": "101", "type": "Simple", "button_text": "Edit Account"},
                    {"id": "102", "type": "Simple", "button_text": "Remove Account"},
                ]
            },
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False,
    },
}
url = f"https://botapi.rubika.ir/v3/{token}/sendMessage"
response = requests.post(url, json=data)
print(response.text)
```

### ارسال InlineKeypad (sendMessage + inline_keypad)
```python
import requests

data = {
    "chat_id": chat_id,
    "text": "Welcome",
    "inline_keypad": {
        "rows": [
            {"buttons": [{"id": "100", "type": "Simple", "button_text": "Add Account"}]},
            {
                "buttons": [
                    {"id": "101", "type": "Simple", "button_text": "Edit Account"},
                    {"id": "102", "type": "Simple", "button_text": "Remove Account"},
                ]
            },
        ]
    },
}
url = f"https://botapi.rubika.ir/v3/{token}/sendMessage"
response = requests.post(url, json=data)
print(response.text)
```

### ارسال نظرسنجی (sendPoll)
```python
import requests

data = {"chat_id": chat_id, "question": "Do you have any question?", "options": ["yes", "no"]}
url = f"https://botapi.rubika.ir/v3/{token}/sendPoll"
response = requests.post(url, json=data)
print(response.text)
```

### ارسال موقعیت مکانی (sendLocation)
```python
import requests

data = {"chat_id": chat_id, "latitude": latitude, "longitude": longitude}
url = f"https://botapi.rubika.ir/v3/{token}/sendLocation"
response = requests.post(url, json=data)
print(response.text)
```

### ارسال مخاطب (sendContact)
```python
import requests

data = {
    "chat_id": chat_id,
    "first_name": first_name,
    "last_name": last_name,
    "phone_number": phone_number,
}
url = f"https://botapi.rubika.ir/v3/{token}/sendContact"
response = requests.post(url, json=data)
print(response.text)
```

### گرفتن اطلاعات چت (getChat)
```python
import requests

data = {"chat_id": chat_id}
url = f"https://botapi.rubika.ir/v3/{token}/getChat"
response = requests.post(url, json=data)
print(response.text)
```

### گرفتن آخرین آپدیت‌ها (getUpdates)
```python
import requests

data = {"limit": limit}
url = f"https://botapi.rubika.ir/v3/{token}/getUpdates"
response = requests.post(url, json=data)
print(response.text)
```

### فوروارد پیام (forwardMessage)
```python
import requests

data = {"from_chat_id": chat_id, "message_id": message_id, "to_chat_id": to_chat_id}
url = f"https://botapi.rubika.ir/v3/{token}/forwardMessage"
response = requests.post(url, json=data)
print(response.text)
```

### ویرایش متن پیام (editMessageText)
```python
import requests

data = {"chat_id": chat_id, "message_id": message_id, "text": "this is my new text"}
url = f"https://botapi.rubika.ir/v3/{token}/editMessageText"
response = requests.post(url, json=data)
print(response.text)
```

### ویرایش InlineKeypad (editMessageKeypad)
```python
import requests

data = {
    "chat_id": chat_id,
    "message_id": message_id,
    "inline_keypad": {
        "rows": [{"buttons": [{"id": "100", "type": "Simple", "button_text": "Add Account"}]}]
    },
}
url = f"https://botapi.rubika.ir/v3/{token}/editMessageKeypad"
response = requests.post(url, json=data)
print(response.text)
```

### حذف پیام (deleteMessage)
```python
import requests

data = {"chat_id": chat_id, "message_id": message_id}
url = f"https://botapi.rubika.ir/v3/{token}/deleteMessage"
response = requests.post(url, json=data)
print(response.text)
```

### تنظیم دستورات (setCommands)
```python
import requests

data = {
    "bot_commands": [
        {"command": "command1", "description": "description1"},
        {"command": "command2", "description": "description2"},
    ]
}
url = f"https://botapi.rubika.ir/v3/{token}/setCommands"
response = requests.post(url, json=data)
print(response.text)
```

### آپدیت آدرس بات (updateBotEndpoints)
```python
import requests

data = {"endpoints": [{"url": "https://example.com/receiveUpdate", "type": "ReceiveUpdate"}]}
url = f"https://botapi.rubika.ir/v3/{token}/updateBotEndpoints"
response = requests.post(url, json=data)
print(response.text)
```

### حذف/ویرایش Keypad (editChatKeypad)
```python
import requests

data = {"chat_id": chat_id, "chat_keypad_type": "Remove"}
url = f"https://botapi.rubika.ir/v3/{token}/editChatKeypad"
response = requests.post(url, json=data)
print(response.text)
```

### دریافت فایل (getFile)
```python
import requests

data = {"file_id": file_id}
url = f"https://botapi.rubika.ir/v3/{token}/getFile"
response = requests.post(url, json=data)
print(response.text)
```

### ارسال فایل (sendFile)
```python
import requests

data = {"chat_id": chat_id, "file_id": file_id}
url = f"https://botapi.rubika.ir/v3/{token}/sendFile"
response = requests.post(url, json=data)
print(response.text)
```

### آپلود فایل (requestSendFile)
```python
import requests

data = {"type": "Image"}
url = f"https://botapi.rubika.ir/v3/{token}/requestSendFile"
response = requests.post(url, json=data)
print(response.text)
```

### مسدود/رفع مسدودیت (banChatMember/unbanChatMember)
```python
import requests

data = {"chat_id": chat_id, "user_id": user_id}
ban_url = f"https://botapi.rubika.ir/v3/{token}/banChatMember"
unban_url = f"https://botapi.rubika.ir/v3/{token}/unbanChatMember"
print(requests.post(ban_url, json=data).text)
print(requests.post(unban_url, json=data).text)
```

## توضیح عملی

### A) بن کردن کاربر اگر لینک ارسال کرد (Anti Link)

1. پیام ورودی از JSON وبهوک استخراج می‌شود.
2. متن پیام با Regex بررسی می‌شود.
3. اگر لینک بود:
   - `deleteMessage(chat_id, message_id)`
   - `banChatMember(chat_id, user_id)`

Regex ساده و قدرتمند:

```
https?:// | www. | دامنه با پسوند
```

### B) حذف پیام انبوه با `/del 1000`

- هر پیام دریافتی در SQLite ذخیره می‌شود.
- دستور `/del 1000` آخرین 1000 پیام ثبت‌شده را خوانده و در Batch حذف می‌کند.
- حذف به صورت مرحله‌ای انجام می‌شود تا فشار به API کم شود.

## مثال‌های cURL

```bash
curl -X POST https://botapi.rubika.ir/v3/{token}/sendMessage \
  -H "Content-Type: application/json" \
  -d '{"chat_id": "123", "text": "سلام"}'
```

## مثال Python

```python
import httpx

TOKEN = "..."
url = f"https://botapi.rubika.ir/v3/{TOKEN}/sendMessage"

payload = {"chat_id": "123", "text": "سلام"}
response = httpx.post(url, json=payload)
print(response.json())
```

## CLI استقرار (botctl)

دستورهای اصلی:

```bash
python -m app.cli.botctl quickstart
python -m app.cli.botctl setup
python -m app.cli.botctl run
python -m app.cli.botctl deploy --path /opt/rubika_bot --source .
python -m app.cli.botctl rollback --path /opt/rubika_bot
python -m app.cli.botctl status
python -m app.cli.botctl logs
```

## استقرار Production (Nginx + SSL + systemd)

### 1) ساخت سرویس systemd

`/etc/systemd/system/rubika-bot.service`

```ini
[Unit]
Description=Rubika Bot
After=network.target

[Service]
User=www-data
WorkingDirectory=/opt/rubika_bot
Environment=RUBIKA_BOT_TOKEN=YOUR_TOKEN
Environment=RUBIKA_API_BASE_URL=https://botapi.rubika.ir/v3
Environment=RUBIKA_WEBHOOK_BASE_URL=https://your-domain.example
ExecStart=/opt/rubika_bot/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8080
Restart=always

[Install]
WantedBy=multi-user.target
```

### 2) تنظیم Nginx

```nginx
server {
    listen 443 ssl;
    server_name your-domain.example;

    ssl_certificate /etc/letsencrypt/live/your-domain/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 3) فعال‌سازی

```bash
sudo systemctl daemon-reload
sudo systemctl enable rubika-bot
sudo systemctl start rubika-bot
```

## تست‌ها

```bash
pytest
```

---

### یادآوری مهم
برای مدیریت گروه، بات باید در گروه ادمین باشد و مجوز حذف پیام/بن را داشته باشد.
