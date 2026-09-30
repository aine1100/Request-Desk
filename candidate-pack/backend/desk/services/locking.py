from django.db import connection


def locked(queryset):
    if connection.features.has_select_for_update:
        return queryset.select_for_update()
    return queryset
