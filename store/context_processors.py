from .models import Cart

def cart_count(request):
    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(user=request.user)
        count = cart.items.count()
    else:
        cart = request.session.get('cart', {})
        if isinstance(cart, list):
            count = len(cart)
        else:
            count = len(cart)
    return {'cart_count': count}
