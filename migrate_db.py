from app import app, db
from models import TopicReservation

def migrate_database():
    with app.app_context():
        try:
            # Проверяем существование колонки expires_at
            from sqlalchemy import text
            conn = db.engine.connect()
            
            # Пытаемся выполнить запрос с expires_at
            try:
                conn.execute(text("SELECT expires_at FROM topic_reservation LIMIT 1"))
                print("✅ Колонка expires_at уже существует")
                return
            except:
                print("❌ Колонка expires_at не найдена, добавляем...")
            
            # Добавляем колонку expires_at
            conn.execute(text("ALTER TABLE topic_reservation ADD COLUMN expires_at DATETIME"))
            conn.close()
            
            print("✅ Колонка expires_at успешно добавлена")
            
        except Exception as e:
            print(f"❌ Ошибка миграции: {e}")

if __name__ == '__main__':
    migrate_database()