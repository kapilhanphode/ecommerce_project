from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import render, redirect, get_object_or_404
from .forms import ProductFrom, ProductVariationForm
from .models import Category, Product, ProductImage, Order, OrderItem, Cart, CartItem, CategoryImage
from django.db.models import Prefetch, Q
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.forms import AuthenticationForm
from django.http import JsonResponse
from django.contrib.humanize.templatetags.humanize import intcomma
from django.core.paginator import Paginator


# def user_login(request):
#     print('user_login.....................')
#     if request.method == "POST":
#         form = AuthenticationForm(request, data=request.POST)
#         if form.is_valid():
#             username = form.cleaned_data.get('username')
#             password = form.cleaned_data.get('password')
#
#             user = authenticate(username=username, password=password)
#             if user is not None:
#                 login(request, user)
#
#                 # Merge session cart into user cart
#                 merge_session_cart(request, user)
#
#                 return redirect('home')
#     else:
#         form = AuthenticationForm()
#     return render(request, 'store/login.html', {'form': form})


def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')
    else:
        form = UserCreationForm()
    return render(request, 'store/signup.html', {'form': form})


def checkout(request):
    cart = request.session.get('cart', [])

    if not cart:
        return redirect('cart')

    order = Order.objects.create(user=request.user)

    products = Product.objects.filter(id__in=cart)

    for product in products:
        OrderItem.objects.create(
            order=order,
            product=product,
            price=product.price,
            quantity=1
        )

    request.session['cart'] = []
    return redirect('home')


def home(request):
    # Prefetch product main images
    product_main_image_prefetch = Prefetch(
        'images',
        queryset=ProductImage.objects.filter(is_main=True),
        to_attr='main_image_list'
    )

    # Prefetch category main images
    category_main_image_prefetch = Prefetch(
        'images',
        queryset=CategoryImage.objects.filter(is_main=True),
        to_attr='main_image_list'
    )

    # Latest 8 products
    products = (
        Product.objects
        .prefetch_related(product_main_image_prefetch)
        .order_by('-id')[:10]
    )

    # All categories with main image
    categories = (
        Category.objects
        .prefetch_related(category_main_image_prefetch)
    )

    return render(request, 'store/home.html', {
        'categories': categories,
        'products': products
    })


def about(request):
    return render(request, 'store/about.html')


def contact_us(request):
    return render(request, 'store/contact_us.html')


def search_products(request):
    query = request.GET.get('q', '')

    main_image_prefetch = Prefetch(
        'images',
        queryset=ProductImage.objects.filter(is_main=True),
        to_attr='main_image_list'
    )
    if query:
        products = (
            Product.objects
            .filter(
                Q(name__icontains=query) |
                Q(description__icontains=query)
            )
            .prefetch_related(main_image_prefetch)
        )
    else:
        products = Product.objects.none()

    categories = Category.objects.all()
    return render(request, 'store/category_products.html', {
        'products': products,
        'categories': categories,
        'category': None,  # important
        'search_query': query  # so template can detect search
    })


def category_products(request, category_slug):
    category = get_object_or_404(Category, slug=category_slug)
    main_image_prefetch = Prefetch(
        'images',
        queryset=ProductImage.objects.filter(is_main=True),
        to_attr='main_image_list'
    )
    products = (
        Product.objects
        .filter(category=category)
        .prefetch_related(main_image_prefetch)
    )
    paginator = Paginator(products, 8)  # Show 8 products per page
    page_number = request.GET.get('page')  # Get the current page number from the URL
    page_obj = paginator.get_page(page_number)  # Get products for the current page
    categories = Category.objects.all()
    return render(request, 'store/category_products.html',
                  {'categories': categories, 'category': category, 'products': page_obj})


def product_detail(request, product_id):
    # Prefetch only the main image
    main_image_prefetch = Prefetch(
        'images',
        queryset=ProductImage.objects.filter(is_main=True),
        to_attr='main_image_list'
    )
    all_images_prefetch = Prefetch('images', queryset=ProductImage.objects.all(), to_attr='all_images')
    product_queryset = Product.objects.prefetch_related(main_image_prefetch, all_images_prefetch)
    product = get_object_or_404(product_queryset, id=product_id)
    variations = product.variations.all()
    categories = Category.objects.all()
    return render(request, 'store/product_details.html',
                  {'categories': categories, 'product': product, 'variations': variations})


def add_product(request):
    if request.method == 'POST':
        form = ProductFrom(request.POST)
        if form.is_valid():
            form.save()
            return redirect('home')
    else:
        form = ProductFrom()
    return render(request, 'store/add_product.html', {'form': form})


def add_variation(request):
    if request.method == 'POST':
        form = ProductVariationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('home')
    else:
        form = ProductVariationForm()
    return render(request, 'store/add_variation.html', {'form': form})


# def merge_session_cart(request, user):
#     session_cart = request.session.get('cart', {})
#     for product_id, quantity in session_cart.items():
#         product = Product.objects.get(id=product_id)
#         cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)
#         if not created:
#             cart_item.quantity += quantity
#         else:
#             cart_item.quantity = quantity
#         cart_item.save()
#     # Clear session cart after merging
#     request.session['cart'] = {}


def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(user=request.user)

        # Check if product already exists in cart
        cart_item = CartItem.objects.filter(cart=cart, product=product)

        if cart_item:
            # Product already in cart → redirect to cart
            messages.info(request, "Product already in cart.")
            return redirect('cart')
        else:
            # Product not in cart → add it
            CartItem.objects.create(cart=cart, product=product, quantity=1)
            messages.success(request, "Product added to cart!")
            # Stay on the same page
            return redirect(request.META.get('HTTP_REFERER', 'home'))
    else:
        session_cart = request.session.get('cart', {})
        if isinstance(session_cart, list):
            new_cart = {}
            for pid in session_cart:
                new_cart[str(pid)] = 1
            session_cart = new_cart

        product_id_str = str(product_id)

        if product_id_str in session_cart:
            # Already in cart → redirect
            messages.info(request, "Product already in cart.")
            return redirect('cart')
        else:
            session_cart[product_id_str] = 1
            request.session['cart'] = session_cart
            messages.success(request, "Product added to cart!")
            return redirect(request.META.get('HTTP_REFERER', 'home'))


def cart_view(request):
    categories = Category.objects.all()
    products_with_qty = []

    # Prefetch main images for all products in cart
    main_image_prefetch = Prefetch(
        'images',
        queryset=ProductImage.objects.filter(is_main=True),
        to_attr='main_image_list'
    )

    if request.user.is_authenticated:
        # Fetch user cart from DB
        cart, created = Cart.objects.get_or_create(user=request.user)
        cart_items = cart.items.all()

        # Prefetch products with main image
        product_ids = [item.product.id for item in cart_items]
        products = Product.objects.filter(id__in=product_ids).prefetch_related(main_image_prefetch)

        # Map products by id for easy lookup
        products_map = {p.id: p for p in products}

        for item in cart_items:
            product = products_map[item.product.id]
            product.cart_item_quantity = item.quantity
            product.cart_item_total_price = product.price * item.quantity
            product.cart_item_total_price_display = intcomma(product.cart_item_total_price)
            products_with_qty.append(product)

        cart_count = cart_items.count()
    else:
        session_cart = request.session.get('cart', {})

        # Convert old list structure to dict if necessary
        if isinstance(session_cart, list):
            new_cart = {}
            for pid in session_cart:
                new_cart[str(pid)] = 1
            session_cart = new_cart

        product_ids = [int(pid) for pid in session_cart.keys()]
        products = Product.objects.filter(id__in=product_ids).prefetch_related(main_image_prefetch)
        products_map = {p.id: p for p in products}

        for pid_str, qty in session_cart.items():
            pid = int(pid_str)
            product = products_map[pid]
            product.cart_item_quantity = qty
            product.cart_item_total_price = product.price * qty
            product.cart_item_total_price_display = intcomma(product.cart_item_total_price)
            products_with_qty.append(product)

        cart_count = len(session_cart)

    return render(request, 'store/cart.html', {
        'products': products_with_qty,
        'categories': categories,
        'cart_count': cart_count
    })


def update_cart_quantity(request, product_id, action):
    """
    action = 'increase' or 'decrease'
    Works for both logged-in and anonymous users.
    """
    product = get_object_or_404(Product, id=product_id)
    product_id_str = str(product_id)

    if request.user.is_authenticated:
        # DB cart
        cart, _ = Cart.objects.get_or_create(user=request.user)
        cart_item = CartItem.objects.filter(cart=cart, product=product).first()

        if cart_item:
            if action == 'increase':
                cart_item.quantity += 1
            elif action == 'decrease' and cart_item.quantity > 1:
                cart_item.quantity -= 1
            if cart_item.quantity <= 0:
                cart_item.delete()
            else:
                cart_item.save()

            # Calculate the updated total price for the product in the cart
            updated_quantity = cart_item.quantity
            updated_price = updated_quantity * product.price
            cart_item.total_price = updated_price  # Update the total price in the cart item
            cart_item.save()

        else:
            return JsonResponse({'error': 'Product not in cart'}, status=400)

    else:
        # Session cart as dict {product_id: quantity}
        session_cart = request.session.get('cart', {})
        if product_id_str in session_cart:
            if action == 'increase':
                session_cart[product_id_str] += 1
            elif action == 'decrease' and session_cart[product_id_str] > 1:
                session_cart[product_id_str] -= 1
            if session_cart[product_id_str] <= 0:
                del session_cart[product_id_str]
            request.session['cart'] = session_cart

            updated_quantity = session_cart[product_id_str]
            updated_price = updated_quantity * product.price
        else:
            return JsonResponse({'error': 'Product not in cart'}, status=400)

    # Return updated quantity and price as JSON
    return JsonResponse({
        'updated_quantity': updated_quantity,
        'updated_price': updated_price,
    })


def remove_from_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(user=request.user)
        CartItem.objects.filter(cart=cart, product=product).delete()
    else:
        session_cart = request.session.get('cart', {})
        # If old structure is list (safety check)
        if isinstance(session_cart, list):
            if product_id in session_cart:
                session_cart.remove(product_id)
        else:
            product_id_str = str(product_id)
            if product_id_str in session_cart:
                del session_cart[product_id_str]  # ✅ correct way for dict
        request.session['cart'] = session_cart
    messages.success(request, "Product removed from cart!")
    return redirect('cart')
