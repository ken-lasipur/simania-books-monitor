# Simania Books Monitor 📚

בוט שעוקב אחרי עדכונים בסימניה לרשימת ספרים שלי, ושולח מייל בכל פעם שספר מהרשימה מתעדכן.

## איך זה עובד

- רץ אוטומטית כל 3 שעות ב-GitHub Actions (בענן, ללא תלות במחשב)
- בודק כל ספר ברשימה מול ה-API של סימניה
- שומר state כדי לא לפספס ספרים גם אם הריצה דילגה
- שולח מייל מעוצב כשנמצא עדכון

## הגדרה ראשונית

הוספת Secrets ב-GitHub (Settings → Secrets and variables → Actions):
- `GMAIL_USER` — כתובת הג'ימייל ששולחת
- `GMAIL_APP_PASSWORD` — סיסמת האפליקציה (16 תווים)
- `RECIPIENT_EMAIL` — כתובת המייל שמקבלת התראות

## הפעלה ידנית

מהטאב Actions → "Check Simania Books" → "Run workflow"
