def get_users(limit=50):
    assert limit > 0, "Limit must be 1 or more."
    from models.user import User

    if limit == 1:
        return [User.objects().first()]

    users = User.objects().all()
    users = users[:limit]
    return users
