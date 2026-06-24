from django.db import models

class Product(models.Model):
    name = models.CharField(max_length=200, db_index=True)
    category = models.CharField(max_length=100, db_index=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [
            models.Index(fields=['-created_at', '-id']),
            models.Index(fields=['category', '-created_at', '-id']),
            # For PostgreSQL you can add: models.Index(fields=['name'], name='name_search_idx')
        ]

    def __str__(self):
        return self.name