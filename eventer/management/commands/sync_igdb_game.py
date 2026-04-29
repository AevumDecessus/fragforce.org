from django.core.management.base import BaseCommand, CommandError

from eventer.igdb import sync_game_from_igdb


class Command(BaseCommand):
    help = 'Fetch a game from IGDB by ID and upsert the local Game record'

    def add_arguments(self, parser):
        parser.add_argument('igdb_id', type=int, nargs='+', help='One or more IGDB game IDs')

    def handle(self, *args, **options):
        for igdb_id in options['igdb_id']:
            try:
                game, created = sync_game_from_igdb(igdb_id)
                action = 'Created' if created else 'Updated'
                self.stdout.write(self.style.SUCCESS(f'{action}: {game.name} (igdb_id={igdb_id})'))
            except ValueError as e:
                raise CommandError(str(e))
            except Exception as e:
                raise CommandError(f'Failed to sync igdb_id={igdb_id}: {e}')
