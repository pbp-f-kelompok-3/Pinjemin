def user_mode(request):
    """Biar template mana pun bisa pakai {{ is_seller_mode }} (untuk navbar/toggle)."""
    profile = getattr(request.user, "profile", None) if request.user.is_authenticated else None
    return {"is_seller_mode": bool(profile and profile.is_seller_mode)}
