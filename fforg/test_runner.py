import subprocess

from django.test.runner import DiscoverRunner


class GitHashTestRunner(DiscoverRunner):
    def run_tests(self, test_labels, **kwargs):
        try:
            git_hash = subprocess.check_output(
                ['git', 'rev-parse', 'HEAD'], stderr=subprocess.DEVNULL
            ).decode().strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            git_hash = 'unavailable'

        print(f'\nRunning tests against commit: {git_hash}\n')
        return super().run_tests(test_labels, **kwargs)
