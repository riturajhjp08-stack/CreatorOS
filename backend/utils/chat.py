from storage import get_storage


def decorate_attachments(message, attachments):
    storage = get_storage()
    decorated = []
    for item in attachments or []:
        decorated_item = dict(item)
        if hasattr(storage, "client") and hasattr(storage, "bucket"):
            key = item.get("key")
            if key:
                try:
                    url = storage.client.generate_presigned_url(
                        "get_object",
                        Params={"Bucket": storage.bucket, "Key": key},
                        ExpiresIn=3600,
                    )
                    decorated_item["url"] = url
                except Exception:
                    pass
        else:
            stored_name = item.get("stored_name")
            if stored_name:
                decorated_item["url"] = f"/api/social/messages/attachments/{message.id}/{stored_name}"
        decorated.append(decorated_item)
    return decorated
