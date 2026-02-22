from django.shortcuts import render


__all__ = (
    'page_not_found_view',
)


def page_not_found_view(request, exception):
   """
   Функция обработки ошибки 404 (страница не найдена).
   """
   return render(request, '404.html', status=404)