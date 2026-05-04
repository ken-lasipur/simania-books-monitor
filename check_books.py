"""
בודק עדכונים בסימניה ושולח מייל אם נמצאו ספרים מהרשימה.
שומר state בקובץ last_run.json — אז לא משנה כמה זמן עבר מהריצה האחרונה,
לא יוחמצו ספרים ולא יישלחו התראות כפולות על אותו ספר.
"""

import requests
import smtplib
import json
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from zoneinfo import ZoneInfo

ISRAEL_TZ = ZoneInfo("Asia/Jerusalem")
UTC = ZoneInfo("UTC")
STATE_FILE = "last_run.json"

# ברירת מחדל: 4 שעות אחורה (חופף עם ריצה כל 3 שעות + מרווח ביטחון)
DEFAULT_WINDOW_HOURS = 4
# גג עליון: לא נחפש יותר מ-7 ימים אחורה גם אם הסקריפט לא רץ הרבה זמן
MAX_WINDOW_HOURS = 24 * 7

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://simania.co.il/",
}

MY_BOOKS = [
    # רשימה מקורית
    "יהודי-יער", "ספר התשובות", "ששת", "קוסם: רב-מג",
    "גילס האכר מפרזון", "יוביק", "גני הירח",
    "ואליס", "המיתולוגיה הכנענית", "בחזרה לבראשית",
    "כוכב הנפילים",
    # עדכון שני
    "נתיב התהילה", "לוחמי החלל", "חליפת חלל", "התוהו המזדחל",
    "ספר הזכרונות של מומינאבא", "דור ההמשך", "כוכב השביט מגיע לעמק המומינים",
    "קיץ מסכן (מסוכן) בעמק המומינים", "משפחת החיות המוזרות (1989)",
    "ספורי משפחת החיות המוזרות (1988)", "סיפורי משפחת החיות המוזרות",
    "עמק החיות המוזרות (פורמט אלבומי)", "המומינים - הטיול של המכשפה",
    "עמק החיות המוזרות (1967)", "הדרקון האחרון בעולם", "העננים המכושפים",
    "מי ינחם את קטנטן", "הספר על בימבל מומינטרול ומאי הקטנה",
    "ספר הפוקר הירוק", "מושבות האבן", "כשל-זמן", "המעבר הירוק",
    "לגיון הארגמן", "חמישיית הצבעים - כרך 3 - מכשפת העינבר (הענבר)",
    "אורקל הבזלת", "סופת התכלת", "חמישיית הצבעים סט מלא (5 כרכים)",
    "סכין החלומות", "עגור הזהב", "מחזור כישור הזמן - סט מלא - כרכים 1-22",
    "שועי הלילה", "רצון הנודד", "אחראן ונביאו",
    "רצון הנודד / שועי הלילה / אחראן ונביאו", "ננסי הכנפיים",
    "טרילוגיית הננסים - שלושה כרכים", "ננסי המכרות", "ננסי המשאית", "הגביע והלהב",
    # עדכון שלישי
    "אחיות הגורל", "בני החורין הקטנים", "אלבש חצות ליל", "כתר הרועים",
    "חרש החורף", "איש הקציר", "ראי נוע", "נשמות אחיות",
    "תאוות נדודים", "לב אפל", "השבועה והמידה", "פלדה ואבן", "החבורה",
    # עדכון רביעי
    "צוערי החלל", "מספר החיה: 666", "דרך התהילה", "טירת האימים",
    "שער הזדון", "במבוך", "חולשחור", "מאורותיה של מכשפת השלג",
    "מכשפת השלג", "שדי התהום", "מלכודת מוות במבוך", "מסיכות מייהאם",
    "שודדי חצות", "רוצח בחלל", "מסעות החללית \"הנודד\"",
    "מאבק הנסיכים - דרך הלוחם", "מאבק הנסיכים - דרך המכשף",
    "המכשף מפסגת הר האש", "ככה למדתי לעוף", "מפלצות הביצים ממאדים",
    "אל תלכו לישון!", "צמרמורת 46",
    # עדכון חמישי
    "הקמיע מסמרקנד", "עינו של הגולם", "שער תלמי",
    # עדכון שישי
    "כישוף אדום", "ים החרבה", "הסילמריליון", "החרב המוכתמת",
    "קבר הדרקון", "כליון הקסם", "מבוכים ודרקונים",
    "ספר החוקים לשחקן", "תיבת האוצרות: ציוד וכלי נשק לכל המקצועות",
    "החברה הנסתרת 6", "מבוכים ודרקונים - ספר החוקים לשחקן",
    "מבוכים ודרקונים - מגדיר המפלצות - ספר חוקים בסיסי III - גרסה 3.5",
    "מבוכים ודרקונים - המדריך לשליט המבוך",
    "מבוכים ודרקונים - מגדיר המפלצות",
    "מבוכים ודרקונים מורחב : מדריך לשליט המבוך",
    "מבוכים ודרקונים - המדריך השלם ללוחמה",
    "מבוכים ודרקונים : אוגדן הכללים",
    "מבוכים ודרקונים - מדריך לשחקן",
    "מבוכים ודרקונים - מגדיר המפלצות 2",
    "הרפתקאות תום בומבדיל", "הנפח מווטון רבא", "עץ ועלה",
    "סיפורים מממלכת הסכנה",
    "טינטין - אוצרו של רקהם האדום", "שרביטו של אוטוקר",
    "תעלומת החד-קרן", "הכוכב המסתורי", "האי השחור",
    "טיסה 714 לסידני", "הטיסה לירח (הוצאת מקורית 1987)",
    "כרישי הים האדום", "פרשת קלקולוס", "תעלומת תכשיטי הזמרת",
    "אסירי השמש", "החוקרים על הירח", "שבעת כדורי הבדולח",
    "קרן ואלר", "עם עלות השחר", "עת לברזל", "אדון הכאוס",
    "כס האמירלין", "שובו של הדרקון", "היציאה מהשממה",
    "האופל", "אש הרקיע", "האמירלין הצעירה", "לב האבן", "אלנטריס",
    # עדכון שביעי
    "כתבי אייזק אסימוב (כרך 1)", "כתבי אייזק אסימוב (כרך 2)",
    "כתבי אייזק אסימוב (כרך 3)", "כתבי אייזק אסימוב (כרך 4)",
    "האלים עצמם", "אבן בשחקים", "זרמי חלל", "מחר כפול תשע",
    "מערות הפלדה", "שמש ערמה", "אין איש פה, פרט...",
    "סוף הנצח", "הכוכבים כאבק", "אופוס 200", "לאקי סטאר",
    # עדכון שמיני
    "מיילדות רוחנית", "מצור האפלה",
]


def load_state():
    """טעינת תאריך הריצה האחרונה (אם קיים)"""
    if not os.path.exists(STATE_FILE):
        return None
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return datetime.fromisoformat(data["last_run"])
    except Exception as e:
        print(f"⚠️ שגיאה בטעינת state: {e}")
        return None


def save_state(notified_book_ids):
    """שמירת תאריך הריצה הנוכחית + ספרים שכבר התרענו עליהם"""
    data = {
        "last_run": datetime.now(tz=UTC).isoformat(),
        "notified_book_ids": notified_book_ids,
    }
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_notified_ids():
    """טעינת מזהי ספרים שכבר נשלחה עליהם התראה"""
    if not os.path.exists(STATE_FILE):
        return set()
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return set(data.get("notified_book_ids", []))
    except Exception:
        return set()


def calculate_window_hours():
    """חישוב חלון בדיקה: מהריצה האחרונה ועד עכשיו, או ברירת מחדל"""
    last_run = load_state()
    if last_run is None:
        return DEFAULT_WINDOW_HOURS

    now = datetime.now(tz=UTC)
    diff = now - last_run
    hours = diff.total_seconds() / 3600

    # מרווח ביטחון של שעה (ליתר ביטחון על חפיפה)
    hours = hours + 1

    # לא פחות מברירת המחדל, לא יותר מהמקסימום
    return max(DEFAULT_WINDOW_HOURS, min(hours, MAX_WINDOW_HOURS))


def check_book(book_name, cutoff):
    """בדיקת ספר אחד מול סימניה"""
    # ספרים שאנחנו רוצים לדבג עליהם בעומק
    DEBUG = book_name in ["מצור האפלה"]

    try:
        r = requests.get(
            f"https://simania.co.il/api/search?query={book_name}",
            headers=headers, timeout=10
        )
        if DEBUG:
            print(f"\n🔬 DEBUG [{book_name}]: search status={r.status_code}")

        if r.status_code != 200 or not r.text.strip():
            return None

        books = r.json().get("data", {}).get("books", [])

        if DEBUG:
            print(f"🔬 DEBUG [{book_name}]: מצא {len(books)} תוצאות")
            for i, b in enumerate(books[:5]):
                print(f"   {i+1}. ID={b.get('ID')} | NAME={b.get('NAME')}")

        if not books:
            return None

        book_id = books[0]["ID"]
        r2 = requests.get(
            f"https://simania.co.il/api/book/{book_id}/sellers",
            headers=headers, timeout=10
        )

        if DEBUG:
            print(f"🔬 DEBUG [{book_name}]: בודק sellers של ID={book_id}, status={r2.status_code}")

        if r2.status_code != 200 or not r2.text.strip():
            return None

        sellers = r2.json().get("sellers", [])

        if DEBUG:
            print(f"🔬 DEBUG [{book_name}]: מצא {len(sellers)} מוכרים")
            for i, s in enumerate(sellers[:5]):
                print(f"   מוכר {i+1}: updatedAt={s.get('updatedAt')}")
            print(f"🔬 DEBUG [{book_name}]: cutoff={cutoff}")

        for s in sellers:
            try:
                raw = s["updatedAt"]
                updated_naive = datetime.strptime(raw[:24], "%a %b %d %Y %H:%M:%S")
                updated = updated_naive.replace(tzinfo=UTC)
                if DEBUG:
                    print(f"   → seller updated={updated}, cutoff={cutoff}, match={updated >= cutoff}")
                if updated >= cutoff:
                    return {
                        "book_name": book_name,
                        "book_id": book_id,
                        "url": f"https://simania.co.il/book/{book_id}",
                        "updated_at": updated.astimezone(ISRAEL_TZ).strftime("%d/%m/%Y %H:%M"),
                    }
            except Exception as e:
                if DEBUG:
                    print(f"   ⚠️ שגיאה בפארסינג תאריך: {e}")
                pass

    except Exception as e:
        print(f"⚠️ שגיאה ב-{book_name}: {e}")

    return None


def send_email(found_books):
    """שליחת מייל עם הספרים שנמצאו"""
    sender = os.environ["GMAIL_USER"]
    password = os.environ["GMAIL_APP_PASSWORD"]
    recipient = os.environ["RECIPIENT_EMAIL"]

    subject = f"🔥 נמצאו {len(found_books)} ספרים חדשים בסימניה!"

    html = """
    <html dir="rtl">
    <body style="font-family: Arial, sans-serif; background: #f7f5f0; padding: 20px;">
    <div style="max-width: 600px; margin: auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.05);">
    <h2 style="color: #2d1b5e;">📚 ספרים חדשים שזיהינו בסימניה</h2>
    <p style="color: #666;">להלן הספרים מרשימת המעקב שעודכנו לאחרונה:</p>
    <ul style="list-style: none; padding: 0;">
    """

    for book in found_books:
        html += f"""
        <li style="background: #fdf6e3; margin: 10px 0; padding: 15px; border-right: 4px solid #d4a574; border-radius: 6px;">
            <strong style="font-size: 16px; color: #2d1b5e;">{book['book_name']}</strong><br>
            <span style="color: #888; font-size: 13px;">עודכן: {book['updated_at']}</span><br>
            <a href="{book['url']}" style="color: #d4567a; text-decoration: none; font-weight: bold;">→ צפה בסימניה</a>
        </li>
        """

    html += """
    </ul>
    <p style="color: #aaa; font-size: 12px; margin-top: 30px;">
    הודעה אוטומטית ממערכת המעקב של סימניה
    </p>
    </div>
    </body>
    </html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = recipient
    msg.attach(MIMEText(html, "html", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender, password)
        server.sendmail(sender, recipient, msg.as_string())

    print(f"📧 מייל נשלח אל {recipient}")


def main():
    now = datetime.now(tz=ISRAEL_TZ)
    window_hours = calculate_window_hours()
    cutoff = datetime.now(tz=UTC) - timedelta(hours=window_hours)

    print(f"🕐 זמן בדיקה: {now.strftime('%d/%m/%Y %H:%M:%S')} (שעון ישראל)")
    print(f"📅 חלון בדיקה: {window_hours:.1f} שעות אחורה")
    print(f"🔍 בודק {len(MY_BOOKS)} ספרים...\n")

    already_notified = load_notified_ids()
    print(f"💾 ספרים שכבר התרענו עליהם: {len(already_notified)}\n")

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda b: check_book(b, cutoff), MY_BOOKS))

    # סינון ספרים שכבר נשלחה עליהם התראה
    found = [r for r in results if r]
    new_books = [b for b in found if b["book_id"] not in already_notified]

    print(f"✅ נמצאו {len(found)} עדכונים, מתוכם {len(new_books)} חדשים")

    if new_books:
        for b in new_books:
            print(f"   📖 {b['book_name']} — {b['url']}")

        try:
            send_email(new_books)
        except Exception as e:
            print(f"❌ שגיאה בשליחת מייל: {e}")
            raise
    else:
        print("😴 אין ספרים חדשים להתריע עליהם")

    # עדכון state — שומרים את כל המזהים (גם הישנים) לטווח שמיש
    all_notified = list(already_notified | {b["book_id"] for b in found})
    # שמירה רק של 500 האחרונים כדי שהקובץ לא יתפח לאינסוף
    save_state(all_notified[-500:])
    print("💾 State נשמר")


if __name__ == "__main__":
    main()
