from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.utils.html import format_html

from .models import Key, Stream
from .wordlist import generate_stream_key


class ActiveBooleanDefault(SimpleListFilter):
    title = "Can be used for Super Stream events"
    parameter_name = 'superstream'

    def lookups(self, request, model_admin):
        return (
            ('all', 'All'),
            ('yes', 'Yes'),
            ('no', 'No'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'all':
            return queryset
        elif self.value() == 'yes':
            return queryset.filter(superstream=True)
        elif self.value() == 'no':
            return queryset.filter(superstream=False)
        # Default: show only superstream-enabled keys
        return queryset.filter(superstream=True)


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
        "stream_key_display",
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
        "stream_key_display",
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
        "stream_key",
        "owner__username",
    )

    def get_deleted_objects(self, objs, request):
        # Default implementation enumerates all related objects which is unusable
        # with millions of Stream records. Show a count summary instead.
        deleted_objects = []
        for key in objs:
            stream_count = Stream.objects.filter(key=key).count()
            deleted_objects.append(
                format_html('{} (and {} related stream records)', str(key), stream_count)
            )
        return deleted_objects, {}, set(), []

    def get_readonly_fields(self, request, obj=None):
        readonly = []
        if obj:
            readonly.append('stream_key')
        if not request.user.has_perm('ffstream.set_key_superstream'):
            readonly.append('superstream')
        if not request.user.has_perm('ffstream.set_key_livestream'):
            readonly.append('livestream')
        return readonly

    def get_exclude(self, request, obj=None):
        if not obj:
            return ['stream_key']
        return []

    @admin.action(description="Regenerate stream key")
    def regenerate_key(self, request, queryset):
        for key in queryset:
            candidate = generate_stream_key()
            while Key.objects.filter(stream_key=candidate).exists():
                candidate = generate_stream_key()
            Key.objects.filter(pk=key.pk).update(stream_key=candidate)

    actions = ['regenerate_key']

    @admin.display(description="Display Name")
    def display_name(self, obj):
        return obj.name

    @admin.display(description="Stream Key")
    def stream_key_display(self, obj):
        return obj.stream_key


# Register your models here.
admin.site.register(Key, KeyAdmin)
admin.site.register(Stream)
