import math


def parse_pagination(args, default_page=1, default_page_size=50, max_page_size=200):
    try:
        page = int(args.get("page", default_page))
    except (TypeError, ValueError):
        page = default_page
    if page < 1:
        page = 1

    try:
        page_size = int(args.get("page_size", default_page_size))
    except (TypeError, ValueError):
        page_size = default_page_size
    if page_size < 1:
        page_size = default_page_size
    page_size = min(page_size, max_page_size)

    offset = (page - 1) * page_size
    return page, page_size, offset


def pagination_meta(total, page, page_size):
    total_pages = math.ceil(total / page_size) if page_size else 0
    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_prev": page > 1,
    }
