# blockchain/management/commands/check_certificates.py
from django.core.management.base import BaseCommand
from watch_customizer.models import WatchCertificate
from web3 import Web3
from django.conf import settings

class Command(BaseCommand):
    help = 'Check status of watch certificates on blockchain'

    def handle(self, *args, **kwargs):
        w3 = Web3(Web3.HTTPProvider(settings.ETHEREUM_NODE_URL))
        contract = w3.eth.contract(
            address=settings.CERTIFICATE_CONTRACT_ADDRESS,
            abi=settings.CERTIFICATE_CONTRACT_ABI
        )
        
        certificates = WatchCertificate.objects.filter(is_verified=False)
        for cert in certificates:
            try:
                stored_hash = contract.functions.getCertificate(
                    cert.order.order_id
                ).call()
                
                if stored_hash == cert.certificate_hash:
                    cert.is_verified = True
                    cert.save()
                    self.stdout.write(self.style.SUCCESS(
                        f'Certificate {cert.id} verified successfully'
                    ))
            except Exception as e:
                self.stdout.write(self.style.ERROR(
                    f'Error checking certificate {cert.id}: {str(e)}'
                ))