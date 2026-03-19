import logging
import time
import pandas as pd
from datetime import date
from django.core.management.base import BaseCommand
from django.db import transaction
from jobspy import scrape_jobs
from AppYndeed.models import JobOffer

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Collecte les offres et remplace totalement la base existante"

    def handle(self, *args, **options):
        logger.info("Demarrage du scraping (mode Remplacement Total)...")

        # Mots-clés généraux pour alternance
        general_keywords = [
            "Alternance",
            "Apprentissage",
            "Contrat de professionnalisation",
            "Alternant"
        ]
        
        # Mots-clés spécifiques développeur + alternance (prioritaires)
        dev_keywords = [
            "Développeur alternance",
            "Developer alternance",
            "Développeur web alternance",
            "Développeur fullstack alternance",
            "Développeur frontend alternance",
            "Développeur backend alternance",
            "Développeur Python alternance",
            "Développeur Java alternance",
            "Développeur JavaScript alternance",
            "Développeur React alternance",
            "Ingénieur logiciel alternance",
            "Software engineer alternance",
            "Dev web alternant",
            "Développeur mobile alternance",
        ]
        
        # Combiner : d'abord les offres dev, puis les générales
        search_keywords = dev_keywords + general_keywords

        jobs_buffer = []
        total_rejected = 0
        seen_urls = set()  # Pour éviter les doublons

        for term in search_keywords:
            logger.info(f"Recherche pour : {term}")

            try:
                jobs = scrape_jobs(
                    site_name=["indeed", "linkedin"],
                    search_term=term,
                    location="France",
                    results_wanted=30,
                )

                jobs_list = jobs.to_dict("records")
                logger.info(f"Offres brutes recuperees : {len(jobs_list)}")

                for job in jobs_list:
                    if not job.get('job_url') or not job.get('title'):
                        continue

                    # Éviter les doublons
                    if job.get('job_url') in seen_urls:
                        logger.debug(f"Doublon ignoré: {job.get('job_url')}")
                        continue
                    
                    seen_urls.add(job.get('job_url'))

                    if not self.is_valid_alternance(job['title']):
                        total_rejected += 1
                        continue

                    raw_date = job.get('date_posted')
                    if pd.isna(raw_date):
                        safe_date = date.today()
                    else:
                        if hasattr(raw_date, 'date'):
                            safe_date = raw_date.date()
                        else:
                            safe_date = raw_date

                    new_job = JobOffer(
                        title=job.get('title'),
                        company=job.get('company'),
                        location=job.get('location'),
                        description=job.get('description'),
                        job_url=job.get('job_url'),
                        date_posted=safe_date
                    )
                    jobs_buffer.append(new_job)
                
                time.sleep(2)

            except Exception as e:
                logger.error(f"Erreur sur {term} : {e}")

        if jobs_buffer:
            try:
                with transaction.atomic():
                    JobOffer.objects.all().delete()
                    JobOffer.objects.bulk_create(jobs_buffer)
                
                logger.info("Base de donnees mise a jour avec succes.")
                logger.info(f"Nouvelles offres en ligne : {len(jobs_buffer)}")
                logger.info(f"Offres rejetees : {total_rejected}")
            except Exception as e:
                logger.error(f"Erreur lors de la sauvegarde en base : {e}")
        else:
            logger.warning("Aucune offre valide trouvee. La base n'a pas ete touchee.")

    def is_valid_alternance(self, title):
        title_lower = title.lower()

        forbidden_words = [
            'cdi', 'c.d.i',
            'senior', 'manager confirmé',
            'freelance', 'indépendant',
            'stage', 'stagiaire'
        ]

        if any(bad_word in title_lower for bad_word in forbidden_words):
            return False

        required_roots = [
            'alternan',
            'apprenti',
            'pro',
            'etude',
            'master'
        ]

        if any(root in title_lower for root in required_roots):
            return True

        return False