import os
import re
import logging
import shutil
import uuid
from django.db import models
from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from common.utils.files import FileUtils

from .managers import ProfileManager

# Create your models here.
class Profile(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(_('E-mail'), unique=True)

    reg_number = models.UUIDField(default=uuid.uuid4,
                                  editable=False,
                                  unique=True,
                                  verbose_name='Регистрационный номер')

    nic_name = models.CharField(max_length=100,
                                verbose_name='Псевдоним',
                                null=True,
                                blank=True)

    dir_name = "avatar"
    image = models.ImageField(upload_to=FileUtils.generate_file_path,
                               null=True,
                               blank=True,
                               verbose_name='Аватар')
    max_size = (300, 300)

    first_name = models.CharField(max_length=100,
                                  verbose_name='Имя',
                                  null=True,
                                  blank=True)

    middle_name = models.CharField(max_length=100,
                                   verbose_name='Отчество',
                                   null=True,
                                   blank=True)

    last_name = models.CharField(max_length=100,
                                 verbose_name='Фамилия',
                                 null=True,
                                 blank=True)

    phone = models.CharField(max_length=20,
                             unique=False,
                             null=True,
                             blank=True,
                             verbose_name='Телефон',
                             db_index=True)

    is_staff = models.BooleanField(default=False,
                                   verbose_name='В команде')

    is_active = models.BooleanField(default=False,
                                    verbose_name='Активный')

    date_joined = models.DateTimeField(default=timezone.now)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = ProfileManager()

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Если nic_name не задан и есть email
        if not self.nic_name and self.email:
            base_nic_name = self.email.split('@')[0]
            self.nic_name = re.sub(r'[^a-zA-Z0-9]', '', base_nic_name).upper()
            # Проверка на уникальность
            original_nic_name = self.nic_name
            counter = 1
            while Profile.objects.filter(nic_name=self.nic_name).exists():
                # Формируем новое имя с порядковым номером
                self.nic_name = f"{original_nic_name}_{counter:03}"
                counter += 1
            super().save(*args, **kwargs)
        # Проверяем наличие аватара
        if self.image:
            # Обрабатываем изображение
            try:
                FileUtils.resize_and_crop_image(self.image.path, self.max_size)
                # Сохраняем изменения, если аватар был изменен
                super().save(*args, **kwargs)
            except Exception as e:
                logger = logging.getLogger(__name__)
                logger.error(f"Ошибка обработки аватара: {e}")

    def delete(self, *args, **kwargs):
        """
        Удаляет объект, связанные файлы и пустые директории.
        """
        # Определение пути к файлу аватара
        image_path = self.image.path if self.image else None
        # Получение каталога пользователя на основе логики, схожей с generate_file_path
        class_name = self.__class__.__name__.lower()
        named_folder = (
            getattr(self, 'slug', None)
            or getattr(self, 'nic_name', None)
            or str(getattr(self, 'id', 'no_id'))
        )
        named_folder = re.sub(r"[\W]", "_", named_folder.strip()) if named_folder else 'no_id'
        user_folder_path = os.path.join('media', class_name, named_folder)
        # Удаление объекта из базы данных
        super().delete(*args, **kwargs)
        # Удаление файла аватара, если он существует
        if image_path and os.path.isfile(image_path):
            try:
                os.remove(image_path)
            except Exception as e:
                print(f'Удаление файла аватара не удалось: {e}')
        # Удаление папки пользователя, если она существует
        if os.path.isdir(user_folder_path):
            try:
                shutil.rmtree(user_folder_path)
            except Exception as e:
                print(f'Удаление папки пользователя не удалось: {e}')
        # Удаление пустых директорий в корневой директории 'media'
        FileUtils.remove_empty_directories('media')


    def __str__(self):
        fio = ''
        if self.nic_name:
            if not self.first_name or not self.last_name:
                fio = str(self.nic_name)
            elif not self.middle_name:
                fio = f"{self.last_name} {self.first_name}"
            else:
                fio = f"{self.last_name} {self.first_name} {self.middle_name}"
        else:
            fio = str(self.email)
        return fio

    class Meta:
        verbose_name = 'Профиль пользователя'
        verbose_name_plural = 'Профили пользователей'
        ordering = ['-is_staff', '-is_active', 'last_name', 'first_name', 'middle_name']