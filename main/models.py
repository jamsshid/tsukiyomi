from django.db import models


class Category(models.Model):
    name_uz = models.CharField("Kategoriya (UZ)", max_length=100)
    name_ru = models.CharField("Kategoriya (RU)", max_length=100)

    def __str__(self):
        return self.name_uz


class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    name_uz = models.CharField("Nomi (UZ)", max_length=100)
    name_ru = models.CharField("Nomi (RU)", max_length=100)
    price = models.PositiveIntegerField("Narxi")
    image = models.ImageField(upload_to="products/")

    def __str__(self):
        return self.name_uz


