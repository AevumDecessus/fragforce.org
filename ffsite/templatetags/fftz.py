import random
import string

from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter(name='localtime')
def format_datetime(value, eid=None):
    if eid is None:
        eid = ''.join([random.choice(string.ascii_letters) for i in range(0, 15)])
    eid = str(eid)
    dt = str(value)
    return mark_safe("""
<time id="{id}"></time>
<script>
    updateTimeValue("#{id}","{dt}.000Z");
</script>
    """.format(id=eid, dt=dt))
