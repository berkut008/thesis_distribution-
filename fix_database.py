from app import app, db
from sqlalchemy import text

def fix_database():
    with app.app_context():
        try:
            # Проверяем существование колонки student_id
            conn = db.engine.connect()
            
            try:
                # Пытаемся выполнить запрос с student_id
                conn.execute(text("SELECT student_id FROM user LIMIT 1"))
                print("✅ Колонка student_id уже существует")
            except Exception as e:
                print("❌ Колонка student_id не найдена, добавляем...")
                # Добавляем колонку student_id
                conn.execute(text("ALTER TABLE user ADD COLUMN student_id INTEGER REFERENCES student(id)"))
                print("✅ Колонка student_id успешно добавлена")
            
            conn.close()
            
        except Exception as e:
            print(f"❌ Ошибка миграции: {e}")

if __name__ == '__main__':
    fix_database()