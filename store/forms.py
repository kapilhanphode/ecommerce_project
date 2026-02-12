from django import forms
from .models import Category, Product, ProductVariation

class ProductFrom(forms.ModelForm):
    class Meta:
        model = Product
        fields = '__all__'

class ProductVariationForm(forms.ModelForm):
    class Meta:
        model = ProductVariation
        fields = '__all__'