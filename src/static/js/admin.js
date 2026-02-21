/*============================================*/
// Показ иконки в админке
document.addEventListener('DOMContentLoaded', function () {
    const fieldsets = document.querySelectorAll('fieldset.module.aligned');

    fieldsets.forEach((fieldset) => {
        const iconInput = fieldset.querySelector('input[type="file"][name="icon"]');
        const thumbnail = fieldset.querySelector('#icon_thumbnail');

        if (iconInput && thumbnail) {
            iconInput.addEventListener('change', function (event) {
                const file = event.target.files[0];
                if (file) {
                    const reader = new FileReader();
                    reader.onload = function (e) {
                        thumbnail.src = e.target.result;
                        thumbnail.style.display = 'block'; // Показываем изображение
                    }
                    reader.readAsDataURL(file);
                } else {
                    thumbnail.src = '';
                    thumbnail.style.display = 'none'; // Скрываем изображение, если файл не выбран
                }
            });
        }
    });
});
// Показ обложки проекта в админке
document.addEventListener('DOMContentLoaded', function () {
    const fieldsets = document.querySelectorAll('fieldset.module.aligned');

    fieldsets.forEach((fieldset) => {
        const imageInput = fieldset.querySelector('input[type="file"][name="image"]');
        const thumbnail = fieldset.querySelector('#image_thumbnail');

        if (imageInput && thumbnail) {
            imageInput.addEventListener('change', function (event) {
                const file = event.target.files[0];
                if (file) {
                    const reader = new FileReader();
                    reader.onload = function (e) {
                        thumbnail.src = e.target.result;
                        thumbnail.style.display = 'block'; // Показываем изображение
                    }
                    reader.readAsDataURL(file);
                } else {
                    thumbnail.src = '';
                    thumbnail.style.display = 'none'; // Скрываем изображение, если файл не выбран
                }
            });
        }
    });
});
