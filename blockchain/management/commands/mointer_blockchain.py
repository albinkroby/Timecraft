from django.core.management.base import BaseCommand
from blockchain.blockchain_utils import monitor_blockchain_status

class Command(BaseCommand):
    help = 'Monitor blockchain status'

    def handle(self, *args, **kwargs):
        status = monitor_blockchain_status()
        if status:
            self.stdout.write(self.style.SUCCESS('Blockchain connection successful'))
            self.stdout.write(f"Status: {status}")
        else:
            self.stdout.write(self.style.ERROR('Blockchain connection failed'))