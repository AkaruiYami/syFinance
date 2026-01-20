def get_users(limit=50):
    assert limit > 0, "Limit must be 1 or more."
    from models.user import User

    if limit == 1:
        user = User.objects().first()
        return [user] if user else []

    users = User.objects().all()
    users = users[:limit]
    return users
