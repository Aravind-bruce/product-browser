from django.core.management.base import BaseCommand
from products.models import Product
from django.utils import timezone
import random
from decimal import Decimal

class Command(BaseCommand):
    help = 'Seed 200,000 products'

    def handle(self, *args, **kwargs):
        self.stdout.write('Seeding products...')

        CATEGORIES = ['Electronics', 'Books', 'Clothing', 'Home', 'Toys', 'Sports', 'Automotive']
        CHUNK_SIZE = 10000
        TOTAL = 200000

        product_batch = []
        for i in range(1, TOTAL + 1):
            product_batch.append(
                Product(
                    name=f'Product {i}',
                    category=random.choice(CATEGORIES),
                    price=Decimal(random.randint(100, 9999)) / 100,
                    created_at=timezone.now() - timezone.timedelta(seconds=random.randint(0, 86400 * 365)),
                    updated_at=timezone.now(),
                )
            )
            if len(product_batch) == CHUNK_SIZE:
                Product.objects.bulk_create(product_batch)
                product_batch = []
                self.stdout.write(f'Seeded {i} products')

        if product_batch:
            Product.objects.bulk_create(product_batch)

        self.stdout.write(self.style.SUCCESS('Successfully seeded 200,000 products'))