import secrets
import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Request

from app.db import get_db
from app.services.catalog import CATEGORIES, SORTS, get_book, home_books, list_books

router = APIRouter()


def render(request, template, context=None, status_code=200):
    token = request.session.setdefault('csrf_token', secrets.token_urlsafe(32))
    common = {
        'request': request, 'categories': CATEGORIES,
        'cart_count': sum(request.session.get('cart', {}).values()),
        'csrf_token': token, 'errors': [],
    }
    return request.app.state.templates.TemplateResponse(
        request=request, name=template, context={**common, **(context or {})}, status_code=status_code,
    )


@router.get('/')
def home(request: Request, db: sqlite3.Connection = Depends(get_db)):
    return render(request, 'home.html', home_books(db))


def listing(request, db, template, q, category, sort, page):
    errors = []
    if category and category not in CATEGORIES:
        errors.append({'field': 'category', 'message': '지원하지 않는 카테고리입니다.'})
    if sort not in SORTS:
        errors.append({'field': 'sort', 'message': '지원하지 않는 정렬입니다.'})
    try:
        number = int(page)
        if number < 1:
            raise ValueError
    except ValueError:
        errors.append({'field': 'page', 'message': '페이지는 1 이상의 정수여야 합니다.'})
    if errors:
        return render(request, 'error.html', {
            'status_code': 422, 'message': '검색 조건을 확인해 주세요.', 'errors': errors,
            'filters': {'q': q, 'category': category, 'sort': sort},
        }, 422)
    return render(request, template, list_books(db, q=q, category=category, sort=sort, page=number))


@router.get('/books')
def books(request: Request, category: str = '', sort: str = 'popular', page: str = '1',
          db: sqlite3.Connection = Depends(get_db)):
    return listing(request, db, 'books.html', '', category, sort, page)


@router.get('/search')
def search(request: Request, q: str = '', category: str = '', sort: str = 'popular', page: str = '1',
           db: sqlite3.Connection = Depends(get_db)):
    return listing(request, db, 'search.html', q, category, sort, page)


@router.get('/books/{book_id}')
def detail(request: Request, book_id: int, db: sqlite3.Connection = Depends(get_db)):
    book = get_book(db, book_id)
    if book is None:
        raise HTTPException(404, '도서를 찾을 수 없습니다.')
    return render(request, 'book_detail.html', {'book': book})
