import secrets

from django import template
from django.utils.safestring import mark_safe

register = template.Library()


def _random_id():
    return secrets.token_hex(8)


@register.filter(name='localtime')
def format_datetime(value, eid=None):
    if eid is None:
        eid = _random_id()
    eid = str(eid)
    dt = str(value)
    return mark_safe("""
<time id="{id}"></time>
<script>
    updateTimeValue("#{id}","{dt}.000Z");
</script>
    """.format(id=eid, dt=dt))


@register.filter(name='localtime_short')
def format_datetime_short(value, eid=None):
    """Like localtime but shows weekday, date and hour:minute with timezone name - no seconds."""
    if eid is None:
        eid = _random_id()
    eid = str(eid)
    dt = str(value)
    return mark_safe("""
<time id="{id}"></time>
<script>
    (function() {{
        var d = new Date("{dt}.000Z");
        var opts = {{weekday:"short",month:"short",day:"numeric",hour:"numeric",minute:"2-digit",timeZoneName:"short"}};
        document.getElementById("{id}").textContent = d.toLocaleString(undefined, opts);
        document.getElementById("{id}").setAttribute("datetime", "{dt}.000Z");
    }})();
</script>
    """.format(id=eid, dt=dt))
