"""
Утилиты для коммуникаций (email, Telegram и т.д.).
"""

import logging
from typing import List, Optional
from django.apps import apps
from django.core.mail import send_mail
from django.conf import settings

# Настройка логгера
logger = logging.getLogger(__name__)


class Communications:
    """Класс для управления коммуникациями."""
    
    @staticmethod
    def email_settings_ready() -> bool:
        """
        Проверяет, настроена ли отправка email.
        
        Returns:
            True если все настройки заданы
        """
        required_settings = [
            'EMAIL_HOST',
            'EMAIL_PORT', 
            'EMAIL_HOST_USER',
            'EMAIL_HOST_PASSWORD',
            'DEFAULT_FROM_EMAIL'
        ]
        
        for setting in required_settings:
            if not getattr(settings, setting, None):
                logger.warning(f"Настройка email не задана: {setting}")
                return False
        
        return True
    
    @staticmethod
    def send_email(
        subject: str,
        message: str,
        recipient_list: List[str],
        html_message: Optional[str] = None,
        fail_silently: bool = False
    ) -> bool:
        """
        Отправляет email.
        
        Args:
            subject: Тема письма
            message: Текстовое сообщение
            recipient_list: Список получателей
            html_message: HTML версия сообщения
            fail_silently: Не выбрасывать исключения
            
        Returns:
            True если письмо отправлено успешно
        """
        if not Communications.email_settings_ready():
            logger.warning(
                "Настройки email не заданы. Письмо не отправлено.",
                extra={
                    'subject': subject,
                    'recipients': recipient_list,
                    'message_preview': message[:100]
                }
            )
            
            # Вывод в консоль для разработки
            print(f"\n{'='*50}")
            print("EMAIL (не отправлен - настройки не заданы):")
            print(f"Subject: {subject}")
            print(f"To: {', '.join(recipient_list)}")
            print(f"Message: {message[:200]}...")
            print(f"{'='*50}\n")
            
            return False
        
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=recipient_list,
                html_message=html_message,
                fail_silently=fail_silently
            )
            
            logger.info(
                f"Email отправлен успешно: {subject}",
                extra={'recipient_count': len(recipient_list)}
            )
            return True
            
        except Exception as e:
            logger.error(
                f"Ошибка при отправке email: {e}",
                extra={'subject': subject, 'recipients': recipient_list},
                exc_info=True
            )
            
            if not fail_silently:
                raise
            return False
    
    @staticmethod
    def send_email_to_user(
        subject: str,
        message: str,
        email: str,
        html_message: Optional[str] = None
    ) -> bool:
        """
        Отправляет email пользователю.
        
        Args:
            subject: Тема письма
            message: Текстовое сообщение
            email: Email получателя
            html_message: HTML версия сообщения
            
        Returns:
            True если письмо отправлено успешно
        """
        if not email:
            logger.warning("Не указан email получателя")
            return False
        
        return Communications.send_email(
            subject=subject,
            message=message,
            recipient_list=[email],
            html_message=html_message,
            fail_silently=True
        )
    
    @staticmethod
    def send_email_to_team(
        subject: str,
        message: str,
        html_message: Optional[str] = None,
        include_superusers: bool = True,
        include_staff: bool = True
    ) -> bool:
        """
        Отправляет email команде (суперпользователям и staff).
        
        Args:
            subject: Тема письма
            message: Текстовое сообщение
            html_message: HTML версия сообщения
            include_superusers: Включать суперпользователей
            include_staff: Включать staff пользователей
            
        Returns:
            True если письмо отправлено успешно
        """
        try:
            # Пытаемся получить модель Profile или User
            try:
                Profile = apps.get_model('users', 'Profile')
                user_model = Profile
            except LookupError:
                from django.contrib.auth.models import User
                user_model = User
            
            # Собираем получателей
            recipients = []
            
            if include_superusers:
                superusers = user_model.objects.filter(is_superuser=True)
                recipients.extend([u.email for u in superusers if u.email])
            
            if include_staff:
                staff_users = user_model.objects.filter(is_staff=True)
                recipients.extend([u.email for u in staff_users if u.email])
            
            # Убираем дубликаты
            recipients = list(set(recipients))
            
            if not recipients:
                logger.warning("Нет получателей для отправки письма команде")
                print("\nНет получателей для отправки письма команде")
                return False
            
            return Communications.send_email(
                subject=subject,
                message=message,
                recipient_list=recipients,
                html_message=html_message,
                fail_silently=True
            )
            
        except Exception as e:
            logger.error(
                f"Ошибка при отправке письма команде: {e}",
                exc_info=True
            )
            print(f"\nОшибка при отправке письма команде: {e}")
            return False
    
    @staticmethod
    def send_telegram_message(
        message: str,
        chat_ids: Optional[List[str]] = None,
        token: Optional[str] = None,
        parse_mode: str = 'HTML'
    ) -> bool:
        """
        Отправляет сообщение в Telegram.
        
        Args:
            message: Сообщение для отправки
            chat_ids: Список ID чатов
            token: Токен бота Telegram
            parse_mode: Режим парсинга ('HTML' или 'Markdown')
            
        Returns:
            True если сообщение отправлено успешно
        """
        try:
            import telepot
        except ImportError:
            logger.error("Библиотека telepot не установлена")
            print("Для отправки Telegram сообщений установите telepot: pip install telepot")
            return False
        
        # Получаем настройки
        token = token or getattr(settings, 'TELEGRAM_TOKEN', None)
        chat_ids = chat_ids or getattr(settings, 'TELEGRAM_CHAT_IDS', [])
        
        if not token or not chat_ids:
            logger.warning(
                "Настройки Telegram не заданы. Сообщение не отправлено.",
                extra={'message_preview': message[:100]}
            )
            
            print(f"\n{'='*50}")
            print("TELEGRAM (не отправлено - настройки не заданы):")
            print(f"Message: {message}")
            print(f"{'='*50}\n")
            return False
        
        try:
            bot = telepot.Bot(token)
            success_count = 0
            
            for chat_id in chat_ids:
                if not chat_id:
                    continue
                
                try:
                    bot.sendMessage(chat_id, message, parse_mode=parse_mode)
                    success_count += 1
                    logger.debug(f"Telegram сообщение отправлено в chat_id: {chat_id}")
                except Exception as e:
                    logger.error(
                        f"Ошибка при отправке Telegram сообщения в {chat_id}: {e}",
                        exc_info=True
                    )
            
            if success_count > 0:
                logger.info(
                    f"Telegram сообщения отправлены в {success_count} чат(ов)",
                    extra={'total_chats': len(chat_ids)}
                )
                return True
            else:
                logger.warning("Telegram сообщения не были отправлены ни в один чат")
                return False
                
        except Exception as e:
            logger.error(
                f"Ошибка при инициализации Telegram бота: {e}",
                exc_info=True
            )
            return False