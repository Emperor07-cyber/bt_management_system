from django.http import JsonResponse

def home(request):
    return JsonResponse({
        "message": "BT Management System API is running",
        "status": "success"
    })