Добавлено: from sqlalchemy.exc import SQLAlchemyError для обработки исключений SQLAlchemy.
Добавлено: try...except SQLAlchemyError блок при сохранении токена в базу данных, чтобы перехватывать ошибки базы данных и откатывать транзакцию.
Добавлено: session.close() в блоке finally для гарантированного закрытия сессии.