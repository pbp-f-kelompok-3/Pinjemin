from django.shortcuts import render

def home(request):
    categories = [
        {
            "name": "Electronics",
            "icon": ""
        },
        {
            "name": "Home & Living",
            "icon": ""
        },
        {
            "name": "Books",
            "icon": ""
        },
        {
            "name": "Clothing",
            "icon": ""
        },
        {
            "name": "More",
            "icon": "•••"
        },
    ]

    return render(request, "home.html", {
        "categories": categories
    })
