from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.db import connection, transaction

from .models import Key, Stream
from .wordlist import generate_stream_key


class ActiveBooleanDefault(SimpleListFilter):
    title = "Can be used for Super Stream events"
    parameter_name = 'superstream'

    def lookups(self, request, model_admin):
        return (
            ('all', 'All'),
            (1, 'Yes'),
            (None, 'No')
        )

    def choices(self, changelist):
        for lookup, title in self.lookup_choices:
            yield {
                'selected': self.value() == (str(lookup) if lookup else lookup),
                'query_string': changelist.get_query_string({self.parameter_name: lookup}, []),
                'display': title,
            }

    def queryset(self, request, queryset):
        if self.value():
            if self.value() == "all":
                return queryset
            else:
                return queryset.filter(**{self.parameter_name: self.value()})
        elif self.value() is None:
            return queryset.filter(**{self.parameter_name: True})


class KeyAdmin(admin.ModelAdmin):
    date_hierarchy = "modified"
    list_filter = (
        "is_live",
        # "superstream",
        ActiveBooleanDefault,
        "livestream",
        "pull",
    )
    ordering = ("-modified",)
    sortable_by = (
        "display_name",
        "stream_key",
        "owner",
        "created",
        "modified",
        "is_live",
        "superstream",
        "livestream",
        "pull",
    )
    list_display = (
        "display_name",
        "stream_key",
        "owner",
        "created",
        "modified",
        "is_live",
        "superstream",
        "livestream",
        "pull",
    )
    search_fields = (
        "name",
        "id",
        "owner__username",
    )

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ('id',)
        return ()

    def get_exclude(self, request, obj=None):
        if not obj:
            return ('id',)
        return ()

    @admin.action(description="Regenerate stream key")
    def regenerate_key(self, request, queryset):
        for key in queryset:
            candidate = generate_stream_key()
            while Key.objects.filter(id=candidate).exists():
                candidate = generate_stream_key()
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute("SET CONSTRAINTS ALL DEFERRED")
                old_id = key.pk
                Key.objects.filter(pk=old_id).update(id=candidate)
                Stream.objects.filter(key_id=old_id).update(key_id=candidate)

    actions = ['regenerate_key']

    @admin.display(description="Display Name")
    def display_name(self, obj):
        return obj.name

    @admin.display(description="Stream Key")
    def stream_key(self, obj):
        return obj.id


# Register your models here.
admin.site.register(Key, KeyAdmin)
admin.site.register(Stream)
