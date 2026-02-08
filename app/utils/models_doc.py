from __future__ import annotations

MODELS_DOC = """پرش به محتویات
logo
بات روبیکا
مدل ها


بات روبیکا
معرفی
متد ها
مدل ها
گروه ها و کانال ها
فهرست موضوعات
Chat
File
ForwardedFrom
MessageTextUpdate
Bot
BotCommand
Sticker
ContactMessage
PollStatus
Poll
Location
ButtonSelectionItem
ButtonSelection
ButtonCalendar
ButtonNumberPicker
ButtonStringPicker
ButtonTextbox
ButtonLocation
AuxData
Button
ButtonTypeEnum
KeypadRow
Keypad
MessageKeypadUpdate
Message
Update
InlineMessage
Enums
ChatTypeEnum
FileTypeEnum
ForwardedFromEnum
PollStatusEnum
ButtonSelectionTypeEnum
ButtonSelectionSearchEnum
ButtonSelectionGetEnum
ButtonCalendarTypeEnum
ButtonTextboxTypeKeypadEnum
ButtonTextboxTypeLineEnum
ButtonLocationTypeEnum
MessageSenderEnum
UpdateTypeEnum
ChatKeypadTypeEnum
UpdateEndpointTypeEnum
مدل ها
Chat¶
فیلد	نوع	توضیحات
chat_id	str	شناسه چت
chat_type	ChatTypeEnum	نوع چت
user_id	str	شناسه کاربر
first_name	str	نام کاربر
last_name	str	نام خانوادگی
title	str	عنوان
username	str	نام کاربری
File¶
فیلد	نوع	توضیحات
file_id	str	شناسه فایل
file_name	str	نام فایل
size	str	حجم فایل (به فرمت Bytes)
ForwardedFrom¶
فیلد	نوع	توضیحات
type_from	ForwardedFromEnum	نوع فوروارد
message_id	str	شناسه پیام
from_chat_id	str	شناسه چت
from_sender_id	str	شناسه کاربر
MessageTextUpdate¶
فیلد	نوع	توضیحات
message_id	str	شناسه پیام
text	str	متن پیام
Bot¶
فیلد	نوع	توضیحات
bot_id	str	شناسه
bot_title	str	عنوان
avatar	File	تصویر
description	str	توضیحات
username	str	نام‌کاربری ربات
start_message	str	پیام اولیه
share_url	str	آدرسِ اشتراک‌گذاری
BotCommand¶
فیلد	نوع	توضیحات
command	str	متن دستور
description	str	توضیحات دستور
Sticker¶
فیلد	نوع	توضیحات
sticker_id	str	شناسه استیکر
file	File	فایل
emoji_character	str	کاراکترِ اموجی
ContactMessage¶
فیلد	نوع	توضیحات
phone_number	str	شماره تلفن
first_name	str	نام
last_name	str	نام خانوادگی
PollStatus¶
فیلد	نوع	توضیحات
state	PollStatusEnum	وضعیت نظرسنجی
selection_index	int	1- به معنی انتخاب نشده است.
percent_vote_options	list[int]	...
total_vote	int	تعداد کل آراء نظرسنجی
show_total_votes	bool	نمایش تمام آرا؟
Poll¶
فیلد	نوع	توضیحات
question	str	متن نظرسنجی
options	list[str]	گزینه‌های نظرسنجی
poll_status	PollStatus	وضعیت نظرسنجی
Location¶
فیلد	نوع	توضیحات
longitude	str	طول جغرافیایی
latitude	str	عرض جغرافیایی
ButtonSelectionItem¶
فیلد	نوع	توضیحات
text	str	متن دکمه
image_url	str	آدرس عکس دکمه
type	ButtonSelectionTypeEnum	نوع نمایش دکمه
ButtonSelection¶
فیلد	نوع	توضیحات
selection_id	str	شناسه مربوط به لیست
search_type	str	نوع جستجو
get_type	str	نوع دریافت آیتم‌های لیست
items	list[ButtonSelectionItem]	آرایه‌ای از ButtonSelectionItem ها
is_multi_selection	bool	امکان انتخاب چند آیتم
columns_count	str	تعداد ستون‌های لیست
title	str	عنوان
ButtonCalendar¶
فیلد	نوع	توضیحات
default_value	Optional[str]	مقدار پیشفرض تقویم
type	ButtonCalendarTypeEnum	نوع تقویم
min_year	str	مقدار کمینه تقویم
max_year	str	مقدار بیشینه تقویم
title	str	عنوان دکمه
ButtonNumberPicker¶
فیلد	نوع	توضیحات
min_value	str	مقدار کمینه
max_value	str	مقدار بیشینه
default_value	Optional[str]	مقدار پیشفرض
title	str	عنوان دکمه
ButtonStringPicker¶
فیلد	نوع	توضیحات
items	list[str]	آرایه‌ای از متن‌ها
default_value	Optional[str]	مقدار پیشفرض
title	Optional[str]	عنوان دکمه
ButtonTextbox¶
فیلد	نوع	توضیحات
type_line	ButtonTextboxTypeLineEnum	نوع وارد کردن پیام
type_keypad	ButtonTextboxTypeKeypadEnum	نوع صفحه کلید
place_holder	Optional[str]	...
title	Optional[str]	عنوان دکمه
default_value	Optional[str]	مقدار پیشفرض
ButtonLocation¶
فیلد	نوع	توضیحات
default_pointer_location	Location	...
default_map_location	Location	موقعیت پیشفرض نقشه
type	ButtonLocationTypeEnum	نوع نقشه
title	Optional[str]	عنوان دکمه
location_image_url	str	...
AuxData¶
فیلد	نوع	توضیحات
start_id	str	شناسه جهت دسترسی سریع
button_id	str	شناسه دکمه
Button¶
فیلد	نوع	توضیحات
id	str	شناسه دکمه
type	ButtonTypeEnum	نوع دکمه
button_text	str	متن دکمه
button_selection	ButtonSelection	...
button_calendar	ButtonCalendar	...
button_number_picker	ButtonNumberPicker	...
button_string_picker	ButtonStringPicker	...
button_location	ButtonLocation	...
button_textbox	ButtonTextbox	...
ButtonTypeEnum¶
فیلد	توضیحات
Simple	str	نمایش دکمه به صورت معمولی
Selection	str	نمایش دکمه به صورت لیست
Calendar	str	نمایش دکمه به صورت تقویم
NumberPicker	str	نمایش دکمه به صورت لیستی از اعداد
StringPicker	str	نمایش دکمه به صورت لیستی از string
Location	str	...
CameraImage	str	نمایش دکمه جهت عکسبرداری با دوربین
CameraVideo	str	نمایش دکمه جهت فیلمبرداری با دوربین
GalleryImage	str	نمایش دکمه جهت ارسال عکس از گالری
GalleryVideo	str	نمایش دکمه جهت ارسال فیلم از گالری
File	str	نمایش دکمه جهت ارسال فایل
Audio	str	نمایش دکمه جهت ارسال صوت
RecordAudio	str	نمایش دکمه جهت ضبط صوت
Textbox	str	نمایش دکمه جهت وارد کردن پیام متنی
Link	str	نمایش دکمه جهت ارسال آدرس اینترنتی
AskMyPhoneNumber	str	...
AskMyLocation	str	...
Barcode	str	نمایش دکمه جهت اسکن بارکد
KeypadRow¶
فیلد	نوع	توضیحات
buttons	list[Button]	آرایه‌ای از دکمه‌ها
Keypad¶
فیلد	نوع	توضیحات
rows	list[KeypadRow]	آرایه‌ای از ردیف keypad ها
resize_keyboard	bool	تغییر اندازه و ارتفاع دکمه‌ها
one_time_keyboard	bool	بسته شدن خودکار کیبورد بعد از اولین انتخاب
MessageKeypadUpdate¶
فیلد	نوع	توضیحات
message_id	str	شناسه پیام
inline_keypad	Keypad	keypad جدید
Message¶
فیلد	نوع	توضیحات
message_id	str	شناسه پیام
text	str	متن پیام
time	int	زمان
is_edited	bool	آیا ویرایش شده است؟
sender_type	MessageSenderEnum	نوع فرستنده
sender_id	str	شناسه فرستنده
aux_data	AuxData	...
file	File	فایل
reply_to_message_id	str	در جوابِ پیامِ؟
forwarded_from	ForwardedFrom	فوروارد شده از‌ طرف؟
forwarded_no_link	str	...
location	Location	موقعیت مکانی
sticker	Sticker	استیکر
contact_message	ContactMessage	...
poll	Poll	نظرسنجی
Update¶
فیلد	نوع	توضیحات
type	UpdateTypeEnum	نوع آپدیت
chat_id	str	شناسه چت
removed_message_id	Optional[str]	شناسه پیام پاک شده
new_message	Message	پیام جدید
updated_message	Optional[Message]	پیام ویرایش شده
InlineMessage¶
فیلد	نوع	توضیحات
sender_id	str	شناسه فرستنده
text	str	متن
file	Optional[File]	فایل
location	Optional[Location]	...
aux_data	Optional[AuxData]	...
message_id	str	شناسه پیام
chat_id	str	شناسه چت
Enums¶
ChatTypeEnum¶
فیلد	توضیحات
User	چت با کاربر
Bot	چت با ربات
Group	چت در گروه
Channel	چت در کانال
FileTypeEnum¶
فیلد	توضیحات
File	فایل‌های عمومی با حداکثر حجم 50 مگابایت.
Image	عکس با فرمت jpg، gif، png یا webp با حداکثر حجم 10 مگابایت.
Voice	پیام صوتی کوتاه با فرمت mp3.
Video	فیلم با فرمت mp4 با حداکثر حجم 50 مگابایت.
Music	آهنگ با فرمت mp3.
Gif	تصویر متحرک با فرمت mp4 که حتماً باید بدون صدا باشد.
ForwardedFromEnum¶
فیلد	توضیحات
User	فوروارد از کاربر
Channel	فوروارد از کانال
Bot	فوروارد از ربات
فیلد	توضیحات
Paid	پرداخت شده
NotPaid	پرداخت نشده
PollStatusEnum¶
فیلد	توضیحات
Open	نظرسنجی باز است.
Closed	نظرسنجی بسته شده است.
ButtonSelectionTypeEnum¶
فیلد	توضیحات
TextOnly	نمایش دکمه به صورت متن
TextImgThu	نمایش دکمه به صورت متن و عکس کوچک
TextImgBig	نمایش دکمه به صورت متن و عکس بزرگ
ButtonSelectionSearchEnum¶
فیلد	توضیحات
None	حالت پیشفرض
Local	جستجو در آیتم‌های لیست با استفاده از مقادیر ارسالی در فیلد items
Api	جستجو در آیتم‌های لیست از طریق Api
ButtonSelectionGetEnum¶
فیلد	توضیحات
Local	نمایش آیتم‌های لیست با استفاده از مقادیر ارسالی در فیلد items
Api	جستجو در آیتم‌های لیست از طریق Api
ButtonCalendarTypeEnum¶
فیلد	توضیحات
DatePersian	نمایش تقویم به فرمت شمسی
DateGregorian	نمایش تقویم به فرمت میلادی
ButtonTextboxTypeKeypadEnum¶
فیلد	نوع	توضیحات
String	str	امکان ارسال تمامی کاراکتر ها
Number	str	امکان ارسال کاراکترها عددی
ButtonTextboxTypeLineEnum¶
فیلد	نوع	توضیحات
SingleLine	str	نوشتن پیام متنی در یک سطر
MultiLine	str	نوشتن پیام متنی در چندین سطر
ButtonLocationTypeEnum¶
فیلد	توضیحات
Picker	...
View	...
MessageSenderEnum¶
فیلد	توضیحات
User	کاربر
Bot	بات
UpdateTypeEnum¶
فیلد	توضیحات
UpdatedMessage	ویرایش پیام
NewMessage	پیام جدید
RemovedMessage	حذف پیام
StartedBot	شروع بات
StoppedBot	توقف بات
ChatKeypadTypeEnum¶
فیلد	توضیحات
None	مقدار پیشفرض
New	اضافه کردن keypad جدید
Remove	حذف keypad
UpdateEndpointTypeEnum¶
فیلد	توضیحات
ReceiveUpdate	ReceiveUpdate
ReceiveInlineMessage	ReceiveInlineMessage
ReceiveQuery	ReceiveQuery
GetSelectionItem	GetSelectionItem
SearchSelectionItems	SearchSelectionItems
قبلیمتدها
بعدیگروه ها و کانال ها
"""
