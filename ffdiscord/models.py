from django.contrib.auth.models import Group
from django.db import models


class DiscordRoleMapping(models.Model):
    """Maps a Discord role ID to a Django Group."""
    discord_role_id = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        verbose_name="Discord Role ID",
    )
    group = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        verbose_name="Django Group",
    )
    description = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Description",
    )

    class Meta:
        verbose_name = "Discord Role Mapping"
        verbose_name_plural = "Discord Role Mappings"

    def __str__(self):
        return f"{self.discord_role_id} → {self.group.name}"
