# Rubica Bot API v3 (PRO)

پروژه‌ی **Rubica Bot API v3** یک فریم‌ورک Production-Ready برای ساخت بات روبیکا است که روی **Webhook** طراحی شده و هدف آن **سرعت بالا، نصب یک‌خطی، Docker حرفه‌ای، و قابلیت مانیتورینگ/عیب‌یابی کامل** است.

## چرا سریع؟

- Ack زیر 100ms با صف داخلی و Worker Pool
- Rate-limit داخلی و Retry هوشمند برای API
- SQLite بهینه (WAL + retention) و janitor داخلی
- لاگ چرخشی و خروجی استاندارد برای observability

---

## نصب سریع (۳ حالت)

### 1) Docker (پیشنهادی)

```bash
cp .env.example .env
# فقط این‌ها را تنظیم کنید
# RUBIKA_BOT_TOKEN=...
# RUBIKA_OWNER_ID=...
# RUBIKA_WEBHOOK_BASE_URL=https://your-domain.example

docker compose up -d --build
```

پورت پیش‌فرض: `8080`

### 2) نصب لینوکس با Wizard (ترمینال حرفه‌ای)

```bash
python3 install.py
```

### 3) اجرای دستی با venv

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

---

## Easy Setup Wizard (یک‌خطی)

**نصب مستقیم از GitHub با curl | bash**

```bash
curl -fsSL https://raw.githubusercontent.com/Opselon/rubica-bot/main/install.sh | bash -s -- \
  --non-interactive \
  --token YOUR_TOKEN \
  --owner-id YOUR_OWNER_ID \
  --webhook-base-url https://your-domain.example
```

**فقط این ۳ مقدار لازم است:**
- `TOKEN`
- `OWNER_ID`
- `WEBHOOK_BASE_URL`

### حالت تست (بدون روت و قابل اتوماسیون)

```bash
curl -fsSL https://raw.githubusercontent.com/Opselon/rubica-bot/main/install.sh | bash -s -- \
  --non-interactive \
  --test-mode \
  --install-path ./sandbox \
  --token TEST_TOKEN \
  --owner-id 123456 \
  --webhook-base-url https://example.test
```

> حالت تست: systemd/nginx به‌صورت mock اجرا می‌شوند و نیاز به دسترسی root ندارد.

---

## CLI مدیریت (rubikactl)

```bash
python -m app.cli.rubikactl install
python -m app.cli.rubikactl configure
python -m app.cli.rubikactl status
python -m app.cli.rubikactl logs -f
python -m app.cli.rubikactl doctor
```

نمونه‌های پرکاربرد:

```bash
python -m app.cli.rubikactl doctor --path /opt/rubika-bot --port 8080
python -m app.cli.rubikactl db stats --path /opt/rubika-bot
python -m app.cli.rubikactl db cleanup --days 2 --keep-per-chat 10000
```

---

## Docker Compose (Production)

```yaml
services:
  rubica-bot:
    build: .
    env_file: .env
    environment:
      RUBIKA_DB_URL: sqlite:///data/bot.db
      RUBIKA_REGISTER_WEBHOOK: "false"
    ports:
      - "8080:8080"
    volumes:
      - rubica-data:/data
```

> برای ثبت وبهوک در Production، مقدار `RUBIKA_WEBHOOK_BASE_URL` را در `.env` تنظیم کنید.

---

## عیب‌یابی (Troubleshooting)

- **خطای getMe:** توکن اشتباه است یا شبکه دسترسی ندارد.
- **صف پر شده:** `rubikactl doctor` را اجرا کنید و اندازه Queue را بررسی کنید.
- **DB حجیم شده:**
  ```bash
  python -m app.cli.rubikactl db cleanup --days 2 --keep-per-chat 10000
  ```
- **systemd فعال نیست:**
  ```bash
  systemctl status rubika-bot
  ```
- **nginx مشکل دارد:**
  ```bash
  nginx -t
  ```

---

## امنیت

- **TOKEN** را در فایل `.env` نگه دارید و هرگز در کد منتشر نکنید.
- وبهوک را پشت **HTTPS** و ترجیحاً با `RUBIKA_WEBHOOK_SECRET` فعال کنید.
- بات باید **حداقل دسترسی** لازم (حذف پیام/بن) را داشته باشد.
- اگر از Docker استفاده می‌کنید، `.env` را در host امن نگه دارید.

---

## ساختار پروژه

```
app/
  cli/              ابزار rubikactl
  db/               مهاجرت‌ها + Repository
  services/         کلاینت API، dispatcher و handler ها
  services/plugins/ پلاگین‌ها
  utils/            ابزارهای عمومی
  webhook/          روت‌های وبهوک
  main.py           نقطه ورود FastAPI
requirements.txt
tests/
install.sh
```

---

## تست‌ها

```bash
python -m pytest -m "not e2e"
python -m pytest -m e2e
```

اجرای تست نصب یک‌خطی:

```bash
./scripts/test_install.sh
```

---

### یادآوری مهم
بات باید در گروه ادمین باشد تا حذف پیام و بن کردن عمل کند.
