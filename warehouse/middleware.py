class RequestLoggingMiddleware:
    """Middleware для логирования HTTP запросов"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Логируем только POST запросы к warehouse
        if request.method == 'POST' and '/warehouse/' in request.path:
            print(f"[MIDDLEWARE] POST to {request.path}")
            print(f"[MIDDLEWARE] POST data: {dict(request.POST)}")
            print(f"[MIDDLEWARE] Headers: {dict(request.headers)}")
        
        response = self.get_response(request)
        return response