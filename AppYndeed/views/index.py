from django.shortcuts import render
from django.core.paginator import Paginator
from django.core.cache import cache
from jobspy import scrape_jobs
import hashlib

def index(request):

    keywords = request.GET.get("keywords", "") 
    location = request.GET.get("location", "France")

    search_term = f"\"alternance\" {keywords}"

    raw_key = f"{search_term}_{location}"
    hashed_key = hashlib.md5(raw_key.encode('utf-8')).hexdigest()
    cache_key = f"job_search_{hashed_key}"

    jobs_list = cache.get(cache_key)

    if not jobs_list:
        jobs = scrape_jobs(
            site_name=["indeed", "linkedin"],
            search_term=search_term,
            location=location,
            results_wanted=100
        )
        jobs_list = jobs.to_dict("records")
        cache.set(cache_key, jobs_list, 60 * 30)


    keywords_to_check = ['alternance', 'alternant', 'apprentissage']
    
    filtered_jobs_list = []
    for job in jobs_list:
        job_title = job.get('title') 
        
        if job_title: 
            title_lower = job_title.lower() 
            
            if any(kw in title_lower for kw in keywords_to_check):
                filtered_jobs_list.append(job)


    paginator = Paginator(filtered_jobs_list, 10) 
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