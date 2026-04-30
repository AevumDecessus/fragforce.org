from django.core.management.base import BaseCommand, CommandError

from eventer.igdb import IGDBClient, IGDBError, sync_game_from_igdb


class Command(BaseCommand):
    help = 'Fetch a game from IGDB by ID and upsert the local Game record'

    def add_arguments(self, parser):
        parser.add_argument('igdb_id', type=int, nargs='+', help='One or more IGDB game IDs')

    def handle(self, *args, **options):
        if not IGDBClient.credentials_configured():
            raise CommandError('IGDB credentials are not configured. Set IGDB_CLIENT_ID and IGDB_CLIENT_SECRET.')

        client = IGDBClient()
        if not client.credentials_valid():
            raise CommandError('IGDB credentials are invalid. Check IGDB_CLIENT_ID and IGDB_CLIENT_SECRET.')

        for igdb_id in options['igdb_id']:
            try:
                game, created = sync_game_from_igdb(igdb_id)
                action = 'Created' if created else 'Updated'
                self.stdout.write(self.style.SUCCESS(f'{action}: {game.name} (igdb_id={igdb_id})'))
            except ValueError as e:
                raise CommandError(str(e))
            except IGDBError as e:
                raise CommandError(f'IGDB API error for igdb_id={igdb_id}: {e}')
