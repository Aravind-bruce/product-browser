import json
from datetime import datetime, timedelta
from django.shortcuts import render
from django.db import models  # <-- added for Case/When
from django.db.models import Q, Count, Avg, Min, Max, Sum, Case, When, Value
from django.db.models.functions import TruncDate
from django.utils.dateparse import parse_datetime
from django.utils import timezone
from decimal import Decimal
from .models import Product

PAGE_SIZE = 20

def product_list(request):
    # Get filter parameters
    category = request.GET.get('category')
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    search = request.GET.get('search')
    cursor = request.GET.get('cursor')

    # Convert min/max to Decimal (or None) for later use
    try:
        min_val = Decimal(min_price) if min_price else None
    except:
        min_val = None
    try:
        max_val = Decimal(max_price) if max_price else None
    except:
        max_val = None

    # Base queryset (with all filters)
    base_qs = Product.objects.all()
    if category:
        base_qs = base_qs.filter(category=category)
    if min_val is not None:
        base_qs = base_qs.filter(price__gte=min_val)
    if max_val is not None:
        base_qs = base_qs.filter(price__lte=max_val)
    if search:
        base_qs = base_qs.filter(name__icontains=search)

    # Paginated queryset (copy of base_qs with cursor filter)
    queryset = base_qs.all()

    if cursor:
        try:
            created_at_str, id_str = cursor.split(',')
            dt = parse_datetime(created_at_str)
            if dt is None:
                dt = datetime.fromisoformat(created_at_str.replace(' ', 'T'))
            if dt.tzinfo is not None:
                dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
            last_id = int(id_str)
            queryset = queryset.filter(
                Q(created_at__lt=dt) | (Q(created_at=dt) & Q(id__lt=last_id))
            )
        except:
            pass

    products = list(queryset.order_by('-created_at', '-id')[:PAGE_SIZE])

    # Next cursor
    next_cursor = None
    if len(products) == PAGE_SIZE:
        last = products[-1]
        dt_str = last.created_at.strftime('%Y-%m-%d %H:%M:%S.%f')
        next_cursor = f"{dt_str},{last.id}"

    total_count = base_qs.count()  # total matching (before pagination)

    # Stats
    stats = base_qs.aggregate(
        categories_count=Count('category', distinct=True),
        avg_price=Avg('price'),
        min_price=Min('price'),
        max_price=Max('price'),
    )

    # Categories for filter dropdown
    categories = Product.objects.values_list('category', flat=True).distinct().order_by('category')

    # ----- CHART DATA -----
    # 1. Category distribution (pie)
    category_summary = (
        Product.objects
        .values('category')
        .annotate(count=Count('id'))
        .order_by('-count')
    )
    chart_labels = [item['category'] for item in category_summary]
    chart_values = [item['count'] for item in category_summary]

    # 2. Price histogram (buckets) – using Case/When on base_qs
    price_buckets_data = (
        base_qs
        .annotate(
            bucket=Case(
                When(price__lt=10, then=Value('0-10')),
                When(price__lt=25, then=Value('10-25')),
                When(price__lt=50, then=Value('25-50')),
                When(price__lt=100, then=Value('50-100')),
                When(price__lt=250, then=Value('100-250')),
                default=Value('250+'),
                output_field=models.CharField(max_length=10)
            )
        )
        .values('bucket')
        .annotate(count=Count('id'))
        .order_by('bucket')
    )

    bucket_labels = ['0-10', '10-25', '25-50', '50-100', '100-250', '250+']
    bucket_counts = []
    for label in bucket_labels:
        found = False
        for item in price_buckets_data:
            if item['bucket'] == label:
                bucket_counts.append(item['count'])
                found = True
                break
        if not found:
            bucket_counts.append(0)

    # 3. Daily products added (last 30 days) – global, not filtered (so we see overall trend)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    daily_data = (
        Product.objects
        .filter(created_at__gte=thirty_days_ago)
        .annotate(day=TruncDate('created_at'))
        .values('day')
        .annotate(count=Count('id'))
        .order_by('day')
    )
    day_labels = [item['day'].strftime('%Y-%m-%d') for item in daily_data]
    day_counts = [item['count'] for item in daily_data]

    # Active filters summary
    active_filters = []
    if category:
        active_filters.append(('category', category))
    if min_price:
        active_filters.append(('min_price', min_price))
    if max_price:
        active_filters.append(('max_price', max_price))
    if search:
        active_filters.append(('search', search))

    context = {
        'products': products,
        'next_cursor': next_cursor,
        'categories': categories,
        'current_category': category,
        'min_price': min_price,
        'max_price': max_price,
        'search': search,
        'has_cursor': bool(cursor),
        'total_count': total_count,
        'page_size': PAGE_SIZE,
        'stats': stats,
        'active_filters': active_filters,
        'chart_labels': json.dumps(chart_labels),
        'chart_values': json.dumps(chart_values),
        'bucket_labels': json.dumps(bucket_labels),
        'bucket_counts': json.dumps(bucket_counts),
        'day_labels': json.dumps(day_labels),
        'day_counts': json.dumps(day_counts),
    }
    return render(request, 'index.html', context)