from django.test import TestCase

# Create your tests here.
from blockchain.blockchain_utils import test_blockchain_connection
success, message = test_blockchain_connection()
print(message)