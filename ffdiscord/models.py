from django.contrib.auth.models import Group
from django.db import models


class DiscordRole(models.Model):
    """A Discord role, synced from the guild."""
    discord_role_id = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        verbose_name="Discord Role ID",
    )
    name = models.CharField(max_length=255, verbose_name="Role Name")

    class Meta:
        verbose_name = "Discord Role"
        verbose_name_plural = "Discord Roles"
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.discord_role_id})"


class DiscordRoleMapping(models.Model):
    """Maps a Discord role to a Django Group."""
    role = models.OneToOneField(
        DiscordRole,
        on_delete=models.CASCADE,
        verbose_name="Discord Role",
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
        return f"{self.role.name} → {self.group.name}"
