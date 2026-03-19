from django.shortcuts import render
from django.core.paginator import Paginator
from django.db.models import Q
from AppYndeed.models import JobOffer 

def index(request):
    keywords = request.GET.get("keywords", "")
    location = request.GET.get("location", "")

    jobs_query = JobOffer.objects.all()

    if keywords:
        jobs_query = jobs_query.filter(
            Q(title__icontains=keywords) | 
            Q(description__icontains=keywords)
        )
    
    if location:
        jobs_query = jobs_query.filter(location__icontains=location)


    paginator = Paginator(jobs_query, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        "index.html",
        {
            "page_obj": page_obj,
            "keywords": keywords,
            "location": location
        },
    )