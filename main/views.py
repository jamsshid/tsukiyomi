from django.shortcuts import render
from .models import Product, Category

def web_app_view(request):
    categories = Category.objects.all()
    products = Product.objects.all()
    context = {
        "categories": categories,
        "products": products,
    }

    return render(request, "index.html", context)
