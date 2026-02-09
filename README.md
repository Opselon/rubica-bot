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
- **کنترل حرفه‌ای درخواست‌های API** با timeout، retry هوشمند، rate-limit و لاگ دقیق
- تست‌های End-to-End برای مسیرهای API و Moderation

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
export RUBIKA_OWNER_ID=YOUR_OWNER_ID
export RUBIKA_API_BASE_URL=https://botapi.rubika.ir/v3
export RUBIKA_WEBHOOK_BASE_URL=https://your-domain.example

uvicorn app.main:app --host 0.0.0.0 --port 8080
```

## نصب سریع با ویزارد (UI در ترمینال)

برای نصب کامل (ساخت venv، نصب وابستگی‌ها، ساخت .env، ساخت فایل systemd، ثبت وبهوک و اجرای تست‌ها) از ویزارد استفاده کنید:

```bash
python3 install.py
```

### دستور مستقیم لینوکس (بدون پرسش)

```bash
python3 install.py --non-interactive \
  --token YOUR_TOKEN \
  --owner-id YOUR_OWNER_ID \
  --webhook-base-url https://your-domain.example \
  --service-name rubika-bot \
  --host 0.0.0.0 \
  --port 8080
```

### دانلود از گیت‌هاب + نصب یکجا

```bash
python3 install.py \
  --github-repo https://github.com/your-org/rubica-bot \
  --install-path /opt/rubica-bot \
  --non-interactive \
  --token YOUR_TOKEN \
  --owner-id YOUR_OWNER_ID \
  --webhook-base-url https://your-domain.example
```

> خروجی `rubika-bot.service` در ریشه پروژه ایجاد می‌شود؛ در صورت نیاز با `--systemd-install` به‌صورت خودکار نصب و فعال می‌شود.

### کنترل و مدیریت با rubikactl

```bash
python3 -m app.cli.rubikactl status
python3 -m app.cli.rubikactl logs -f
python3 -m app.cli.rubikactl configure --path /opt/rubika-bot
python3 -m app.cli.rubikactl webhook-set --path /opt/rubika-bot
python3 -m app.cli.rubikactl update --path /opt/rubika-bot
python3 -m app.cli.rubikactl rollback --path /opt/rubika-bot
```

## تنظیم وبهوک و Endpoint

در `startup` اگر `RUBIKA_WEBHOOK_BASE_URL` تنظیم باشد، متد `updateBotEndpoints` برای ثبت آدرس‌های زیر فراخوانی می‌شود:

- `/receiveUpdate`
- `/receiveInlineMessage`

## امنیت و کنترل ترافیک

- **Signature**: اگر `RUBIKA_WEBHOOK_SECRET` تنظیم شود، امضای HMAC بررسی می‌شود.
- **Rate Limit**: محدودیت تعداد درخواست در دقیقه.
- **Dedup**: جلوگیری از پردازش تکراری آپدیت‌ها با TTL.
- **API Control**: تمام درخواست‌های روبیکا از `api_call` عبور می‌کند (timeout + retry + rate-limit + logging).
- **Log File**: خروجی‌ها به‌صورت پیش‌فرض در `/var/log/rubika-bot/app.log` ذخیره می‌شود (قابل تغییر با `RUBIKA_LOG_FILE`).

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

## تست‌ها

### اجرای تست‌های استاندارد

```bash
python -m pytest -m "not e2e"
```

### اجرای تست‌های End-to-End

```bash
python -m pytest -m e2e
```

### اجرای کامل

```bash
python -m pytest
```

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
- `/uptime` زمان اجرای بات
- `/stats` آمار پردازش
- `/echo` تکرار متن
- `/id` نمایش شناسه‌ها
- `/time` زمان سرور
- `/calc` محاسبه سریع
- `/about` نسخه بات
- `/settings` تنظیمات گروه
- `/admins` تعداد ادمین‌ها
- `/antilink on|off` مدیریت ضد لینک
- `/filter add|del|list <word>` مدیریت فیلترها
- `/del <n>` حذف انبوه پیام‌های اخیر
- `/ban <user_id>` / `/unban <user_id>`
- `/ping` / `/joke` / `/roll` / `/coin`

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

## متد کنترل حرفه‌ای Rubika API

تمام فراخوانی‌های API از متد مرکزی `api_call` عبور می‌کند تا رفتار استاندارد و پایدار داشته باشد:

- Timeout قابل تنظیم
- Retry هوشمند روی خطاهای موقتی (۵xx، ۴۰۸، ۴۲۹)
- Rate-limit داخلی برای جلوگیری از Flood
- لاگ‌گیری با جزئیات زمان پاسخ

نمونه:

```python
result = await client.api_call("sendMessage", {"chat_id": "123", "text": "سلام"})
if not result.get("ok", True):
    print("API error", result)
```

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
python -m app.cli.botctl deploy --path /opt/rubika_bot --source .
python -m app.cli.botctl rollback --path /opt/rubika_bot
python -m app.cli.botctl status
python -m app.cli.botctl logs
python -m app.cli.botctl check
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
